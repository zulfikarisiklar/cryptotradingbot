# Crypto Trading Bot with AI & Sentiment Analysis

A comprehensive cryptocurrency trading bot built with Python that combines:
- **CCXT** for Binance exchange connectivity
- **Futures Trading** with up to 125x leverage 🆕
- **Multi-Symbol Portfolio** management (up to 5 concurrent positions) 🆕
- **Dynamic Signal Scanner** across 50+ symbols 🆕
- **200+ Technical Indicators** from TA-Lib
- **Machine Learning** for pattern recognition (XGBoost, LightGBM, Random Forest)
- **Sentiment Analysis** from news sources
- **Advanced Risk Management** with ATR-based stops
- **Pyramid Position Building**
- **Complete Backtesting Engine**

## Features

### 🚀 Futures Trading (NEW!)
- **Binance Futures** with customizable leverage (1-125x)
- **Multi-Symbol Portfolio Management:**
  - Trade up to 5 symbols simultaneously
  - 4% risk per trade (configurable)
  - Automatic position sizing based on risk
- **Dynamic Market Scanner:**
  - Scans 50+ top symbols by volume
  - Ranks by signal strength (0-100)
  - Automatically finds best opportunities
- **User-Configurable Settings:**
  - Set your own leverage
  - Adjust stop loss (ATR-based)
  - Customize take profit targets
- **Isolated Margin Mode:** Each position independent
- **Automatic TP/SL Orders:** Set on every trade
- **Liquidation Protection:** Closes positions at 90% margin

**Quick Start:**
```bash
# Futures paper trading
python futures_bot.py --mode paper --capital 10000 --leverage 10

# See FUTURES_TRADING.md for complete guide
```

### 🛡️ Advanced Safety Systems
- **Emergency Stop System**:
  - Automatic detection of market crashes (-5% in 1min, -10% in 5min, -15% in 15min)
  - Extreme volume spike detection (5x+ normal volume)
  - Volatility explosion detection (3x+ normal volatility)
  - Instant position closure on emergency triggers

- **Market Hours Filter**:
  - Avoids trading during Asian stock market openings (Tokyo, Hong Kong, Shanghai)
  - Avoids trading during US stock market opening (NYSE/NASDAQ)
  - Prevents entries during high-volatility institutional trading periods

- **Circuit Breaker**:
  - Automatic trading halt on 15%+ drawdown
  - Stops after 5 consecutive losing trades
  - 60-minute cooldown period after trigger
  - Manual reset required after review

### 📊 Technical Analysis
- **All 200+ TA-Lib indicators** including:
  - Overlap Studies (SMA, EMA, Bollinger Bands, etc.)
  - Momentum Indicators (RSI, MACD, Stochastic, ADX, etc.)
  - Volume Indicators (OBV, AD, ADOSC)
  - Volatility Indicators (ATR, NATR)
  - 60+ Candlestick Pattern Recognition
  - Cycle Indicators (Hilbert Transform)
  - Statistical Functions

### 🤖 Machine Learning
- **Multiple ML Models**:
  - Random Forest
  - XGBoost
  - LightGBM
  - Gradient Boosting
- Ensemble predictions with confidence scoring
- Automatic model retraining
- Feature importance analysis

### 📰 Sentiment Analysis
- News sentiment analysis using VADER and TextBlob
- Crypto-specific lexicon
- Fear & Greed index calculation
- Integration with NewsAPI

### 💰 Advanced Trading Features
- **Take Profit**: ATR-based dynamic targets
- **Stop Loss**: ATR-based trailing stops
- **Pyramid Mode**: Add to winning positions (configurable levels)
- **Risk Management**: Position sizing, drawdown limits, daily loss limits
- **Paper Trading**: Test strategies without real money
- **Emergency Exit**: Automatic position closure on market crashes
- **Smart Timing**: Avoids high-volatility periods during stock market openings

