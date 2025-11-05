# 📈 Futures Trading Guide

## Overview

The Futures Trading Bot is an advanced multi-symbol trading system that:
- **Trades Binance Futures** with up to 125x leverage
- **Manages Multiple Positions** (up to 5 concurrent trades)
- **Dynamically Discovers Opportunities** across 50+ symbols
- **Auto-adjusts Position Sizes** based on 4% risk per trade
- **Sets Automatic TP/SL** using ATR-based calculations

## 🚀 Quick Start

### Basic Usage

```bash
# Paper trading with default settings (10x leverage, 5 max positions)
python futures_bot.py --mode paper --capital 10000

# Live trading with custom leverage
python futures_bot.py --mode live --capital 5000 --leverage 20

# Custom settings
python futures_bot.py \
  --capital 10000 \
  --max-positions 5 \
  --leverage 10 \
  --risk 0.04 \
  --stop-loss-atr 2.0 \
  --take-profit-atr 3.0 \
  --interval 300
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--capital` | Initial capital in USDT | 10000 |
| `--max-positions` | Maximum concurrent positions | 5 |
| `--risk` | Risk per trade (0.04 = 4%) | 0.04 |
| `--leverage` | Leverage multiplier (1-125) | 10 |
| `--timeframe` | Trading timeframe | 1h |
| `--mode` | paper or live | paper |
| `--interval` | Scan interval (seconds) | 300 |
| `--stop-loss-atr` | Stop loss ATR multiplier | 2.0 |
| `--take-profit-atr` | Take profit ATR multiplier | 3.0 |

## 🎯 How It Works

### 1. Market Scanning

Every 5 minutes (configurable), the bot:

1. **Fetches Top Symbols** by 24h volume (top 50)
2. **Analyzes Each Symbol** for trading signals
3. **Ranks by Signal Strength** (0-100)
4. **Selects Best Opportunity** to trade

### 2. Signal Generation

Signals are generated using multiple factors:

**Bullish Signals:**
- RSI oversold (< 40)
- MACD bullish crossover
- Price above 50/200 SMA (uptrend)
- Stochastic oversold (< 30)
- Volume spike (> 1.5x average)
- Price below lower Bollinger Band
- ADX shows strong uptrend
- Bullish candlestick patterns
- ML prediction (if available)

**Bearish Signals:**
- RSI overbought (> 70)
- MACD bearish crossover
- Price below 50/200 SMA (downtrend)
- Stochastic overbought (> 70)
- Price above upper Bollinger Band
- ADX shows strong downtrend
- Bearish candlestick patterns

**Signal Strength:** Sum of all factors (capped at 100)

### 3. Position Opening

When a strong signal is found (≥60 strength):

1. **Calculate Position Size** based on:
   - Risk amount = Capital × 4%
   - Stop loss distance (entry - SL)
   - Position size = Risk amount / SL distance

2. **Set Leverage** (user configurable)

3. **Calculate TP/SL:**
   - Stop Loss = Entry ± (ATR × 2.0)
   - Take Profit = Entry ± (ATR × 3.0)
   - This gives ~1.5:1 reward-to-risk ratio

4. **Execute Orders:**
   - Market entry order
   - Stop loss order (reduce-only)
   - Take profit order (reduce-only)

### 4. Position Management

The bot continuously:

- **Monitors All Positions** every cycle
- **Updates P&L** in real-time
- **Checks Exit Conditions:**
  - Stop loss hit
  - Take profit hit
  - Liquidation risk (margin < 90%)
  - Emergency conditions
- **Closes Positions** when conditions met

## 💰 Risk Management

### Position Sizing Formula

```python
risk_amount = capital × 0.04  # 4% risk
risk_per_contract = abs(entry_price - stop_loss)
position_size = risk_amount / risk_per_contract
```

**Example:**
- Capital: $10,000
- Risk: 4% = $400
- Entry: $50,000
- Stop Loss: $49,000 (distance = $1,000)
- Position Size: $400 / $1,000 = 0.4 BTC

