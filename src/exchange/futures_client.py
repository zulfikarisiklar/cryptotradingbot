"""
Binance Futures client with leverage trading support.
Handles futures-specific operations including leverage, positions, and funding rates.
"""

import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from src.config import config

logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    """
    CCXT-based Binance Futures client with full leverage trading support.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 testnet: bool = None):
        """
        Initialize Binance Futures client.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet
        """
        self.api_key = api_key or config.BINANCE_API_KEY
        self.api_secret = api_secret or config.BINANCE_API_SECRET
        self.testnet = testnet if testnet is not None else config.BINANCE_TESTNET

        # Initialize exchange
        self.exchange = self._init_exchange()
        logger.info(f"Binance Futures client initialized (testnet={self.testnet})")

    def _init_exchange(self) -> ccxt.binance:
        """Initialize CCXT Binance Futures exchange."""
        exchange_config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Use futures market
                'adjustForTimeDifference': True,
            }
        }

        if self.testnet:
            exchange_config['urls'] = {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1',
                }
            }

        exchange = ccxt.binance(exchange_config)
        exchange.load_markets()
        return exchange

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Set leverage for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            leverage: Leverage multiplier (1-125)

        Returns:
            Response from exchange
        """
        try:
            response = self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return response
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            raise

    def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> Dict[str, Any]:
        """
        Set margin mode (isolated or cross).

        Args:
            symbol: Trading pair
            margin_mode: 'isolated' or 'cross'

        Returns:
            Response from exchange
        """
        try:
            if margin_mode.lower() == 'isolated':
                response = self.exchange.set_margin_mode('isolated', symbol)
            else:
                response = self.exchange.set_margin_mode('cross', symbol)

            logger.info(f"Margin mode set to {margin_mode} for {symbol}")
            return response
        except Exception as e:
            logger.error(f"Error setting margin mode: {e}")
            # Some exchanges don't support changing margin mode, continue
            logger.warning(f"Could not set margin mode, using default")
            return {}

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h',
                    since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data for futures.

        Args:
            symbol: Trading pair
            timeframe: Timeframe
            since: Start timestamp
            limit: Number of candles

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
            logger.error(f"Error fetching OHLCV: {e}")
            raise

    def create_market_order(self, symbol: str, side: str, amount: float,
                           reduce_only: bool = False) -> Dict[str, Any]:
        """
        Create a market order for futures.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            reduce_only: If True, only reduces position

        Returns:
            Order information
        """
        try:
            params = {}
            if reduce_only:
                params['reduceOnly'] = True

            order = self.exchange.create_market_order(symbol, side, amount, params)
            logger.info(f"Futures market {side} order created: {amount} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            raise

    def create_limit_order(self, symbol: str, side: str, amount: float, price: float,
                          reduce_only: bool = False) -> Dict[str, Any]:
        """
        Create a limit order for futures.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            price: Limit price
            reduce_only: If True, only reduces position

        Returns:
            Order information
        """
        try:
            params = {}
            if reduce_only:
                params['reduceOnly'] = True

            order = self.exchange.create_limit_order(symbol, side, amount, price, params)
            logger.info(f"Futures limit {side} order created: {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            raise

    def create_stop_market_order(self, symbol: str, side: str, amount: float,
                                stop_price: float, reduce_only: bool = True) -> Dict[str, Any]:
        """
        Create a stop-loss market order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount
            stop_price: Stop trigger price
            reduce_only: If True, only reduces position

        Returns:
            Order information
        """
        try:
            params = {
                'stopPrice': stop_price,
                'type': 'STOP_MARKET',
            }
            if reduce_only:
                params['reduceOnly'] = True

            order = self.exchange.create_order(symbol, 'STOP_MARKET', side, amount, None, params)
            logger.info(f"Stop-loss order created: {side} {amount} {symbol} @ {stop_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating stop-loss order: {e}")
            raise

    def create_take_profit_market_order(self, symbol: str, side: str, amount: float,
                                       stop_price: float, reduce_only: bool = True) -> Dict[str, Any]:
        """
        Create a take-profit market order.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount
            stop_price: Take profit trigger price
            reduce_only: If True, only reduces position

        Returns:
            Order information
        """
        try:
            params = {
                'stopPrice': stop_price,
                'type': 'TAKE_PROFIT_MARKET',
            }
            if reduce_only:
                params['reduceOnly'] = True

            order = self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', side, amount, None, params)
            logger.info(f"Take-profit order created: {side} {amount} {symbol} @ {stop_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating take-profit order: {e}")
            raise

    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch current open positions.

        Args:
            symbols: List of symbols to fetch (None for all)

        Returns:
            List of position information
        """
        try:
            positions = self.exchange.fetch_positions(symbols)

            # Filter out positions with zero contracts
            active_positions = [
                pos for pos in positions
                if float(pos.get('contracts', 0)) != 0
            ]

            logger.info(f"Fetched {len(active_positions)} active positions")
            return active_positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    def fetch_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch position for a specific symbol.

        Args:
            symbol: Trading pair

        Returns:
            Position information or None
        """
        try:
            positions = self.fetch_positions([symbol])
            if positions:
                return positions[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching position: {e}")
            return None

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close an open position completely.

        Args:
            symbol: Trading pair

        Returns:
            Order information
        """
        try:
            # Get current position
            position = self.fetch_position(symbol)

            if not position or float(position.get('contracts', 0)) == 0:
                logger.warning(f"No open position for {symbol}")
                return {}

            # Determine side and amount
            contracts = float(position['contracts'])
            side = 'sell' if contracts > 0 else 'buy'  # Opposite side to close
            amount = abs(contracts)

            # Close position with market order
            order = self.create_market_order(symbol, side, amount, reduce_only=True)
            logger.info(f"Position closed for {symbol}")
            return order
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise

    def fetch_balance(self) -> Dict[str, Any]:
        """Fetch futures account balance."""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise

    def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current funding rate.

        Args:
            symbol: Trading pair

        Returns:
            Funding rate information
        """
        try:
            funding_rate = self.exchange.fetch_funding_rate(symbol)
            logger.info(f"Funding rate for {symbol}: {funding_rate.get('fundingRate', 0)}")
            return funding_rate
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return {}

    def fetch_funding_history(self, symbol: str, since: Optional[int] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch funding rate history.

        Args:
            symbol: Trading pair
            since: Start timestamp
            limit: Number of records

        Returns:
            List of funding rate history
        """
        try:
            funding_history = self.exchange.fetch_funding_rate_history(symbol, since, limit)
            return funding_history
        except Exception as e:
            logger.error(f"Error fetching funding history: {e}")
            return []

    def get_available_symbols(self) -> List[str]:
        """
        Get all available futures trading pairs.

        Returns:
            List of symbol names
        """
        try:
            markets = self.exchange.load_markets()

            # Filter for USDT perpetual futures
            futures_symbols = [
                symbol for symbol, market in markets.items()
                if market.get('type') == 'future' and
                   market.get('quote') == 'USDT' and
                   market.get('active', False)
            ]

            logger.info(f"Found {len(futures_symbols)} active futures symbols")
            return sorted(futures_symbols)
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []

    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get market information for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Market information
        """
        try:
            markets = self.exchange.load_markets()
            market = markets.get(symbol, {})
            return market
        except Exception as e:
            logger.error(f"Error getting market info: {e}")
            return {}

    def calculate_position_value(self, symbol: str, amount: float, price: float,
                                 leverage: int) -> Tuple[float, float]:
        """
        Calculate position value and required margin.

        Args:
            symbol: Trading pair
            amount: Position size
            price: Entry price
            leverage: Leverage multiplier

        Returns:
            Tuple of (position_value, required_margin)
        """
        position_value = amount * price
        required_margin = position_value / leverage

        return position_value, required_margin

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker information."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            raise

    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Fetch open orders."""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled for {symbol}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Cancel all open orders for a symbol."""
        try:
            result = self.exchange.cancel_all_orders(symbol)
            logger.info(f"All orders cancelled for {symbol}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return []

    def close(self):
        """Close exchange connection."""
        if hasattr(self.exchange, 'close'):
            self.exchange.close()
        logger.info("Binance Futures client closed")