### 📈 Backtesting
- Historical data replay
- Performance metrics (Sharpe ratio, max drawdown, win rate)
- Visual results with charts
- Trade-by-trade analysis

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone the repository
```bash
git clone https://github.com/yourusername/cryptotradingbot.git
cd cryptotradingbot
```

### Step 2: Install TA-Lib (Required)

**On Ubuntu/Debian:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
```

**On macOS:**
```bash
brew install ta-lib
```

**On Windows:**
Download and install from: https://github.com/cgohlke/talib-build/releases

### Step 3: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=True

# Trading Configuration
TRADING_SYMBOL=BTC/USDT
TRADING_TIMEFRAME=1h
INITIAL_CAPITAL=10000

# Risk Management
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENT=0.02
TAKE_PROFIT_MULTIPLIER=2.0
MAX_PYRAMID_LEVELS=3

# Sentiment Analysis (Optional)
NEWS_API_KEY=your_news_api_key_here
ENABLE_SENTIMENT=True
```

## Usage

### Running a Backtest

```bash
python backtest_example.py
```

This will:
1. Fetch 1 year of historical data
2. Train ML models on the data
3. Run backtest simulation
4. Generate performance report and charts
5. Save results to CSV files

### Running the Trading Bot (Paper Trading)

```bash
python main.py --mode paper --symbol BTC/USDT --timeframe 1h --capital 10000
```

### Running the Trading Bot (Live Trading)

⚠️ **WARNING**: Live trading involves real money. Start with small amounts and paper trade first!

```bash
python main.py --mode live --symbol BTC/USDT --timeframe 1h --capital 1000
```

### Command Line Arguments

```bash
python main.py --help

Options:
  --symbol SYMBOL       Trading pair (e.g., BTC/USDT)
  --timeframe TIMEFRAME Timeframe (e.g., 1h, 4h, 1d)
  --capital CAPITAL     Initial capital
  --mode {paper,live}   Trading mode
  --interval INTERVAL   Check interval in seconds (default: 300)
```

## Project Structure

```
cryptotradingbot/
├── src/
│   ├── exchange/          # Binance CCXT client
│   ├── data/              # Data collection and storage
│   ├── indicators/        # 200+ TA-Lib indicators
│   ├── sentiment/         # Sentiment analysis
│   ├── ml/                # Machine learning engine
│   ├── strategy/          # Trading strategy with TP/SL/Pyramid
│   ├── backtest/          # Backtesting engine
│   ├── risk/              # Risk management
│   ├── utils/             # Utilities and logging
│   └── config.py          # Configuration
├── main.py                # Main bot orchestrator
├── backtest_example.py    # Backtest example
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
└── README.md             # This file
```

## Configuration

### Trading Parameters

Edit `.env` or modify `src/config.py`:

```python
# Position sizing
MAX_POSITION_SIZE = 0.1  # 10% of portfolio per position

# Stop loss and take profit
STOP_LOSS_PERCENT = 0.02  # 2% stop loss
TAKE_PROFIT_MULTIPLIER = 2.0  # 2x ATR for take profit

# Pyramid trading
MAX_PYRAMID_LEVELS = 3  # Maximum pyramid levels

# Safety systems
ENABLE_EMERGENCY_STOP = True
ENABLE_MARKET_HOURS_FILTER = True
ENABLE_CIRCUIT_BREAKER = True

# Emergency thresholds
CRASH_THRESHOLD_1M = -0.05  # -5% in 1 minute
CRASH_THRESHOLD_5M = -0.10  # -10% in 5 minutes
CRASH_THRESHOLD_15M = -0.15  # -15% in 15 minutes
VOLUME_SPIKE_THRESHOLD = 5.0  # 5x normal volume

# Circuit breaker
MAX_DRAWDOWN_BEFORE_STOP = 0.15  # 15%
MAX_CONSECUTIVE_LOSSES = 5
CIRCUIT_BREAKER_COOLDOWN = 60  # minutes

# Machine learning
ML_LOOKBACK_PERIODS = 100  # Historical periods for training
ML_RETRAIN_INTERVAL = 24  # Retrain every 24 hours
```

