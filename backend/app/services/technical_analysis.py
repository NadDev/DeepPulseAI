"""
Technical Analysis Service
Calculates technical indicators (RSI, MACD, Bollinger Bands, EMA, etc.)
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
import statistics

logger = logging.getLogger(__name__)


class TechnicalAnalysis:
    """
    Provides technical analysis indicators for trading
    """
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Simple Moving Average
        
        Args:
            prices: List of prices
            period: SMA period (e.g., 20, 50, 200)
            
        Returns:
            List of SMA values (with None for initial period)
        """
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                window = prices[i - period + 1:i + 1]
                sma.append(statistics.mean(window))
        return sma
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Exponential Moving Average
        
        Args:
            prices: List of prices
            period: EMA period
            
        Returns:
            List of EMA values
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        ema = []
        multiplier = 2 / (period + 1)
        
        # First EMA is SMA
        first_ema = statistics.mean(prices[:period])
        ema.append(first_ema)
        
        for i in range(period, len(prices)):
            next_ema = prices[i] * multiplier + ema[-1] * (1 - multiplier)
            ema.append(next_ema)
        
        # Fill initial values with None
        return [None] * (period - 1) + ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Calculate Relative Strength Index
        
        Args:
            prices: List of prices
            period: RSI period (default 14)
            
        Returns:
            List of RSI values (0-100)
        """
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        rsi = [None] * (period)
        gains = []
        losses = []
        
        # Calculate gains and losses
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))
        
        # Calculate average gain and loss
        avg_gain = statistics.mean(gains[:period])
        avg_loss = statistics.mean(losses[:period])
        
        if avg_loss == 0:
            rsi.append(100 if avg_gain > 0 else 50)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
        
        # Calculate RSI for remaining values
        for i in range(period + 1, len(prices)):
            gain = max(prices[i] - prices[i-1], 0)
            loss = abs(min(prices[i] - prices[i-1], 0))
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                rsi.append(100 if avg_gain > 0 else 50)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: List of prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        ema_fast = TechnicalAnalysis.calculate_ema(prices, fast)
        ema_slow = TechnicalAnalysis.calculate_ema(prices, slow)
        
        # MACD line
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        # Signal line (EMA of MACD)
        macd_values = [x for x in macd_line if x is not None]
        signal_line = [None] * len(macd_line)
        
        if len(macd_values) >= signal:
            signal_ema = TechnicalAnalysis.calculate_ema(macd_values, signal)
            signal_idx = 0
            for i in range(len(macd_line)):
                if macd_line[i] is not None:
                    if signal_idx < len(signal_ema) and signal_ema[signal_idx] is not None:
                        signal_line[i] = signal_ema[signal_idx]
                    signal_idx += 1
        
        # Histogram
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram.append(macd_line[i] - signal_line[i])
            else:
                histogram.append(None)
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """
        Calculate Bollinger Bands
        
        Args:
            prices: List of prices
            period: SMA period
            std_dev: Number of standard deviations
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        middle_band = TechnicalAnalysis.calculate_sma(prices, period)
        
        upper_band = [None] * len(prices)
        lower_band = [None] * len(prices)
        
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            std = statistics.stdev(window)
            
            if middle_band[i] is not None:
                upper_band[i] = middle_band[i] + (std * std_dev)
                lower_band[i] = middle_band[i] - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_atr(
        candles: List[Dict[str, float]],
        period: int = 14
    ) -> List[Optional[float]]:
        """
        Calculate Average True Range (ATR)
        
        Args:
            candles: List of candle data with high, low, close
            period: ATR period
            
        Returns:
            List of ATR values
        """
        if len(candles) < period:
            return [None] * len(candles)
        
        tr_values = []
        
        # Calculate True Range
        for i in range(len(candles)):
            if i == 0:
                tr = candles[i]['high'] - candles[i]['low']
            else:
                tr1 = candles[i]['high'] - candles[i]['low']
                tr2 = abs(candles[i]['high'] - candles[i-1]['close'])
                tr3 = abs(candles[i]['low'] - candles[i-1]['close'])
                tr = max(tr1, tr2, tr3)
            
            tr_values.append(tr)
        
        # Calculate ATR (SMA of TR)
        atr = []
        for i in range(len(tr_values)):
            if i < period - 1:
                atr.append(None)
            else:
                atr.append(statistics.mean(tr_values[i - period + 1:i + 1]))
        
        return atr
    
    @staticmethod
    def analyze_trend(prices: List[float]) -> str:
        """
        Analyze price trend
        
        Args:
            prices: List of prices
            
        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if len(prices) < 10:
            return 'sideways'
        
        # Compare recent prices with older prices
        recent_avg = statistics.mean(prices[-5:])
        older_avg = statistics.mean(prices[-20:-15])
        
        change_percent = ((recent_avg - older_avg) / older_avg) * 100
        
        if change_percent > 2:
            return 'uptrend'
        elif change_percent < -2:
            return 'downtrend'
        else:
            return 'sideways'
    
    @staticmethod
    def get_support_resistance(prices: List[float]) -> Tuple[float, float]:
        """
        Calculate support and resistance levels
        
        Args:
            prices: List of prices
            
        Returns:
            Tuple of (support, resistance)
        """
        min_price = min(prices[-50:]) if len(prices) >= 50 else min(prices)
        max_price = max(prices[-50:]) if len(prices) >= 50 else max(prices)
        
        return min_price, max_price

    # ============ SPRINT 2: ELLIOTT WAVE ============
    @staticmethod
    def detect_elliott_waves(prices: List[float], candles: List[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Detect Elliott Wave patterns in price data
        
        Elliott Wave Theory:
        - 5 impulse waves (1-2-3-4-5) in the trend direction
        - 3 corrective waves (A-B-C) against the trend
        
        Args:
            prices: List of closing prices
            candles: Optional candle data for more precision
            
        Returns:
            Dictionary with wave analysis
        """
        if len(prices) < 50:
            return {"status": "insufficient_data", "waves": []}
        
        # Find local extrema (peaks and troughs)
        extrema = TechnicalAnalysis._find_extrema(prices, window=5)
        
        # Analyze wave structure
        waves = []
        current_wave = None
        wave_count = 0
        
        for i, (idx, price, extrema_type) in enumerate(extrema):
            if i == 0:
                current_wave = {"start_idx": idx, "start_price": price, "type": extrema_type}
                continue
            
            # Determine wave number based on pattern
            prev_extrema = extrema[i - 1]
            move = price - prev_extrema[1]
            move_pct = (move / prev_extrema[1]) * 100
            
            wave_count += 1
            wave_num = wave_count % 8  # 5 impulse + 3 corrective = 8 wave cycle
            
            wave_label = TechnicalAnalysis._get_wave_label(wave_num)
            
            waves.append({
                "wave": wave_label,
                "start_idx": prev_extrema[0],
                "end_idx": idx,
                "start_price": prev_extrema[1],
                "end_price": price,
                "move_percent": round(move_pct, 2),
                "type": "impulse" if wave_num <= 5 else "corrective"
            })
        
        # Analyze current position in wave cycle
        current_position = TechnicalAnalysis._analyze_wave_position(waves, prices[-1])
        
        # Predict next wave
        prediction = TechnicalAnalysis._predict_next_wave(waves, prices[-1])
        
        return {
            "status": "detected",
            "wave_count": len(waves),
            "waves": waves[-10:],  # Last 10 waves
            "current_position": current_position,
            "prediction": prediction,
            "confidence": min(0.9, len(waves) / 20)  # More waves = more confidence
        }
    
    @staticmethod
    def _find_extrema(prices: List[float], window: int = 5) -> List[Tuple[int, float, str]]:
        """Find local minima and maxima"""
        extrema = []
        
        for i in range(window, len(prices) - window):
            local_window = prices[i - window:i + window + 1]
            
            if prices[i] == max(local_window):
                extrema.append((i, prices[i], "peak"))
            elif prices[i] == min(local_window):
                extrema.append((i, prices[i], "trough"))
        
        return extrema
    
    @staticmethod
    def _get_wave_label(wave_num: int) -> str:
        """Get Elliott Wave label"""
        labels = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "A", 7: "B", 0: "C"}
        return labels.get(wave_num, str(wave_num))
    
    @staticmethod
    def _analyze_wave_position(waves: List[Dict], current_price: float) -> Dict[str, Any]:
        """Analyze current position in wave cycle"""
        if not waves:
            return {"wave": "unknown", "phase": "unknown"}
        
        last_wave = waves[-1]
        wave_label = last_wave["wave"]
        
        # Determine phase
        if wave_label in ["1", "2", "3", "4", "5"]:
            phase = "impulse"
        else:
            phase = "corrective"
        
        # Calculate position within wave
        if last_wave["end_price"] != last_wave["start_price"]:
            progress = (current_price - last_wave["start_price"]) / (last_wave["end_price"] - last_wave["start_price"])
        else:
            progress = 0
        
        return {
            "current_wave": wave_label,
            "phase": phase,
            "progress": round(min(1.0, max(0, progress)), 2),
            "trend": "bullish" if last_wave["move_percent"] > 0 else "bearish"
        }
    
    @staticmethod
    def _predict_next_wave(waves: List[Dict], current_price: float) -> Dict[str, Any]:
        """Predict the next wave based on Elliott Wave theory"""
        if not waves:
            return {"next_wave": "1", "direction": "up", "confidence": 0.3}
        
        last_wave = waves[-1]["wave"]
        
        predictions = {
            "1": {"next": "2", "direction": "down", "target_retracement": 0.382},
            "2": {"next": "3", "direction": "up", "target_extension": 1.618},
            "3": {"next": "4", "direction": "down", "target_retracement": 0.382},
            "4": {"next": "5", "direction": "up", "target_extension": 1.0},
            "5": {"next": "A", "direction": "down", "target_retracement": 0.5},
            "A": {"next": "B", "direction": "up", "target_retracement": 0.5},
            "B": {"next": "C", "direction": "down", "target_extension": 1.0},
            "C": {"next": "1", "direction": "up", "target_extension": 1.618}
        }
        
        pred = predictions.get(last_wave, {"next": "1", "direction": "up"})
        
        # Calculate target price
        if len(waves) >= 2:
            last_move = abs(waves[-1]["end_price"] - waves[-1]["start_price"])
            if "target_retracement" in pred:
                target_move = last_move * pred["target_retracement"]
            else:
                target_move = last_move * pred.get("target_extension", 1.0)
            
            if pred["direction"] == "up":
                target_price = current_price + target_move
            else:
                target_price = current_price - target_move
        else:
            target_price = current_price
        
        return {
            "next_wave": pred["next"],
            "direction": pred["direction"],
            "target_price": round(target_price, 2),
            "confidence": 0.6 if len(waves) > 5 else 0.4
        }

    # ============ SPRINT 2: FIBONACCI ============
    @staticmethod
    def calculate_fibonacci_retracements(
        high: float, 
        low: float, 
        trend: str = "uptrend"
    ) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels
        
        Args:
            high: Swing high price
            low: Swing low price
            trend: 'uptrend' or 'downtrend'
            
        Returns:
            Dictionary of Fibonacci levels
        """
        diff = high - low
        
        # Standard Fibonacci levels
        fib_levels = {
            "0.0": 0.0,
            "0.236": 0.236,
            "0.382": 0.382,
            "0.5": 0.5,
            "0.618": 0.618,
            "0.786": 0.786,
            "1.0": 1.0
        }
        
        result = {}
        
        if trend == "uptrend":
            # Retracements from high
            for level_name, level in fib_levels.items():
                result[level_name] = round(high - (diff * level), 2)
        else:
            # Retracements from low
            for level_name, level in fib_levels.items():
                result[level_name] = round(low + (diff * level), 2)
        
        return result
    
    @staticmethod
    def calculate_fibonacci_extensions(
        swing_low: float,
        swing_high: float,
        retracement_low: float
    ) -> Dict[str, float]:
        """
        Calculate Fibonacci extension levels
        
        Args:
            swing_low: Initial swing low
            swing_high: Swing high
            retracement_low: Retracement low point
            
        Returns:
            Dictionary of extension levels
        """
        wave1 = swing_high - swing_low
        
        extension_levels = {
            "1.0": 1.0,
            "1.272": 1.272,
            "1.414": 1.414,
            "1.618": 1.618,
            "2.0": 2.0,
            "2.618": 2.618,
            "3.618": 3.618
        }
        
        result = {}
        for level_name, level in extension_levels.items():
            result[level_name] = round(retracement_low + (wave1 * level), 2)
        
        return result
    
    @staticmethod
    def get_fibonacci_analysis(prices: List[float]) -> Dict[str, Any]:
        """
        Complete Fibonacci analysis for price data
        
        Args:
            prices: List of closing prices
            
        Returns:
            Complete Fibonacci analysis
        """
        if len(prices) < 20:
            return {"status": "insufficient_data"}
        
        # Find recent swing points
        recent_prices = prices[-100:] if len(prices) >= 100 else prices
        
        swing_high = max(recent_prices)
        swing_low = min(recent_prices)
        high_idx = recent_prices.index(swing_high)
        low_idx = recent_prices.index(swing_low)
        
        # Determine trend
        if high_idx > low_idx:
            trend = "uptrend"
        else:
            trend = "downtrend"
        
        # Calculate retracements
        retracements = TechnicalAnalysis.calculate_fibonacci_retracements(
            swing_high, swing_low, trend
        )
        
        # Current price position
        current_price = prices[-1]
        
        # Find nearest Fibonacci levels
        nearest_support = None
        nearest_resistance = None
        
        sorted_levels = sorted(retracements.values())
        for level in sorted_levels:
            if level < current_price:
                nearest_support = level
            if level > current_price and nearest_resistance is None:
                nearest_resistance = level
        
        return {
            "status": "analyzed",
            "trend": trend,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "current_price": current_price,
            "retracement_levels": retracements,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "position_in_range": round((current_price - swing_low) / (swing_high - swing_low), 3) if swing_high != swing_low else 0.5
        }

    # ============ SPRINT 2: ICHIMOKU CLOUD ============
    @staticmethod
    def calculate_ichimoku(candles: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Calculate Ichimoku Cloud indicators
        
        Args:
            candles: List of candle data with high, low, close
            
        Returns:
            Ichimoku indicators
        """
        if len(candles) < 52:
            return {"status": "insufficient_data"}
        
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        
        # Tenkan-sen (Conversion Line) - 9 period
        tenkan_high = max(highs[-9:])
        tenkan_low = min(lows[-9:])
        tenkan_sen = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line) - 26 period
        kijun_high = max(highs[-26:])
        kijun_low = min(lows[-26:])
        kijun_sen = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_span_a = (tenkan_sen + kijun_sen) / 2
        
        # Senkou Span B (Leading Span B) - 52 period
        senkou_high = max(highs[-52:])
        senkou_low = min(lows[-52:])
        senkou_span_b = (senkou_high + senkou_low) / 2
        
        # Chikou Span (Lagging Span) - Current close shifted 26 periods back
        chikou_span = closes[-1]
        
        # Determine cloud color and position
        cloud_top = max(senkou_span_a, senkou_span_b)
        cloud_bottom = min(senkou_span_a, senkou_span_b)
        current_price = closes[-1]
        
        if current_price > cloud_top:
            cloud_position = "above"
            signal = "bullish"
        elif current_price < cloud_bottom:
            cloud_position = "below"
            signal = "bearish"
        else:
            cloud_position = "inside"
            signal = "neutral"
        
        return {
            "status": "calculated",
            "tenkan_sen": round(tenkan_sen, 2),
            "kijun_sen": round(kijun_sen, 2),
            "senkou_span_a": round(senkou_span_a, 2),
            "senkou_span_b": round(senkou_span_b, 2),
            "chikou_span": round(chikou_span, 2),
            "cloud_top": round(cloud_top, 2),
            "cloud_bottom": round(cloud_bottom, 2),
            "cloud_position": cloud_position,
            "signal": signal,
            "tk_cross": "bullish" if tenkan_sen > kijun_sen else "bearish"
        }


