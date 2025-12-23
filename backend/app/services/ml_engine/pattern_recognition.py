"""
==============================================
ML ENGINE - Transformer Pattern Recognition
==============================================

Détecte les patterns chartistes (Head & Shoulders, Wedge, Flag, etc.)
"""

import numpy as np
from typing import Dict, List, Optional
from enum import Enum


class ChartPattern(str, Enum):
    """Patterns détectables"""
    HEAD_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    WEDGE_UP = "wedge_up"
    WEDGE_DOWN = "wedge_down"
    FLAG = "flag"
    PENNANT = "pennant"
    TRIANGLE = "triangle"
    BREAKOUT = "breakout"
    BREAKOWN = "breakdown"


class PatternRecognition:
    """Détecte les patterns chartistes avec Transformer-like approach"""
    
    def __init__(self):
        self.lookback = 50  # Regarder 50 candles en arrière
    
    def detect_patterns(self, prices: List[float]) -> List[Dict]:
        """
        Détecte les patterns dans les données
        
        Args:
            prices: Liste des prix (derniers 100+ candles)
        
        Returns:
            Liste des patterns détectés avec confiance
        """
        prices = np.array(prices)
        if len(prices) < self.lookback:
            return []
        
        patterns = []
        
        # Tester tous les patterns
        patterns.extend(self._detect_head_shoulders(prices))
        patterns.extend(self._detect_double_tops_bottoms(prices))
        patterns.extend(self._detect_wedges(prices))
        patterns.extend(self._detect_flags(prices))
        patterns.extend(self._detect_breakouts(prices))
        
        # Trier par confiance décroissante
        patterns.sort(key=lambda p: p["confidence"], reverse=True)
        
        return patterns
    
    def _detect_head_shoulders(self, prices: np.ndarray) -> List[Dict]:
        """Détecte Head & Shoulders / Inverse H&S"""
        patterns = []
        
        # Chercher locaux max/min
        local_max = self._find_local_extrema(prices, "max")
        local_min = self._find_local_extrema(prices, "min")
        
        # Pattern H&S = 3 peaks (left < head > right)
        for i in range(len(local_max) - 2):
            idx1, idx2, idx3 = local_max[i], local_max[i+1], local_max[i+2]
            
            # Vérifier la forme: left < head > right
            if prices[idx1] < prices[idx2] > prices[idx3]:
                # Calculer la confiance
                confidence = self._calculate_pattern_confidence(
                    prices, [idx1, idx2, idx3]
                )
                
                if confidence > 0.6:
                    patterns.append({
                        "pattern": ChartPattern.HEAD_SHOULDERS,
                        "confidence": confidence,
                        "indices": [int(idx1), int(idx2), int(idx3)],
                        "target_price": np.min(prices[idx1:idx3+1]),
                        "entry_zone": self._calculate_entry_zone(prices[idx1:idx3+1])
                    })
        
        return patterns
    
    def _detect_double_tops_bottoms(self, prices: np.ndarray) -> List[Dict]:
        """Détecte Double Top / Double Bottom"""
        patterns = []
        
        local_max = self._find_local_extrema(prices, "max", window=5)
        local_min = self._find_local_extrema(prices, "min", window=5)
        
        # Double Top = 2 peaks presque égaux
        for i in range(len(local_max) - 1):
            idx1, idx2 = local_max[i], local_max[i+1]
            peak1, peak2 = prices[idx1], prices[idx2]
            
            # Vérifier similitude
            similarity = 1 - abs(peak1 - peak2) / max(peak1, peak2)
            
            if similarity > 0.95:  # Presque identiques
                confidence = min(similarity, 0.85)
                
                patterns.append({
                    "pattern": ChartPattern.DOUBLE_TOP,
                    "confidence": confidence,
                    "indices": [int(idx1), int(idx2)],
                    "target_price": np.min(prices[idx1:idx2+1]),
                    "entry_zone": self._calculate_entry_zone(prices[idx1:idx2+1])
                })
        
        # Double Bottom = 2 troughs presque égaux
        for i in range(len(local_min) - 1):
            idx1, idx2 = local_min[i], local_min[i+1]
            trough1, trough2 = prices[idx1], prices[idx2]
            
            similarity = 1 - abs(trough1 - trough2) / max(trough1, trough2)
            
            if similarity > 0.95:
                confidence = min(similarity, 0.85)
                
                patterns.append({
                    "pattern": ChartPattern.DOUBLE_BOTTOM,
                    "confidence": confidence,
                    "indices": [int(idx1), int(idx2)],
                    "target_price": np.max(prices[idx1:idx2+1]),
                    "entry_zone": self._calculate_entry_zone(prices[idx1:idx2+1])
                })
        
        return patterns
    
    def _detect_wedges(self, prices: np.ndarray) -> List[Dict]:
        """Détecte Wedges (Rising / Falling)"""
        patterns = []
        
        window = 20
        
        for i in range(len(prices) - window):
            segment = prices[i:i+window]
            
            # Calculer les ligne de trend
            x = np.arange(len(segment))
            
            # Fit polynomials
            upper_line = np.polyfit(x, segment, 1)
            lower_line = np.polyfit(x, -segment, 1)
            
            # Calculer la convergence
            first_spread = segment[0] - (-segment[0])
            last_spread = segment[-1] - (-segment[-1])
            convergence = (first_spread - last_spread) / first_spread
            
            # Wedge = convergence significative
            if 0.3 < convergence < 0.9:
                # Rising wedge = prix monte mais range se réduit
                if upper_line[0] > 0:
                    pattern_type = ChartPattern.WEDGE_UP
                else:
                    pattern_type = ChartPattern.WEDGE_DOWN
                
                confidence = 0.6 + (convergence * 0.25)
                
                patterns.append({
                    "pattern": pattern_type,
                    "confidence": min(confidence, 0.85),
                    "indices": [int(i), int(i+window)],
                    "target_price": segment[-1] * (1 - convergence),
                    "entry_zone": [np.min(segment), np.max(segment)]
                })
        
        return patterns
    
    def _detect_flags(self, prices: np.ndarray) -> List[Dict]:
        """Détecte Flags et Pennants"""
        patterns = []
        
        window = 15
        
        for i in range(len(prices) - window):
            segment = prices[i:i+window]
            
            # Flag = petite consolidation après forte tendance
            # Volatilité réduite
            volatility = np.std(segment)
            full_volatility = np.std(prices)
            
            volatility_ratio = volatility / full_volatility if full_volatility > 0 else 1
            
            # Chercher une tendance avant le flag
            if i > 0:
                pre_segment = prices[max(0, i-10):i]
                pre_volatility = np.std(pre_segment)
                
                # Flag = volatilité pré-flag > volatilité du flag
                if pre_volatility > volatility and volatility_ratio < 0.6:
                    confidence = 1 - volatility_ratio
                    
                    patterns.append({
                        "pattern": ChartPattern.FLAG,
                        "confidence": min(confidence, 0.8),
                        "indices": [int(i), int(i+window)],
                        "target_price": segment[-1] + (segment[-1] - np.mean(pre_segment)),
                        "entry_zone": self._calculate_entry_zone(segment)
                    })
        
        return patterns
    
    def _detect_breakouts(self, prices: np.ndarray) -> List[Dict]:
        """Détecte les breakouts / breakdowns"""
        patterns = []
        
        # Calculer les support/resistance
        window = 20
        support = np.min(prices[-window:])
        resistance = np.max(prices[-window:])
        
        current_price = prices[-1]
        
        # Breakout = prix > resistance de manière significative
        breakout_threshold = (resistance - support) * 0.02  # 2% du range
        
        if current_price > resistance + breakout_threshold:
            confidence = min(0.75 + ((current_price - resistance) / (resistance - support)), 0.9)
            
            patterns.append({
                "pattern": ChartPattern.BREAKOUT,
                "confidence": confidence,
                "indices": [int(len(prices)-window), int(len(prices)-1)],
                "target_price": resistance + ((resistance - support) * 0.5),
                "entry_zone": [resistance, resistance + breakout_threshold]
            })
        
        # Breakdown = prix < support
        if current_price < support - breakout_threshold:
            confidence = min(0.75 + ((support - current_price) / (resistance - support)), 0.9)
            
            patterns.append({
                "pattern": ChartPattern.BREAKOWN,
                "confidence": confidence,
                "indices": [int(len(prices)-window), int(len(prices)-1)],
                "target_price": support - ((resistance - support) * 0.5),
                "entry_zone": [support - breakout_threshold, support]
            })
        
        return patterns
    
    @staticmethod
    def _find_local_extrema(
        prices: np.ndarray,
        extrema_type: str = "max",
        window: int = 5
    ) -> List[int]:
        """Trouve les maxima/minima locaux"""
        indices = []
        
        for i in range(window, len(prices) - window):
            segment = prices[i-window:i+window+1]
            
            if extrema_type == "max":
                if prices[i] == np.max(segment):
                    indices.append(i)
            else:  # min
                if prices[i] == np.min(segment):
                    indices.append(i)
        
        return indices
    
    @staticmethod
    def _calculate_pattern_confidence(prices: np.ndarray, indices: List[int]) -> float:
        """Calcule la confiance d'un pattern"""
        if len(indices) < 2:
            return 0.5
        
        # Basé sur la régularité de la forme
        segment = prices[indices[0]:indices[-1]+1]
        
        # Calculer l'écart type normalisé
        mean_price = np.mean(segment)
        normalized_std = np.std(segment) / mean_price if mean_price > 0 else 0
        
        # Moins de variation = plus confiant
        confidence = 1 - min(normalized_std, 0.5) / 0.5
        
        return confidence
    
    @staticmethod
    def _calculate_entry_zone(segment: np.ndarray) -> List[float]:
        """Calcule la zone d'entrée optimale"""
        support = np.min(segment)
        resistance = np.max(segment)
        mid = (support + resistance) / 2
        
        return [support, mid, resistance]