## How It Works

### 0. Safety Check (First Priority!)
- **Emergency Detection**: Checks for market crashes, volume spikes, volatility explosions
- **Market Hours Filter**: Avoids stock market opening times
- **Circuit Breaker**: Validates drawdown and losing streaks
- **Action**: If any safety condition fails, closes positions and halts trading

### 1. Data Collection
- Fetches OHLCV data from Binance via CCXT
- Stores data in SQLite database
- Updates with latest candles

### 2. Feature Engineering
- Calculates 200+ technical indicators
- Adds volume analysis features
- Includes sentiment scores from news
- Creates ML-ready feature matrix

### 3. Machine Learning
- Trains multiple models on historical data
- Uses ensemble predictions
- Considers confidence scores
- Retrains periodically

### 4. Trading Decision
- Combines ML predictions with technical filters
- Checks sentiment analysis
- Validates with risk management
- Executes trades via CCXT

### 5. Position Management
- Opens positions with calculated size
- Sets ATR-based stop loss and take profit
- Adds pyramid levels on profit
- Trails stop loss as price moves favorably

### 6. Risk Management
- Position sizing based on risk percentage
- Drawdown limits
- Daily loss limits
- Trade validation

## Backtesting Results

Example backtest output:

```
============================================================
BACKTEST SUMMARY
============================================================
Symbol: BTC/USDT
Timeframe: 1h

Capital:
  Initial: $10,000.00
  Final: $12,450.00
  Total Return: 24.50%

Risk Metrics:
  Sharpe Ratio: 1.85
  Max Drawdown: -8.35%

Trade Statistics:
  Total Trades: 45
  Winning Trades: 28
  Losing Trades: 17
  Win Rate: 62.22%
  Profit Factor: 2.15

Average Results:
  Avg Win: $185.50
  Avg Loss: $86.25
  Largest Win: $425.00
  Largest Loss: $165.00
============================================================
```

## API Keys

### Binance API
1. Go to Binance.com (or testnet.binance.vision for testing)
2. Create API key in account settings
3. Enable trading permissions
4. Add IP whitelist for security
5. Copy API key and secret to `.env`

### NewsAPI (Optional)
1. Sign up at https://newsapi.org/
2. Get free API key (500 requests/day)
3. Add to `.env`

## Safety & Risk Warnings

⚠️ **IMPORTANT WARNINGS**:

1. **Start with Paper Trading**: Always test strategies in paper mode first
2. **Use Small Amounts**: Start with minimal capital in live mode
3. **Test on Testnet**: Use Binance testnet before real trading
4. **Monitor Closely**: Keep an eye on the bot, especially initially
5. **Set Loss Limits**: Configure appropriate stop losses and daily limits
6. **Understand Risks**: Crypto trading is highly risky, you can lose money
7. **No Guarantees**: Past performance doesn't guarantee future results
8. **API Security**: Keep API keys secure, use IP whitelisting
9. **Withdrawal Restrictions**: Consider disabling withdrawals on API keys

### 🚨 Emergency Safety Features

The bot includes multiple layers of protection:

**1. Emergency Stop System**
- Triggers on sudden price crashes (configurable thresholds)
- Activates on extreme volume spikes
- Detects volatility explosions
- **Automatically closes all positions immediately**

**2. Market Hours Protection**
- Pauses trading during stock market openings
- Asian Markets: Tokyo (00:00-01:00 UTC), Hong Kong/Shanghai (01:30-02:30 UTC)
- US Markets: NYSE/NASDAQ (14:30-15:30 UTC)
- Prevents entry during high-volatility institutional trading

**3. Circuit Breaker**
- Trips on 15% drawdown (configurable)
- Trips after 5 consecutive losses (configurable)
- Requires manual reset after cooldown period
- Forces review before resuming trading

