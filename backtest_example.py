"""
Example script for running backtests.
"""

import sys
from src.backtest.backtest_engine import run_quick_backtest
from src.utils.logger import setup_logger

logger = setup_logger('backtest')


def main():
    """Run backtest example."""
    # Configuration
    SYMBOL = 'BTC/USDT'
    TIMEFRAME = '1h'
    DAYS = 365
    INITIAL_CAPITAL = 10000

    logger.info("Starting backtest example...")
    logger.info(f"Symbol: {SYMBOL}")
    logger.info(f"Timeframe: {TIMEFRAME}")
    logger.info(f"Days: {DAYS}")
    logger.info(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")

    # Run backtest
    stats = run_quick_backtest(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        days=DAYS,
        initial_capital=INITIAL_CAPITAL
    )

    if stats:
        logger.info("Backtest completed successfully")
        logger.info(f"Total Return: {stats.get('total_return_percent', 0):.2f}%")
        logger.info(f"Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}")
        logger.info(f"Max Drawdown: {stats.get('max_drawdown_percent', 0):.2f}%")
        logger.info(f"Win Rate: {stats.get('win_rate_percent', 0):.2f}%")
    else:
        logger.error("Backtest failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