With 10x leverage:
- Position Value: 0.4 × $50,000 = $20,000
- Margin Required: $20,000 / 10 = $2,000
- Max Loss: $400 (4% of capital)

### Portfolio Limits

- **Max Positions:** 5 (configurable)
- **Per-Trade Risk:** 4% of capital
- **Max Exposure:** Limited by margin requirements
- **Available Capital:** Capital - Total Margin Used

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Futures Trading
ENABLE_FUTURES_TRADING=True
FUTURES_MARGIN_MODE=isolated

# Portfolio Settings
MAX_POSITIONS=5
RISK_PER_TRADE=0.04

# Leverage
DEFAULT_LEVERAGE=10
MAX_LEVERAGE=20
MIN_LEVERAGE=1

# TP/SL
ATR_MULTIPLIER_SL=2.0
ATR_MULTIPLIER_TP=3.0

# Scanner
MIN_SIGNAL_STRENGTH=60
MAX_SYMBOLS_TO_SCAN=50
SCAN_INTERVAL=300

# Safety
ENABLE_LIQUIDATION_PROTECTION=True
LIQUIDATION_MARGIN_RATIO=0.9
```

### Leverage Guidelines

| Leverage | Risk Level | Use Case |
|----------|------------|----------|
| 1-3x | Low | Conservative trading |
| 5-10x | Medium | Balanced approach |
| 10-20x | High | Aggressive trading |
| 20-50x | Very High | Expert traders only |
| 50-125x | Extreme | Not recommended |

**⚠️ Important:** Higher leverage = higher risk of liquidation!

## 📊 Example Trading Scenario

### Scenario: Bot Finds BTC Long Signal

**Market Scan Results:**
```
Symbol: BTC/USDT
Direction: LONG
Strength: 75
Current Price: $50,000
Reasons:
- RSI oversold (35)
- MACD bullish crossover
- Volume spike (2.1x)
- Price above 50 SMA (uptrend)
```

**Position Calculation:**
```
Capital: $10,000
Risk: 4% = $400
Leverage: 10x

ATR: $1,000
Stop Loss: $50,000 - ($1,000 × 2) = $48,000
Take Profit: $50,000 + ($1,000 × 3) = $53,000

Risk per BTC: $50,000 - $48,000 = $2,000
Position Size: $400 / $2,000 = 0.2 BTC

Position Value: 0.2 × $50,000 = $10,000
Margin Required: $10,000 / 10 = $1,000
```

**Orders Executed:**
1. Market Buy: 0.2 BTC @ $50,000
2. Stop Loss: Sell 0.2 BTC @ $48,000
3. Take Profit: Sell 0.2 BTC @ $53,000

**Outcomes:**

*If Take Profit Hit ($53,000):*
- Profit: 0.2 × ($53,000 - $50,000) = $600
- ROE: $600 / $1,000 = 60%
- New Capital: $10,600

*If Stop Loss Hit ($48,000):*
- Loss: 0.2 × ($50,000 - $48,000) = $400
- ROE: -$400 / $1,000 = -40%
- New Capital: $9,600

## 🎛️ Advanced Features

### Multi-Symbol Portfolio

The bot can trade up to 5 different symbols simultaneously:

```
Position 1: BTC/USDT LONG (10x) | +$250
Position 2: ETH/USDT SHORT (10x) | -$100
Position 3: SOL/USDT LONG (10x) | +$150
Position 4: MATIC/USDT LONG (10x) | +$75
Position 5: Available

