"""
Configuration management for the trading bot.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()


class Config:
    """Central configuration class for the trading bot."""

    # Binance API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'True').lower() == 'true'

    # Trading Configuration
    TRADING_SYMBOL = os.getenv('TRADING_SYMBOL', 'BTC/USDT')
    TRADING_TIMEFRAME = os.getenv('TRADING_TIMEFRAME', '1h')
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '10000'))

    # Risk Management
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.02'))
    TAKE_PROFIT_MULTIPLIER = float(os.getenv('TAKE_PROFIT_MULTIPLIER', '2.0'))
    MAX_PYRAMID_LEVELS = int(os.getenv('MAX_PYRAMID_LEVELS', '3'))

    # Machine Learning
    ML_LOOKBACK_PERIODS = int(os.getenv('ML_LOOKBACK_PERIODS', '100'))
    ML_RETRAIN_INTERVAL = int(os.getenv('ML_RETRAIN_INTERVAL', '24'))

    # Sentiment Analysis
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
    ENABLE_SENTIMENT = os.getenv('ENABLE_SENTIMENT', 'True').lower() == 'true'

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_data.db')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')

    @classmethod
    def load_yaml_config(cls, config_path: str) -> Dict[str, Any]:
        """Load additional configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    @classmethod
    def validate(cls) -> bool:
        """Validate essential configuration."""
        if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
            raise ValueError("Binance API credentials not configured!")
        return True


# Export singleton config
config = Config()