**How Emergency Stop Works:**
```
Market Crash Detected → Emergency Stop Triggered → Close All Positions → Halt Trading
```

All safety thresholds are configurable in `.env` file.

## Advanced Configuration

### Custom Indicators
Add custom indicators in `src/indicators/technical_indicators.py`

### Custom Strategy
Modify entry/exit logic in `src/strategy/trading_strategy.py`

### ML Model Tuning
Adjust model parameters in `src/ml/ml_engine.py`

### Sentiment Sources
Add custom sentiment sources in `src/sentiment/sentiment_analyzer.py`

## Troubleshooting

### TA-Lib Installation Issues
If TA-Lib fails to install:
- Ensure you installed the C library first (see Installation)
- Try: `pip install --no-cache-dir TA-Lib`
- On Windows, download precompiled wheel from GitHub

### Exchange Connection Errors
- Verify API keys in `.env`
- Check API key permissions on Binance
- Ensure IP is whitelisted (if configured)
- Try testnet first

### Insufficient Data
- Wait for bot to collect enough historical data
- Manually fetch data using data_manager

### ML Model Errors
- Ensure sufficient training data (>1000 candles)
- Check for NaN values in data
- Verify all indicators calculate correctly

## Performance Optimization

### For Better Results:
1. **Optimize Parameters**: Run multiple backtests with different parameters
2. **Feature Selection**: Use feature importance to select best indicators
3. **Market Conditions**: Adapt strategy to current market regime
4. **Risk Management**: Fine-tune position sizing and stops
5. **Timeframe Selection**: Test different timeframes (1h, 4h, 1d)
6. **Symbol Selection**: Some pairs perform better than others

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

⚠️ **THIS IS NOT INVESTMENT ADVICE** ⚠️

This software is for educational and informational purposes only. It is not intended as and does not constitute financial advice, investment advice, trading advice, or any other type of advice.

**Important:**
- Do not risk money which you are afraid to lose
- USE THE SOFTWARE AT YOUR OWN RISK
- THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS
- Past performance does not guarantee future results
- Trading cryptocurrencies carries a high level of risk and may not be suitable for all investors
- You should carefully consider your investment objectives, level of experience, and risk appetite
- Consult with a qualified financial advisor before making any investment decisions

**By using this software, you acknowledge that:**
1. You are using it at your own risk
2. You understand the risks involved in cryptocurrency trading
3. You will not hold the developers responsible for any losses
4. This is NOT investment advice

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review backtest results before live trading

## Acknowledgments

- **CCXT**: Cryptocurrency exchange connectivity
- **TA-Lib**: Technical analysis library
- **scikit-learn, XGBoost, LightGBM**: Machine learning
- **VADER, TextBlob**: Sentiment analysis
- **Binance**: Exchange API

## Roadmap

Future enhancements:
- [ ] Multi-symbol portfolio management
- [ ] Deep learning models (LSTM, Transformer)
- [ ] Social media sentiment (Twitter, Reddit)
- [ ] Telegram notifications
- [ ] Web dashboard for monitoring
- [ ] Additional exchanges support
- [ ] Options and futures trading
- [ ] Advanced order types (OCO, Iceberg)

---

**Happy Trading! 🚀📈**

*Remember: Only invest what you can afford to lose. Always do your own research.*

---

## ⚠️ FINAL REMINDER ⚠️

**THIS IS NOT INVESTMENT ADVICE**

This trading bot is a tool for educational purposes. Any trading decisions you make are your own responsibility. The developers of this software are not financial advisors and do not provide investment advice. Always:

- Do your own research (DYOR)
- Understand the technology and markets
- Never invest more than you can afford to lose
- Consider seeking advice from qualified financial professionals
- Test thoroughly in paper trading mode before using real money

**USE AT YOUR OWN RISK. NOT INVESTMENT ADVICE.**