Total Unrealized P&L: +$375
```

### Dynamic Symbol Selection

The bot automatically:
- Scans 50+ symbols every 5 minutes
- Excludes symbols with open positions
- Ranks by signal strength
- Opens position in best opportunity

### Isolated Margin Mode

Each position uses isolated margin:
- **Independent Risk:** One liquidation doesn't affect others
- **Controlled Exposure:** Limited loss per position
- **Portfolio Protection:** Capital preserved across failures

## 🛡️ Safety Features

All standard safety features apply to futures trading:

### 1. Emergency Stop
- Detects market crashes
- Closes all positions immediately
- Protects from cascading losses

### 2. Market Hours Filter
- Avoids stock market opening volatility
- Pauses new entries during high-risk periods

### 3. Circuit Breaker
- Trips on 15% drawdown
- Stops after 5 consecutive losses
- Forces review before resuming

### 4. Liquidation Protection
- Monitors margin levels
- Closes positions at 90% margin used
- Prevents liquidation losses

## 📈 Performance Tracking

### Portfolio Statistics

```python
{
    'initial_capital': 10000,
    'current_capital': 12500,
    'total_unrealized_pnl': 250,
    'portfolio_value': 12750,
    'margin_used': 3000,
    'available_capital': 9500,
    'open_positions': 3,
    'max_positions': 5,
    'total_trades': 15,
    'winning_trades': 10,
    'losing_trades': 5,
    'win_rate': 66.67,
    'total_return': 27.5
}
```

### Position Details

```python
{
    'symbol': 'BTC/USDT',
    'side': 'long',
    'entry_price': 50000,
    'current_price': 51000,
    'amount': 0.2,
    'leverage': 10,
    'stop_loss': 48000,
    'take_profit': 53000,
    'position_value': 10200,
    'margin_used': 1020,
    'unrealized_pnl': 200,
    'unrealized_pnl_percent': 4.0,
    'roe': 19.6
}
```

## ⚠️ Risks & Warnings

### Leverage Risks

**High Leverage = High Risk:**
- Small price movements can liquidate your position
- 10x leverage means 10% against you = 100% loss of margin
- Use lower leverage until experienced

**Liquidation Example:**
```
Entry: $50,000
Leverage: 20x
Margin: $1,000

Liquidation if price drops to ~$47,500 (only 5%!)
```

### Best Practices

1. **Start Small:**
   - Begin with low leverage (3-5x)
   - Use small capital initially
   - Increase as you gain experience

2. **Monitor Regularly:**
   - Check positions at least daily
   - Watch for news events
   - Be ready to intervene

3. **Respect Stop Losses:**
   - Never disable stop losses
   - Don't move stops further away
   - Accept losses as part of trading

4. **Diversify:**
   - Don't put all capital in one position
   - Use multiple uncorrelated symbols
   - Max 5 positions helps spread risk

5. **Paper Trade First:**
   - Test strategies without real money
   - Verify bot behavior
   - Build confidence

## 🔧 Troubleshooting

### Position Not Opening

**Check:**
- Max positions reached?
- Insufficient available capital?
- Signal strength below threshold?
- Symbol already in portfolio?

### Position Closed Unexpectedly

**Possible Reasons:**
- Stop loss hit
- Take profit hit
- Liquidation protection triggered
- Emergency stop activated
- Circuit breaker tripped

### Orders Failing

**Solutions:**
- Check API permissions (futures enabled?)
- Verify sufficient balance
- Ensure symbol is active
- Check leverage limits for symbol

## 📚 Additional Resources

### Binance Futures Guides

- [Binance Futures Docs](https://www.binance.com/en/support/faq/futures)
- [Leverage & Margin](https://www.binance.com/en/support/faq/360033162192)
- [Risk Management](https://www.binance.com/en/support/faq/360033525071)

### Learning Resources

- Understand leverage mechanics
- Learn about funding rates
- Study risk management
- Practice with paper trading

## 🎯 Tips for Success

1. **Conservative Start:** Begin with 3-5x leverage
2. **Gradual Increase:** Only increase leverage with proven success
3. **Monitor Funding:** Be aware of funding rate costs
4. **Check Liquidation:** Always know your liquidation price
5. **Use Safety Features:** Don't disable safety systems
6. **Stay Informed:** Follow crypto news and events
7. **Review Trades:** Learn from wins and losses
8. **Paper Trade:** Test extensively before going live

## 📞 Support

For issues or questions:
1. Check logs: `logs/futures_bot.log`
2. Review configuration: `.env`
3. Test in paper mode
4. Start with small capital

---

**Remember:** Futures trading is high-risk. Only trade with money you can afford to lose. The higher the leverage, the higher the risk. Always use stop losses and never trade emotionally.

**Good luck and trade safely! 🚀**