# Utility function to create analysis package
def create_technical_analysis_package(
    prices: List[float],
    candles: List[Dict[str, float]]
) -> Dict[str, Any]:
    """
    Create a complete technical analysis package
    
    Args:
        prices: List of closing prices
        candles: List of candle data
        
    Returns:
        Dictionary with all indicators
    """
    ta = TechnicalAnalysis()
    
    rsi = ta.calculate_rsi(prices)
    ema_12 = ta.calculate_ema(prices, 12)
    ema_26 = ta.calculate_ema(prices, 26)
    macd, signal, histogram = ta.calculate_macd(prices)
    upper_bb, middle_bb, lower_bb = ta.calculate_bollinger_bands(prices)
    atr = ta.calculate_atr(candles)
    trend = ta.analyze_trend(prices)
    support, resistance = ta.get_support_resistance(prices)
    
    return {
        "rsi": rsi[-1],
        "ema_12": ema_12[-1],
        "ema_26": ema_26[-1],
        "macd": macd[-1],
        "signal": signal[-1],
        "histogram": histogram[-1],
        "bollinger_upper": upper_bb[-1],
        "bollinger_middle": middle_bb[-1],
        "bollinger_lower": lower_bb[-1],
        "atr": atr[-1],
        "trend": trend,
        "support": support,
        "resistance": resistance,
    }
