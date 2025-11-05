"""
Binance exchange client using CCXT library.
Handles all exchange interactions including market data and order execution.
"""

import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import logging

from src.config import config

logger = logging.getLogger(__name__)


class BinanceClient:
    """CCXT-based Binance client with comprehensive trading capabilities."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = None):
        """
        Initialize Binance client.

        Args:
            api_key: Binance API key (optional, uses config if not provided)
            api_secret: Binance API secret (optional, uses config if not provided)
            testnet: Use testnet (optional, uses config if not provided)
        """
        self.api_key = api_key or config.BINANCE_API_KEY
        self.api_secret = api_secret or config.BINANCE_API_SECRET
        self.testnet = testnet if testnet is not None else config.BINANCE_TESTNET

        # Initialize exchange
        self.exchange = self._init_exchange()
        logger.info(f"Binance client initialized (testnet={self.testnet})")

    def _init_exchange(self) -> ccxt.binance:
        """Initialize CCXT Binance exchange."""
        exchange_config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # spot, margin, future
            }
        }

        if self.testnet:
            exchange_config['urls'] = {
                'api': {
                    'public': 'https://testnet.binance.vision/api',
                    'private': 'https://testnet.binance.vision/api',
                }
            }

        exchange = ccxt.binance(exchange_config)
        return exchange

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h',
                          since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe
            since: Timestamp to fetch from
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise

    def fetch_ohlcv_sync(self, symbol: str, timeframe: str = '1h',
                         since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        """Synchronous version of fetch_ohlcv."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker information.

        Args:
            symbol: Trading pair

        Returns:
            Ticker data
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            raise

    def fetch_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Fetch order book.

        Args:
            symbol: Trading pair
            limit: Depth of order book

        Returns:
            Order book data
        """
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            raise

    def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades."""
        try:
            return self.exchange.fetch_trades(symbol, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            raise

    def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """
        Create a market order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade

        Returns:
            Order information
        """
        try:
            order = self.exchange.create_market_order(symbol, side, amount)
            logger.info(f"Market {side} order created: {amount} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            raise

    def create_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Create a limit order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade
            price: Limit price

        Returns:
            Order information
        """
        try:
            order = self.exchange.create_limit_order(symbol, side, amount, price)
            logger.info(f"Limit {side} order created: {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            raise

    def create_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Dict[str, Any]:
        """
        Create a stop-loss order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade
            stop_price: Stop price

        Returns:
            Order information
        """
        try:
            params = {'stopPrice': stop_price}
            order = self.exchange.create_order(symbol, 'stop_loss_limit', side, amount, stop_price, params)
            logger.info(f"Stop-loss {side} order created: {amount} {symbol} @ {stop_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating stop-loss order: {e}")
            raise

    def create_take_profit_order(self, symbol: str, side: str, amount: float,
                                 limit_price: float, stop_price: float) -> Dict[str, Any]:
        """
        Create a take-profit order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade
            limit_price: Limit price
            stop_price: Stop price

        Returns:
            Order information
        """
        try:
            params = {'stopPrice': stop_price}
            order = self.exchange.create_order(symbol, 'take_profit_limit', side, amount, limit_price, params)
            logger.info(f"Take-profit {side} order created: {amount} {symbol} @ {limit_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating take-profit order: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled for {symbol}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

    def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise

    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Fetch open orders."""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            raise

    def fetch_closed_orders(self, symbol: Optional[str] = None, since: Optional[int] = None,
                           limit: Optional[int] = None) -> List[Dict]:
        """Fetch closed orders."""
        try:
            return self.exchange.fetch_closed_orders(symbol, since, limit)
        except Exception as e:
            logger.error(f"Error fetching closed orders: {e}")
            raise

    def fetch_my_trades(self, symbol: Optional[str] = None, since: Optional[int] = None,
                       limit: Optional[int] = None) -> List[Dict]:
        """Fetch my trades."""
        try:
            return self.exchange.fetch_my_trades(symbol, since, limit)
        except Exception as e:
            logger.error(f"Error fetching my trades: {e}")
            raise

    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """Get market information for a symbol."""
        try:
            markets = self.exchange.load_markets()
            return markets.get(symbol, {})
        except Exception as e:
            logger.error(f"Error fetching market info: {e}")
            raise

    def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Fetch funding rate (for futures)."""
        try:
            return self.exchange.fetch_funding_rate(symbol)
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            raise

    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        ticker = self.fetch_ticker(symbol)
        return ticker['last']

    def close(self):
        """Close exchange connection."""
        if hasattr(self.exchange, 'close'):
            self.exchange.close()
        logger.info("Binance client closed")
