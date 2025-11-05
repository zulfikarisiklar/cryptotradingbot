"""
Backtesting engine for testing trading strategies on historical data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import seaborn as sns

from src.strategy.trading_strategy import TradingStrategy
from src.ml.ml_engine import MLEngine
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.data.data_manager import DataManager
from src.exchange.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine for strategy evaluation.
    """

    def __init__(self, symbol: str, timeframe: str, initial_capital: float = 10000):
        """
        Initialize backtest engine.

        Args:
            symbol: Trading pair
            timeframe: Timeframe
            initial_capital: Initial capital
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital

        self.strategy = TradingStrategy(symbol, initial_capital)
        self.ml_engine = MLEngine()
        self.sentiment_analyzer = SentimentAnalyzer()

        self.results = []
        self.equity_curve = []

        logger.info(f"BacktestEngine initialized for {symbol} {timeframe}")

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data with all features for backtesting.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with all features
        """
        logger.info("Preparing data for backtesting...")

        # Add features using ML engine
        df_features = self.ml_engine.prepare_features(df, include_sentiment=False)

        return df_features

    def run_backtest(self, df: pd.DataFrame, train_test_split: float = 0.7) -> Dict:
        """
        Run backtest on historical data.

        Args:
            df: DataFrame with OHLCV data
            train_test_split: Ratio for train/test split

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest on {len(df)} candles...")

        # Split data
        split_index = int(len(df) * train_test_split)
        train_df = df.iloc[:split_index].copy()
        test_df = df.iloc[split_index:].copy()

        logger.info(f"Training period: {train_df.index[0]} to {train_df.index[-1]}")
        logger.info(f"Testing period: {test_df.index[0]} to {test_df.index[-1]}")

        # Train ML models
        logger.info("Training ML models...")
        training_scores = self.ml_engine.train(train_df, symbol=self.symbol)
        logger.info(f"Training scores: {training_scores}")

        # Prepare test data with features
        test_df_features = self.prepare_data(test_df)

        # Run backtest on test data
        logger.info("Running backtest on test data...")
        self._backtest_loop(test_df, test_df_features)

        # Calculate statistics
        stats = self._calculate_statistics()

        logger.info("Backtest complete")
        return stats

    def _backtest_loop(self, df_price: pd.DataFrame, df_features: pd.DataFrame):
        """
        Main backtest loop.

        Args:
            df_price: DataFrame with OHLCV data
            df_features: DataFrame with features
        """
        # Minimum lookback period for indicators
        lookback = 200

        for i in range(lookback, len(df_price)):
            # Get data up to current point
            current_df_price = df_price.iloc[:i+1]
            current_df_features = df_features.iloc[:i+1]

            current_timestamp = df_price.index[i]
            current_price = df_price.iloc[i]['close']

            # Get ML prediction
            try:
                ml_prediction, ml_confidence = self.ml_engine.predict(
                    current_df_price,
                    symbol=self.symbol,
                    ensemble=True
                )
            except Exception as e:
                logger.warning(f"ML prediction error at {current_timestamp}: {e}")
                ml_prediction = 0
                ml_confidence = 0.0

            # Get sentiment signal (simplified for backtesting - using a dummy value)
            # In real-time, this would fetch actual news sentiment
            sentiment_signal = 0.0

            # Update position price
            if self.strategy.position:
                self.strategy.position.update_price(current_price)

                # Check exit conditions
                should_exit, exit_reason = self.strategy.check_exit_signal(current_df_price)

                if should_exit:
                    trade_info = self.strategy.close_position(
                        current_df_price,
                        current_timestamp,
                        exit_reason
                    )
                    self.results.append(trade_info)

                # Check pyramid conditions
                elif self.strategy.check_pyramid_entry(current_df_price, ml_confidence):
                    trade_info = self.strategy.add_pyramid_level(
                        current_df_price,
                        current_timestamp
                    )
                    self.results.append(trade_info)

            else:
                # Check entry conditions
                if self.strategy.check_entry_signal(
                    current_df_features,
                    ml_prediction,
                    ml_confidence,
                    sentiment_signal
                ):
                    trade_info = self.strategy.open_position(
                        current_df_price,
                        current_timestamp
                    )
                    self.results.append(trade_info)

            # Record equity
            current_equity = self.strategy.capital
            if self.strategy.position:
                current_equity += current_price * self.strategy.position.amount

            self.equity_curve.append({
                'timestamp': current_timestamp,
                'equity': current_equity,
                'price': current_price,
            })

    def _calculate_statistics(self) -> Dict:
        """Calculate backtest statistics."""
        if not self.equity_curve:
            return {}

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)

        # Performance metrics
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / self.initial_capital - 1) * 100

        # Calculate returns
        equity_df['returns'] = equity_df['equity'].pct_change()

        # Sharpe Ratio (assuming daily data, annualized)
        if equity_df['returns'].std() > 0:
            sharpe_ratio = equity_df['returns'].mean() / equity_df['returns'].std() * np.sqrt(365)
        else:
            sharpe_ratio = 0

        # Maximum Drawdown
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
        max_drawdown = equity_df['drawdown'].min()

        # Trade statistics
        trade_stats = self.strategy.get_performance_stats()

        # Combine statistics
        stats = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return_percent': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_percent': max_drawdown,
            'total_trades': trade_stats.get('total_trades', 0),
            'winning_trades': trade_stats.get('winning_trades', 0),
            'losing_trades': trade_stats.get('losing_trades', 0),
            'win_rate_percent': trade_stats.get('win_rate', 0),
            'avg_win': trade_stats.get('avg_win', 0),
            'avg_loss': trade_stats.get('avg_loss', 0),
            'largest_win': trade_stats.get('largest_win', 0),
            'largest_loss': trade_stats.get('largest_loss', 0),
            'profit_factor': abs(trade_stats.get('avg_win', 0) / trade_stats.get('avg_loss', 1)) if trade_stats.get('avg_loss', 0) != 0 else 0,
        }

        return stats

    def plot_results(self, save_path: Optional[str] = None):
        """
        Plot backtest results.

        Args:
            save_path: Path to save the plot (optional)
        """
        if not self.equity_curve:
            logger.warning("No backtest results to plot")
            return

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)

        # Create subplots
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))

        # Plot 1: Equity curve
        axes[0].plot(equity_df.index, equity_df['equity'], label='Equity', color='blue')
        axes[0].axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
        axes[0].set_title('Equity Curve', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('Equity ($)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Plot 2: Price with trades
        axes[1].plot(equity_df.index, equity_df['price'], label='Price', color='black', alpha=0.7)

        # Mark trades
        open_trades = [r for r in self.results if r.get('action') == 'OPEN']
        close_trades = [r for r in self.results if r.get('action') == 'CLOSE']

        if open_trades:
            open_df = pd.DataFrame(open_trades)
            axes[1].scatter(open_df['timestamp'], open_df['price'],
                          color='green', marker='^', s=100, label='Open', zorder=5)

        if close_trades:
            close_df = pd.DataFrame(close_trades)
            winning_closes = close_df[close_df['pnl'] > 0]
            losing_closes = close_df[close_df['pnl'] <= 0]

            if not winning_closes.empty:
                axes[1].scatter(winning_closes['timestamp'], winning_closes['price'],
                              color='blue', marker='v', s=100, label='Close (Win)', zorder=5)

            if not losing_closes.empty:
                axes[1].scatter(losing_closes['timestamp'], losing_closes['price'],
                              color='red', marker='v', s=100, label='Close (Loss)', zorder=5)

        axes[1].set_title('Price with Trade Markers', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('Price ($)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        # Plot 3: Drawdown
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100

        axes[2].fill_between(equity_df.index, equity_df['drawdown'], 0,
                            color='red', alpha=0.3, label='Drawdown')
        axes[2].set_title('Drawdown', fontsize=14, fontweight='bold')
        axes[2].set_ylabel('Drawdown (%)')
        axes[2].set_xlabel('Date')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plot saved to {save_path}")
        else:
            plt.show()

        plt.close()

    def print_summary(self):
        """Print backtest summary."""
        stats = self._calculate_statistics()

        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.timeframe}")
        print(f"\nCapital:")
        print(f"  Initial: ${stats.get('initial_capital', 0):,.2f}")
        print(f"  Final: ${stats.get('final_equity', 0):,.2f}")
        print(f"  Total Return: {stats.get('total_return_percent', 0):.2f}%")
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {stats.get('max_drawdown_percent', 0):.2f}%")
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {stats.get('total_trades', 0)}")
        print(f"  Winning Trades: {stats.get('winning_trades', 0)}")
        print(f"  Losing Trades: {stats.get('losing_trades', 0)}")
        print(f"  Win Rate: {stats.get('win_rate_percent', 0):.2f}%")
        print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
        print(f"\nAverage Results:")
        print(f"  Avg Win: ${stats.get('avg_win', 0):.2f}")
        print(f"  Avg Loss: ${stats.get('avg_loss', 0):.2f}")
        print(f"  Largest Win: ${stats.get('largest_win', 0):.2f}")
        print(f"  Largest Loss: ${stats.get('largest_loss', 0):.2f}")
        print("=" * 60 + "\n")

    def export_results(self, filename: str = 'backtest_results.csv'):
        """
        Export backtest results to CSV.

        Args:
            filename: Output filename
        """
        if not self.results:
            logger.warning("No results to export")
            return

        results_df = pd.DataFrame(self.results)
        results_df.to_csv(filename, index=False)
        logger.info(f"Results exported to {filename}")

        # Export equity curve
        equity_df = pd.DataFrame(self.equity_curve)
        equity_filename = filename.replace('.csv', '_equity.csv')
        equity_df.to_csv(equity_filename, index=False)
        logger.info(f"Equity curve exported to {equity_filename}")


def run_quick_backtest(symbol: str, timeframe: str, days: int = 365,
                      initial_capital: float = 10000) -> Dict:
    """
    Quick backtest helper function.

    Args:
        symbol: Trading pair
        timeframe: Timeframe
        days: Number of days to backtest
        initial_capital: Initial capital

    Returns:
        Backtest statistics
    """
    logger.info(f"Running quick backtest for {symbol} {timeframe}...")

    # Initialize components
    client = BinanceClient()
    data_manager = DataManager()

    # Fetch historical data
    logger.info(f"Fetching {days} days of historical data...")
    data_manager.fetch_historical_bulk(client, symbol, timeframe, days_back=days)

    # Load data
    df = data_manager.load_ohlcv(symbol, timeframe)

    if df.empty:
        logger.error("No data available for backtesting")
        return {}

    logger.info(f"Loaded {len(df)} candles for backtesting")

    # Run backtest
    backtest = BacktestEngine(symbol, timeframe, initial_capital)
    stats = backtest.run_backtest(df)

    # Print summary
    backtest.print_summary()

    # Plot results
    backtest.plot_results(save_path='backtest_results.png')

    # Export results
    backtest.export_results()

    return stats
