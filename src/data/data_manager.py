"""
Data management module for fetching, storing, and loading market data.
Handles historical data retrieval and local caching.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
import sqlite3

from src.config import config

logger = logging.getLogger(__name__)


class DataManager:
    """
    Data manager for market data operations.
    Handles fetching, storing, and loading OHLCV data.
    """

    def __init__(self, data_dir: str = 'data', use_database: bool = True):
        """
        Initialize data manager.

        Args:
            data_dir: Directory to store data files
            use_database: Whether to use SQLite database for storage
        """
        self.data_dir = data_dir
        self.use_database = use_database
        self.cache: Dict[str, pd.DataFrame] = {}

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Initialize database if using database storage
        if use_database:
            self.db_path = os.path.join(data_dir, 'market_data.db')
            self._init_database()

        logger.info(f"DataManager initialized (data_dir={data_dir})")

    def _init_database(self):
        """Initialize SQLite database for OHLCV data storage."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp
                ON ohlcv (symbol, timeframe, timestamp)
            ''')

            conn.commit()
            conn.close()

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.use_database = False

    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """Generate cache key for symbol and timeframe."""
        return f"{symbol}_{timeframe}"

    def fetch_historical_bulk(self, client, symbol: str, timeframe: str,
                              days_back: int = 365) -> pd.DataFrame:
        """
        Fetch historical data in bulk from the exchange.

        Args:
            client: Exchange client (BinanceClient)
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            days_back: Number of days of historical data to fetch

        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {days_back} days of historical data for {symbol} ({timeframe})")

        all_data = []
        current_time = datetime.now()

        # Calculate start time
        start_time = current_time - timedelta(days=days_back)

        # Determine how many candles per request based on timeframe
        timeframe_minutes = self._timeframe_to_minutes(timeframe)
        candles_per_day = 24 * 60 // timeframe_minutes

        # Calculate total candles needed
        total_candles = days_back * candles_per_day
        limit_per_request = 1000  # Most exchanges limit to 1000 candles

        # Fetch in batches
        since_timestamp = int(start_time.timestamp() * 1000)
        fetched_candles = 0

        while fetched_candles < total_candles:
            try:
                # Fetch data
                df = client.fetch_ohlcv_sync(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since_timestamp,
                    limit=limit_per_request
                )

                if df.empty:
                    break

                all_data.append(df)
                fetched_candles += len(df)

                # Update since timestamp for next batch
                last_timestamp = df.index[-1]
                since_timestamp = int(last_timestamp.timestamp() * 1000) + 1

                logger.debug(f"Fetched {len(df)} candles, total: {fetched_candles}")

                # Check if we've reached the present
                if last_timestamp >= current_time - timedelta(minutes=timeframe_minutes):
                    break

            except Exception as e:
                logger.error(f"Error fetching historical data: {e}")
                break

        if not all_data:
            logger.warning("No historical data fetched")
            return pd.DataFrame()

        # Combine all data
        result_df = pd.concat(all_data)

        # Remove duplicates
        result_df = result_df[~result_df.index.duplicated(keep='last')]

        # Sort by timestamp
        result_df = result_df.sort_index()

        logger.info(f"Fetched {len(result_df)} total candles for {symbol}")

        # Store in cache and database
        cache_key = self._get_cache_key(symbol, timeframe)
        self.cache[cache_key] = result_df

        if self.use_database:
            self._save_to_database(result_df, symbol, timeframe)

        return result_df

    def update_latest_data(self, client, symbol: str, timeframe: str,
                           limit: int = 100) -> pd.DataFrame:
        """
        Update with the latest market data.

        Args:
            client: Exchange client
            symbol: Trading pair
            timeframe: Candlestick timeframe
            limit: Number of recent candles to fetch

        Returns:
            Updated DataFrame
        """
        try:
            # Fetch latest data
            new_df = client.fetch_ohlcv_sync(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )

            if new_df.empty:
                logger.warning("No new data fetched")
                return self.load_ohlcv(symbol, timeframe, limit)

            # Get cache key
            cache_key = self._get_cache_key(symbol, timeframe)

            # Merge with existing data
            if cache_key in self.cache:
                existing_df = self.cache[cache_key]
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()
                self.cache[cache_key] = combined_df
            else:
                self.cache[cache_key] = new_df

            # Update database
            if self.use_database:
                self._save_to_database(new_df, symbol, timeframe)

            logger.debug(f"Updated data for {symbol} ({timeframe})")

            return self.cache[cache_key]

        except Exception as e:
            logger.error(f"Error updating latest data: {e}")
            return self.load_ohlcv(symbol, timeframe, limit)

    def load_ohlcv(self, symbol: str, timeframe: str,
                   limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load OHLCV data from cache or database.

        Args:
            symbol: Trading pair
            timeframe: Candlestick timeframe
            limit: Maximum number of candles to return (most recent)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = self._get_cache_key(symbol, timeframe)

        # Try cache first
        if cache_key in self.cache:
            df = self.cache[cache_key]
            if limit:
                df = df.tail(limit)
            return df

        # Try database
        if self.use_database:
            df = self._load_from_database(symbol, timeframe, limit)
            if not df.empty:
                self.cache[cache_key] = df
                return df

        logger.warning(f"No data found for {symbol} ({timeframe})")
        return pd.DataFrame()

    def _save_to_database(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Save OHLCV data to database."""
        try:
            conn = sqlite3.connect(self.db_path)

            for timestamp, row in df.iterrows():
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO ohlcv
                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        timeframe,
                        timestamp.isoformat(),
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume']
                    ))
                except Exception as e:
                    logger.debug(f"Error inserting row: {e}")

            conn.commit()
            conn.close()

            logger.debug(f"Saved {len(df)} candles to database")

        except Exception as e:
            logger.error(f"Error saving to database: {e}")

    def _load_from_database(self, symbol: str, timeframe: str,
                            limit: Optional[int] = None) -> pd.DataFrame:
        """Load OHLCV data from database."""
        try:
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
            '''

            if limit:
                query += f' LIMIT {limit}'

            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, timeframe),
                parse_dates=['timestamp'],
                index_col='timestamp'
            )

            conn.close()

            # Reverse to chronological order
            df = df.iloc[::-1]

            logger.debug(f"Loaded {len(df)} candles from database")

            return df

        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return pd.DataFrame()

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        multipliers = {
            'm': 1,
            'h': 60,
            'd': 1440,
            'w': 10080,
        }

        unit = timeframe[-1].lower()
        value = int(timeframe[:-1])

        return value * multipliers.get(unit, 1)

    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Clear cached data.

        Args:
            symbol: Symbol to clear (None for all)
            timeframe: Timeframe to clear (None for all)
        """
        if symbol and timeframe:
            cache_key = self._get_cache_key(symbol, timeframe)
            if cache_key in self.cache:
                del self.cache[cache_key]
        elif symbol:
            keys_to_remove = [k for k in self.cache if k.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()

        logger.info("Cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data."""
        info = {}
        for key, df in self.cache.items():
            info[key] = {
                'rows': len(df),
                'start': df.index[0].isoformat() if len(df) > 0 else None,
                'end': df.index[-1].isoformat() if len(df) > 0 else None,
            }
        return info
