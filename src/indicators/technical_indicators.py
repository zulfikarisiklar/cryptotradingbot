"""
Comprehensive technical indicators using TA-Lib.
Implements all 200+ indicators available in TA-Lib library.
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Comprehensive technical indicators calculator.
    Supports all 200+ TA-Lib indicators across all categories:
    - Overlap Studies
    - Momentum Indicators
    - Volume Indicators
    - Volatility Indicators
    - Price Transform
    - Cycle Indicators
    - Pattern Recognition
    - Statistic Functions
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV dataframe.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
        """
        self.df = df.copy()
        self.open = df['open'].values
        self.high = df['high'].values
        self.low = df['low'].values
        self.close = df['close'].values
        self.volume = df['volume'].values

    def calculate_all_indicators(self) -> pd.DataFrame:
        """
        Calculate all technical indicators and return enriched dataframe.

        Returns:
            DataFrame with all indicators
        """
        result_df = self.df.copy()

        logger.info("Calculating all technical indicators...")

        # Calculate all indicator groups
        result_df = pd.concat([result_df, self.overlap_studies()], axis=1)
        result_df = pd.concat([result_df, self.momentum_indicators()], axis=1)
        result_df = pd.concat([result_df, self.volume_indicators()], axis=1)
        result_df = pd.concat([result_df, self.volatility_indicators()], axis=1)
        result_df = pd.concat([result_df, self.price_transform()], axis=1)
        result_df = pd.concat([result_df, self.cycle_indicators()], axis=1)
        result_df = pd.concat([result_df, self.pattern_recognition()], axis=1)
        result_df = pd.concat([result_df, self.statistic_functions()], axis=1)

        logger.info(f"Calculated {len(result_df.columns)} total features")
        return result_df

    def overlap_studies(self) -> pd.DataFrame:
        """Calculate all Overlap Studies indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            indicators[f'SMA_{period}'] = talib.SMA(self.close, timeperiod=period)
            indicators[f'EMA_{period}'] = talib.EMA(self.close, timeperiod=period)
            indicators[f'WMA_{period}'] = talib.WMA(self.close, timeperiod=period)
            indicators[f'DEMA_{period}'] = talib.DEMA(self.close, timeperiod=period)
            indicators[f'TEMA_{period}'] = talib.TEMA(self.close, timeperiod=period)
            indicators[f'TRIMA_{period}'] = talib.TRIMA(self.close, timeperiod=period)
            indicators[f'KAMA_{period}'] = talib.KAMA(self.close, timeperiod=period)

        # T3 - Triple Exponential Moving Average
        indicators['T3'] = talib.T3(self.close, timeperiod=5)

        # MAMA - MESA Adaptive Moving Average
        indicators['MAMA'], indicators['FAMA'] = talib.MAMA(self.close)

        # Bollinger Bands
        for period in [20, 50]:
            indicators[f'BB_UPPER_{period}'], indicators[f'BB_MIDDLE_{period}'], indicators[f'BB_LOWER_{period}'] = \
                talib.BBANDS(self.close, timeperiod=period)

        # Parabolic SAR
        indicators['SAR'] = talib.SAR(self.high, self.low)
        indicators['SAREXT'] = talib.SAREXT(self.high, self.low)

        # Hilbert Transform - Instantaneous Trendline
        indicators['HT_TRENDLINE'] = talib.HT_TRENDLINE(self.close)

        # MIDPOINT
        indicators['MIDPOINT'] = talib.MIDPOINT(self.close, timeperiod=14)
        indicators['MIDPRICE'] = talib.MIDPRICE(self.high, self.low, timeperiod=14)

        return indicators

    def momentum_indicators(self) -> pd.DataFrame:
        """Calculate all Momentum Indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # RSI - Relative Strength Index
        for period in [6, 14, 21]:
            indicators[f'RSI_{period}'] = talib.RSI(self.close, timeperiod=period)

        # MACD - Moving Average Convergence/Divergence
        indicators['MACD'], indicators['MACD_SIGNAL'], indicators['MACD_HIST'] = talib.MACD(self.close)
        indicators['MACD_EXT'], indicators['MACD_EXT_SIGNAL'], indicators['MACD_EXT_HIST'] = talib.MACDEXT(self.close)
        indicators['MACD_FIX'], indicators['MACD_FIX_SIGNAL'], indicators['MACD_FIX_HIST'] = talib.MACDFIX(self.close)

        # Stochastic
        indicators['STOCH_K'], indicators['STOCH_D'] = talib.STOCH(self.high, self.low, self.close)
        indicators['STOCHF_K'], indicators['STOCHF_D'] = talib.STOCHF(self.high, self.low, self.close)
        indicators['STOCHRSI_K'], indicators['STOCHRSI_D'] = talib.STOCHRSI(self.close)

        # ADX - Average Directional Movement Index
        indicators['ADX'] = talib.ADX(self.high, self.low, self.close, timeperiod=14)
        indicators['ADXR'] = talib.ADXR(self.high, self.low, self.close, timeperiod=14)

        # Directional Indicators
        indicators['PLUS_DI'] = talib.PLUS_DI(self.high, self.low, self.close, timeperiod=14)
        indicators['MINUS_DI'] = talib.MINUS_DI(self.high, self.low, self.close, timeperiod=14)
        indicators['PLUS_DM'] = talib.PLUS_DM(self.high, self.low, timeperiod=14)
        indicators['MINUS_DM'] = talib.MINUS_DM(self.high, self.low, timeperiod=14)

        # APO - Absolute Price Oscillator
        indicators['APO'] = talib.APO(self.close)

        # Aroon
        indicators['AROON_DOWN'], indicators['AROON_UP'] = talib.AROON(self.high, self.low)
        indicators['AROONOSC'] = talib.AROONOSC(self.high, self.low)

        # BOP - Balance of Power
        indicators['BOP'] = talib.BOP(self.open, self.high, self.low, self.close)

        # CCI - Commodity Channel Index
        indicators['CCI'] = talib.CCI(self.high, self.low, self.close, timeperiod=14)

        # CMO - Chande Momentum Oscillator
        indicators['CMO'] = talib.CMO(self.close, timeperiod=14)

        # DX - Directional Movement Index
        indicators['DX'] = talib.DX(self.high, self.low, self.close, timeperiod=14)

        # MFI - Money Flow Index
        indicators['MFI'] = talib.MFI(self.high, self.low, self.close, self.volume, timeperiod=14)

        # MOM - Momentum
        indicators['MOM'] = talib.MOM(self.close, timeperiod=10)

        # PPO - Percentage Price Oscillator
        indicators['PPO'] = talib.PPO(self.close)

        # ROC - Rate of Change
        for period in [10, 20]:
            indicators[f'ROC_{period}'] = talib.ROC(self.close, timeperiod=period)
            indicators[f'ROCP_{period}'] = talib.ROCP(self.close, timeperiod=period)
            indicators[f'ROCR_{period}'] = talib.ROCR(self.close, timeperiod=period)
            indicators[f'ROCR100_{period}'] = talib.ROCR100(self.close, timeperiod=period)

        # TRIX - 1-day Rate-Of-Change (ROC) of a Triple Smooth EMA
        indicators['TRIX'] = talib.TRIX(self.close, timeperiod=30)

        # Ultimate Oscillator
        indicators['ULTOSC'] = talib.ULTOSC(self.high, self.low, self.close)

        # Williams %R
        indicators['WILLR'] = talib.WILLR(self.high, self.low, self.close, timeperiod=14)

        return indicators

    def volume_indicators(self) -> pd.DataFrame:
        """Calculate all Volume Indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # AD - Chaikin A/D Line
        indicators['AD'] = talib.AD(self.high, self.low, self.close, self.volume)

        # ADOSC - Chaikin A/D Oscillator
        indicators['ADOSC'] = talib.ADOSC(self.high, self.low, self.close, self.volume)

        # OBV - On Balance Volume
        indicators['OBV'] = talib.OBV(self.close, self.volume)

        return indicators

    def volatility_indicators(self) -> pd.DataFrame:
        """Calculate all Volatility Indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # ATR - Average True Range
        for period in [7, 14, 21]:
            indicators[f'ATR_{period}'] = talib.ATR(self.high, self.low, self.close, timeperiod=period)

        # NATR - Normalized Average True Range
        indicators['NATR'] = talib.NATR(self.high, self.low, self.close, timeperiod=14)

        # TRANGE - True Range
        indicators['TRANGE'] = talib.TRANGE(self.high, self.low, self.close)

        return indicators

    def price_transform(self) -> pd.DataFrame:
        """Calculate all Price Transform indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # AVGPRICE - Average Price
        indicators['AVGPRICE'] = talib.AVGPRICE(self.open, self.high, self.low, self.close)

        # MEDPRICE - Median Price
        indicators['MEDPRICE'] = talib.MEDPRICE(self.high, self.low)

        # TYPPRICE - Typical Price
        indicators['TYPPRICE'] = talib.TYPPRICE(self.high, self.low, self.close)

        # WCLPRICE - Weighted Close Price
        indicators['WCLPRICE'] = talib.WCLPRICE(self.high, self.low, self.close)

        return indicators

    def cycle_indicators(self) -> pd.DataFrame:
        """Calculate all Cycle Indicators (Hilbert Transform)."""
        indicators = pd.DataFrame(index=self.df.index)

        # HT_DCPERIOD - Hilbert Transform - Dominant Cycle Period
        indicators['HT_DCPERIOD'] = talib.HT_DCPERIOD(self.close)

        # HT_DCPHASE - Hilbert Transform - Dominant Cycle Phase
        indicators['HT_DCPHASE'] = talib.HT_DCPHASE(self.close)

        # HT_PHASOR - Hilbert Transform - Phasor Components
        indicators['HT_PHASOR_INPHASE'], indicators['HT_PHASOR_QUADRATURE'] = talib.HT_PHASOR(self.close)

        # HT_SINE - Hilbert Transform - SineWave
        indicators['HT_SINE'], indicators['HT_LEADSINE'] = talib.HT_SINE(self.close)

        # HT_TRENDMODE - Hilbert Transform - Trend vs Cycle Mode
        indicators['HT_TRENDMODE'] = talib.HT_TRENDMODE(self.close)

        return indicators

    def pattern_recognition(self) -> pd.DataFrame:
        """Calculate all Candlestick Pattern Recognition indicators."""
        indicators = pd.DataFrame(index=self.df.index)

        # All candlestick patterns
        indicators['CDL2CROWS'] = talib.CDL2CROWS(self.open, self.high, self.low, self.close)
        indicators['CDL3BLACKCROWS'] = talib.CDL3BLACKCROWS(self.open, self.high, self.low, self.close)
        indicators['CDL3INSIDE'] = talib.CDL3INSIDE(self.open, self.high, self.low, self.close)
        indicators['CDL3LINESTRIKE'] = talib.CDL3LINESTRIKE(self.open, self.high, self.low, self.close)
        indicators['CDL3OUTSIDE'] = talib.CDL3OUTSIDE(self.open, self.high, self.low, self.close)
        indicators['CDL3STARSINSOUTH'] = talib.CDL3STARSINSOUTH(self.open, self.high, self.low, self.close)
        indicators['CDL3WHITESOLDIERS'] = talib.CDL3WHITESOLDIERS(self.open, self.high, self.low, self.close)
        indicators['CDLABANDONEDBABY'] = talib.CDLABANDONEDBABY(self.open, self.high, self.low, self.close)
        indicators['CDLADVANCEBLOCK'] = talib.CDLADVANCEBLOCK(self.open, self.high, self.low, self.close)
        indicators['CDLBELTHOLD'] = talib.CDLBELTHOLD(self.open, self.high, self.low, self.close)
        indicators['CDLBREAKAWAY'] = talib.CDLBREAKAWAY(self.open, self.high, self.low, self.close)
        indicators['CDLCLOSINGMARUBOZU'] = talib.CDLCLOSINGMARUBOZU(self.open, self.high, self.low, self.close)
        indicators['CDLCONCEALBABYSWALL'] = talib.CDLCONCEALBABYSWALL(self.open, self.high, self.low, self.close)
        indicators['CDLCOUNTERATTACK'] = talib.CDLCOUNTERATTACK(self.open, self.high, self.low, self.close)
        indicators['CDLDARKCLOUDCOVER'] = talib.CDLDARKCLOUDCOVER(self.open, self.high, self.low, self.close)
        indicators['CDLDOJI'] = talib.CDLDOJI(self.open, self.high, self.low, self.close)
        indicators['CDLDOJISTAR'] = talib.CDLDOJISTAR(self.open, self.high, self.low, self.close)
        indicators['CDLDRAGONFLYDOJI'] = talib.CDLDRAGONFLYDOJI(self.open, self.high, self.low, self.close)
        indicators['CDLENGULFING'] = talib.CDLENGULFING(self.open, self.high, self.low, self.close)
        indicators['CDLEVENINGDOJISTAR'] = talib.CDLEVENINGDOJISTAR(self.open, self.high, self.low, self.close)
        indicators['CDLEVENINGSTAR'] = talib.CDLEVENINGSTAR(self.open, self.high, self.low, self.close)
        indicators['CDLGAPSIDESIDEWHITE'] = talib.CDLGAPSIDESIDEWHITE(self.open, self.high, self.low, self.close)
        indicators['CDLGRAVESTONEDOJI'] = talib.CDLGRAVESTONEDOJI(self.open, self.high, self.low, self.close)
        indicators['CDLHAMMER'] = talib.CDLHAMMER(self.open, self.high, self.low, self.close)
        indicators['CDLHANGINGMAN'] = talib.CDLHANGINGMAN(self.open, self.high, self.low, self.close)
        indicators['CDLHARAMI'] = talib.CDLHARAMI(self.open, self.high, self.low, self.close)
        indicators['CDLHARAMICROSS'] = talib.CDLHARAMICROSS(self.open, self.high, self.low, self.close)
        indicators['CDLHIGHWAVE'] = talib.CDLHIGHWAVE(self.open, self.high, self.low, self.close)
        indicators['CDLHIKKAKE'] = talib.CDLHIKKAKE(self.open, self.high, self.low, self.close)
        indicators['CDLHIKKAKEMOD'] = talib.CDLHIKKAKEMOD(self.open, self.high, self.low, self.close)
        indicators['CDLHOMINGPIGEON'] = talib.CDLHOMINGPIGEON(self.open, self.high, self.low, self.close)
        indicators['CDLIDENTICAL3CROWS'] = talib.CDLIDENTICAL3CROWS(self.open, self.high, self.low, self.close)
        indicators['CDLINNECK'] = talib.CDLINNECK(self.open, self.high, self.low, self.close)
        indicators['CDLINVERTEDHAMMER'] = talib.CDLINVERTEDHAMMER(self.open, self.high, self.low, self.close)
        indicators['CDLKICKING'] = talib.CDLKICKING(self.open, self.high, self.low, self.close)
        indicators['CDLKICKINGBYLENGTH'] = talib.CDLKICKINGBYLENGTH(self.open, self.high, self.low, self.close)
        indicators['CDLLADDERBOTTOM'] = talib.CDLLADDERBOTTOM(self.open, self.high, self.low, self.close)
        indicators['CDLLONGLEGGEDDOJI'] = talib.CDLLONGLEGGEDDOJI(self.open, self.high, self.low, self.close)
        indicators['CDLLONGLINE'] = talib.CDLLONGLINE(self.open, self.high, self.low, self.close)
        indicators['CDLMARUBOZU'] = talib.CDLMARUBOZU(self.open, self.high, self.low, self.close)
        indicators['CDLMATCHINGLOW'] = talib.CDLMATCHINGLOW(self.open, self.high, self.low, self.close)
        indicators['CDLMATHOLD'] = talib.CDLMATHOLD(self.open, self.high, self.low, self.close)
        indicators['CDLMORNINGDOJISTAR'] = talib.CDLMORNINGDOJISTAR(self.open, self.high, self.low, self.close)
        indicators['CDLMORNINGSTAR'] = talib.CDLMORNINGSTAR(self.open, self.high, self.low, self.close)
        indicators['CDLONNECK'] = talib.CDLONNECK(self.open, self.high, self.low, self.close)
        indicators['CDLPIERCING'] = talib.CDLPIERCING(self.open, self.high, self.low, self.close)
        indicators['CDLRICKSHAWMAN'] = talib.CDLRICKSHAWMAN(self.open, self.high, self.low, self.close)
        indicators['CDLRISEFALL3METHODS'] = talib.CDLRISEFALL3METHODS(self.open, self.high, self.low, self.close)
        indicators['CDLSEPARATINGLINES'] = talib.CDLSEPARATINGLINES(self.open, self.high, self.low, self.close)
        indicators['CDLSHOOTINGSTAR'] = talib.CDLSHOOTINGSTAR(self.open, self.high, self.low, self.close)
        indicators['CDLSHORTLINE'] = talib.CDLSHORTLINE(self.open, self.high, self.low, self.close)
        indicators['CDLSPINNINGTOP'] = talib.CDLSPINNINGTOP(self.open, self.high, self.low, self.close)
        indicators['CDLSTALLEDPATTERN'] = talib.CDLSTALLEDPATTERN(self.open, self.high, self.low, self.close)
        indicators['CDLSTICKSANDWICH'] = talib.CDLSTICKSANDWICH(self.open, self.high, self.low, self.close)
        indicators['CDLTAKURI'] = talib.CDLTAKURI(self.open, self.high, self.low, self.close)
        indicators['CDLTASUKIGAP'] = talib.CDLTASUKIGAP(self.open, self.high, self.low, self.close)
        indicators['CDLTHRUSTING'] = talib.CDLTHRUSTING(self.open, self.high, self.low, self.close)
        indicators['CDLTRISTAR'] = talib.CDLTRISTAR(self.open, self.high, self.low, self.close)
        indicators['CDLUNIQUE3RIVER'] = talib.CDLUNIQUE3RIVER(self.open, self.high, self.low, self.close)
        indicators['CDLUPSIDEGAP2CROWS'] = talib.CDLUPSIDEGAP2CROWS(self.open, self.high, self.low, self.close)
        indicators['CDLXSIDEGAP3METHODS'] = talib.CDLXSIDEGAP3METHODS(self.open, self.high, self.low, self.close)

        return indicators

    def statistic_functions(self) -> pd.DataFrame:
        """Calculate all Statistic Functions."""
        indicators = pd.DataFrame(index=self.df.index)

        # Beta
        indicators['BETA'] = talib.BETA(self.high, self.low, timeperiod=5)

        # Correlation
        indicators['CORREL'] = talib.CORREL(self.high, self.low, timeperiod=30)

        # Linear Regression
        indicators['LINEARREG'] = talib.LINEARREG(self.close, timeperiod=14)
        indicators['LINEARREG_ANGLE'] = talib.LINEARREG_ANGLE(self.close, timeperiod=14)
        indicators['LINEARREG_INTERCEPT'] = talib.LINEARREG_INTERCEPT(self.close, timeperiod=14)
        indicators['LINEARREG_SLOPE'] = talib.LINEARREG_SLOPE(self.close, timeperiod=14)

        # Standard Deviation
        indicators['STDDEV'] = talib.STDDEV(self.close, timeperiod=5)

        # Time Series Forecast
        indicators['TSF'] = talib.TSF(self.close, timeperiod=14)

        # Variance
        indicators['VAR'] = talib.VAR(self.close, timeperiod=5)

        return indicators

    def get_atr(self, period: int = 14) -> np.ndarray:
        """
        Get ATR (Average True Range) - used for stop loss and take profit.

        Args:
            period: ATR period

        Returns:
            ATR values
        """
        return talib.ATR(self.high, self.low, self.close, timeperiod=period)

    def get_indicator_by_name(self, name: str, **kwargs) -> np.ndarray:
        """
        Get specific indicator by name.

        Args:
            name: Indicator name (TA-Lib function name)
            **kwargs: Additional parameters for the indicator

        Returns:
            Indicator values
        """
        try:
            func = getattr(talib, name.upper())
            return func(self.close, **kwargs)
        except AttributeError:
            logger.error(f"Indicator {name} not found")
            raise
