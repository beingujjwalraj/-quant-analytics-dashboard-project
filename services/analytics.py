import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from datetime import datetime, timedelta

class QuantitativeAnalytics:
    def __init__(self, db):
        self.db = db
    
    def resample_ticks(self, df, interval='1m'):
        if df.empty or len(df) < 5:
            return pd.DataFrame()
            
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            if interval.endswith('s'):
                seconds = int(interval[:-1])
                rule = f'{seconds}s'  # FIXED: Changed 'S' to 's'
            elif interval.endswith('m'):
                minutes = int(interval[:-1])
                rule = f'{minutes}min'  # FIXED: Changed 'T' to 'min'
            else:
                rule = '1min'
            
            # Use mean for OHLC if we don't have enough ticks
            if len(df) < 10:
                ohlc_df = df['price'].resample(rule).agg({
                    'open': 'first',
                    'high': 'max', 
                    'low': 'min',
                    'close': 'last'
                }).reset_index()
                volume = df['size'].resample(rule).sum().reset_index()
                result = pd.merge(ohlc_df, volume, on='timestamp')
            else:
                ohlc = df['price'].resample(rule).ohlc()
                volume = df['size'].resample(rule).sum()
                result = ohlc
                result['volume'] = volume
            
            result = result.dropna()
            return result.reset_index()
            
        except Exception as e:
            print(f"Resampling error: {e}")
            return pd.DataFrame()
    
    def calculate_basic_stats(self, df):
        if df.empty or len(df) < 2:
            return {
                'current_price': 0,
                'high': 0,
                'low': 0,
                'mean': 0,
                'std': 0,
                'volatility': 0,
                'volume': 0,
                'vwap': 0
            }
            
        prices = df['price'].values
        if len(prices) < 2:
            returns = np.array([0])
        else:
            returns = np.diff(np.log(prices))
        
        volume_sum = df['size'].sum()
        vwap = (df['price'] * df['size']).sum() / volume_sum if volume_sum > 0 else prices[-1] if len(prices) > 0 else 0
        
        return {
            'current_price': float(prices[-1]) if len(prices) > 0 else 0,
            'high': float(np.max(prices)) if len(prices) > 0 else 0,
            'low': float(np.min(prices)) if len(prices) > 0 else 0,
            'mean': float(np.mean(prices)) if len(prices) > 0 else 0,
            'std': float(np.std(prices)) if len(prices) > 0 else 0,
            'volatility': float(np.std(returns)) * 100 if len(returns) > 0 else 0,
            'volume': float(volume_sum),
            'vwap': float(vwap)
        }
    
    def pairwise_regression(self, symbol1, symbol2, timeframe='1m'):
        try:
            df1 = self.db.get_recent_ticks(symbol1, 500)  # Reduced for stability
            df2 = self.db.get_recent_ticks(symbol2, 500)
            
            if df1.empty or df2.empty or len(df1) < 10 or len(df2) < 10:
                return None
            
            df1_resampled = self.resample_ticks(df1, timeframe)
            df2_resampled = self.resample_ticks(df2, timeframe)
            
            if df1_resampled.empty or df2_resampled.empty:
                return None
            
            # Use close prices for regression
            merged = pd.merge(df1_resampled, df2_resampled, on='timestamp', suffixes=('_1', '_2'))
            
            if len(merged) < 5:
                return None
            
            # Ensure we have the close column
            if 'close_1' not in merged.columns or 'close_2' not in merged.columns:
                return None
            
            X = merged['close_1'].values
            y = merged['close_2'].values
            
            # Add constant for intercept
            X = sm.add_constant(X)
            
            # Check for valid data
            if np.any(np.isnan(X)) or np.any(np.isnan(y)):
                return None
                
            model = sm.OLS(y, X).fit()
            
            hedge_ratio = model.params[1] if len(model.params) > 1 else 0
            spread = y - hedge_ratio * X[:, 1]
            
            return {
                'hedge_ratio': float(hedge_ratio),
                'intercept': float(model.params[0]),
                'r_squared': float(model.rsquared),
                'p_value': float(model.f_pvalue) if hasattr(model, 'f_pvalue') else 0.0,
                'spread_mean': float(np.mean(spread)) if len(spread) > 0 else 0,
                'spread_std': float(np.std(spread)) if len(spread) > 0 else 0,
                'current_spread': float(spread[-1]) if len(spread) > 0 else 0
            }
            
        except Exception as e:
            print(f"Regression error: {e}")
            return None
    
    def calculate_spread_zscore(self, spread_series, window=20):
        if len(spread_series) < window or len(spread_series) < 5:
            return {
                'current_zscore': 0,
                'zscore_series': [],
                'mean': 0,
                'std': 0
            }
        
        try:
            spread_series = pd.Series(spread_series)
            rolling_mean = spread_series.rolling(window=min(window, len(spread_series))).mean()
            rolling_std = spread_series.rolling(window=min(window, len(spread_series))).std()
            zscore = (spread_series - rolling_mean) / rolling_std
            
            return {
                'current_zscore': float(zscore.iloc[-1]) if not pd.isna(zscore.iloc[-1]) else 0,
                'zscore_series': zscore.dropna().tolist(),
                'mean': float(rolling_mean.iloc[-1]) if not pd.isna(rolling_mean.iloc[-1]) else 0,
                'std': float(rolling_std.iloc[-1]) if not pd.isna(rolling_std.iloc[-1]) else 0
            }
        except Exception as e:
            print(f"Z-score calculation error: {e}")
            return {
                'current_zscore': 0,
                'zscore_series': [],
                'mean': 0,
                'std': 0
            }
    
    def adf_test(self, series):
        if len(series) < 10:
            return {
                'test_statistic': 0,
                'p_value': 1.0,
                'critical_values': {'1%': 0, '5%': 0, '10%': 0},
                'is_stationary': False
            }
            
        try:
            series_clean = pd.Series(series).dropna()
            if len(series_clean) < 10:
                return {
                    'test_statistic': 0,
                    'p_value': 1.0,
                    'critical_values': {'1%': 0, '5%': 0, '10%': 0},
                    'is_stationary': False
                }
                
            result = adfuller(series_clean)
            
            return {
                'test_statistic': float(result[0]),
                'p_value': float(result[1]),
                'critical_values': {key: float(value) for key, value in result[4].items()},
                'is_stationary': result[1] <= 0.05
            }
        except Exception as e:
            print(f"ADF test error: {e}")
            return {
                'test_statistic': 0,
                'p_value': 1.0,
                'critical_values': {'1%': 0, '5%': 0, '10%': 0},
                'is_stationary': False
            }
    
    def rolling_correlation(self, symbol1, symbol2, window=20, timeframe='1m'):
        try:
            df1 = self.db.get_recent_ticks(symbol1, 500)
            df2 = self.db.get_recent_ticks(symbol2, 500)
            
            if df1.empty or df2.empty:
                return None
            
            df1_resampled = self.resample_ticks(df1, timeframe)
            df2_resampled = self.resample_ticks(df2, timeframe)
            
            if df1_resampled.empty or df2_resampled.empty:
                return None
            
            merged = pd.merge(df1_resampled, df2_resampled, on='timestamp', suffixes=('_1', '_2'))
            
            if len(merged) < window or 'close_1' not in merged.columns or 'close_2' not in merged.columns:
                return {
                    'current_correlation': 0,
                    'correlation_series': [],
                    'mean_correlation': 0
                }
            
            corr = merged['close_1'].rolling(window=min(window, len(merged))).corr(merged['close_2'])
            
            return {
                'current_correlation': float(corr.iloc[-1]) if not pd.isna(corr.iloc[-1]) else 0,
                'correlation_series': corr.dropna().tolist(),
                'mean_correlation': float(corr.mean()) if not pd.isna(corr.mean()) else 0
            }
        except Exception as e:
            print(f"Correlation error: {e}")
            return {
                'current_correlation': 0,
                'correlation_series': [],
                'mean_correlation': 0
            }