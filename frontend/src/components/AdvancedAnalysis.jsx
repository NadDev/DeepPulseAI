import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, Layers, Target, BarChart3, Info } from 'lucide-react';
import { cryptoAPI as api } from '../services/api';
import './AdvancedAnalysis.css';

// Descriptions détaillées des vagues Elliott
const waveDescriptions = {
  '1': "Début d'une nouvelle tendance. Souvent difficile à identifier en temps réel. Volume généralement faible.",
  '2': "Correction de la vague 1 (typiquement 50-61.8% de retracement). Ne doit jamais descendre sous le début de la vague 1.",
  '3': "La plus longue et la plus puissante. Fort volume, forte dynamique. Jamais la plus courte des vagues impulsives.",
  '4': "Correction modérée (souvent 38.2%). Ne doit pas chevaucher le sommet de la vague 1. Phase de consolidation.",
  '5': "Dernière poussée de la tendance. Volume souvent plus faible que la vague 3. Signale une fin de tendance imminente.",
  'A': "Début de la correction. Souvent confondue avec un simple pullback. Marque le retournement initial.",
  'B': "Rebond correctif, souvent un 'bull trap'. Peut atteindre ou dépasser le sommet de la vague 5.",
  'C': "Dernière vague corrective, souvent aussi longue que la vague A. Complète la correction avant un nouveau cycle."
};

// Mapping période -> Wave Degree
const getWaveDegree = (period) => {
  const degreeMap = {
    '1h': { name: 'Micro', duration: 'Minutes à heures' },
    '24h': { name: 'Intraday', duration: 'Heures à jour' },
    '7d': { name: 'Court terme', duration: 'Jours à semaine' },
    '30d': { name: 'Moyen terme', duration: 'Semaines à mois' },
    '90d': { name: 'Long terme', duration: 'Mois à trimestre' },
    '1y': { name: 'Tendance majeure', duration: 'Trimestres à année' }
  };
  return degreeMap[period] || { name: 'Moyen terme', duration: 'Semaines à mois' };
};

const AdvancedAnalysis = ({ symbol = 'BTC', localWaves = null, period = '7d' }) => {
  const [elliottWave, setElliottWave] = useState(null);
  const [fibonacci, setFibonacci] = useState(null);
  const [ichimoku, setIchimoku] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('elliott');

  useEffect(() => {
    const fetchAdvancedData = async () => {
      setLoading(true);
      try {
        const [elliottData, fiboData, ichimokuData] = await Promise.all([
          api.getElliottWave(symbol).catch(() => null),
          api.getFibonacci(symbol).catch(() => null),
          api.getIchimoku(symbol).catch(() => null)
        ]);
        
        setElliottWave(elliottData);
        setFibonacci(fiboData);
        setIchimoku(ichimokuData);
      } catch (error) {
        console.error('Error fetching advanced analysis:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAdvancedData();
    const interval = setInterval(fetchAdvancedData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [symbol]);

  const renderElliottWave = () => {
    // Use local waves data if API data is unavailable
    const hasApiData = elliottWave && !elliottWave.error && elliottWave.current_wave;
    const hasLocalData = localWaves && localWaves.currentWave;
    
    // Determine current wave from API or local analysis
    const current_wave = hasApiData 
      ? elliottWave.current_wave 
      : (hasLocalData ? localWaves.currentWave.label : null);
    
    const wave_sequence = hasApiData ? elliottWave.wave_sequence : ['1', '2', '3', '4', '5', 'A', 'B', 'C'];
    const trend = hasApiData ? elliottWave.trend : (hasLocalData && localWaves.currentWave.direction === 'up' ? 'bullish' : 'bearish');
    
    // Confidence: use local calculated confidence or API confidence
    const localConfidence = hasLocalData && localWaves.confidence ? localWaves.confidence : null;
    const confidence = hasApiData ? elliottWave.confidence : (localConfidence ? localConfidence.score : 0.5);
    const confidenceFactors = localConfidence ? localConfidence.factors : null;
    
    const waveDegreeInfo = getWaveDegree(period);
    const wave_degree = hasApiData ? elliottWave.wave_degree : waveDegreeInfo.name;
    const dataSource = hasApiData ? 'API' : (hasLocalData ? 'Local' : null);

    if (!current_wave) {
      return <div className="no-data">Elliott Wave data unavailable - sélectionnez une période plus longue</div>;
    }

    const isImpulse = ['1', '2', '3', '4', '5'].includes(current_wave);
    
    // Confidence color based on score
    const getConfidenceColor = (score) => {
      if (score >= 0.7) return '#00d4aa'; // Green - high confidence
      if (score >= 0.5) return '#f5a623'; // Orange - medium
      return '#ff6b6b'; // Red - low
    };

    return (
      <div className="elliott-wave-panel">
        <div className="wave-header">
          <div className="current-wave">
            <span className="wave-label">Current Wave {dataSource && <small>({dataSource})</small>}</span>
            <span className={`wave-number ${isImpulse ? 'impulse' : 'corrective'}`}>
              {current_wave}
            </span>
          </div>
          <div className="wave-trend">
            {trend === 'bullish' ? (
              <TrendingUp className="trend-icon bullish" />
            ) : (
              <TrendingDown className="trend-icon bearish" />
            )}
            <span className={`trend-text ${trend}`}>{trend}</span>
          </div>
        </div>

        <div className="wave-details">
          <div className="detail-item">
            <span className="detail-label">Wave Degree</span>
            <span className="detail-value" title={waveDegreeInfo.duration}>{wave_degree}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Fiabilité</span>
            <div className="confidence-bar" title={confidenceFactors ? 
              `Structure: ${Math.round(confidenceFactors.structure * 100)}% | Historique: ${Math.round(confidenceFactors.historical * 100)}% | Pattern: ${Math.round(confidenceFactors.pattern * 100)}%` : ''}>
              <div 
                className="confidence-fill" 
                style={{ 
                  width: `${confidence * 100}%`,
                  background: getConfidenceColor(confidence)
                }}
              />
            </div>
            <span className="confidence-value" style={{ color: getConfidenceColor(confidence) }}>
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        <div className="wave-sequence">
          <span className="sequence-label">Wave Sequence</span>
          <div className="wave-pills">
            {(wave_sequence || ['1', '2', '3', '4', '5', 'A', 'B', 'C']).map((wave, idx) => (
              <span 
                key={idx} 
                className={`wave-pill ${wave === current_wave ? 'active' : ''} ${['A', 'B', 'C'].includes(wave) ? 'corrective' : 'impulse'}`}
              >
                {wave}
              </span>
            ))}
          </div>
        </div>

        <div className="wave-interpretation">
          <Activity className="interp-icon" />
          <p>
            {isImpulse 
              ? `Wave ${current_wave} is part of the impulse phase. ${current_wave === '3' ? 'Wave 3 is typically the strongest wave.' : current_wave === '5' ? 'Wave 5 may signal the end of the trend.' : ''}`
              : `Wave ${current_wave} is a corrective wave. ${current_wave === 'C' ? 'Wave C often completes the correction.' : 'Expect counter-trend movement.'}`
            }
          </p>
        </div>

        {/* Detected waves from local analysis */}
        {localWaves && localWaves.waves && localWaves.waves.length > 0 && (
          <div className="local-waves-section">
            <h4><Info size={14} /> Vagues détectées (analyse locale)</h4>
            <div className="detected-waves-list">
              {localWaves.waves.slice(-5).map((wave, idx) => (
                <div key={idx} className={`detected-wave-item ${wave.type}`}>
                  <span className="wave-badge">Vague {wave.wave}</span>
                  <span className="wave-desc"> — {waveDescriptions[wave.wave] || 'Vague en cours d\'analyse'}</span>
                </div>
              ))}
            </div>
            {localWaves.currentWave && (
              <div className="current-wave-info">
                <strong>Vague en cours :</strong> {localWaves.currentWave.label}
                <p className="current-wave-desc">{waveDescriptions[localWaves.currentWave.label]}</p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderFibonacci = () => {
    if (!fibonacci || fibonacci.error) {
      return <div className="no-data">Fibonacci data unavailable</div>;
    }

    const { retracement_levels, extension_levels, current_price, trend, swing_high, swing_low } = fibonacci;

    return (
      <div className="fibonacci-panel">
        <div className="fibo-header">
          <div className="price-info">
            <span className="price-label">Current Price</span>
            <span className="price-value">${current_price?.toLocaleString() || 'N/A'}</span>
          </div>
          <div className="swing-info">
            <div className="swing-item">
              <TrendingUp className="swing-icon high" />
              <span>High: ${swing_high?.toLocaleString() || 'N/A'}</span>
            </div>
            <div className="swing-item">
              <TrendingDown className="swing-icon low" />
              <span>Low: ${swing_low?.toLocaleString() || 'N/A'}</span>
            </div>
          </div>
        </div>

        <div className="fibo-section">
          <h4><Target className="section-icon" /> Retracement Levels</h4>
          <div className="fibo-levels">
            {retracement_levels && Object.entries(retracement_levels).map(([level, price]) => {
              const isNearLevel = current_price && Math.abs((current_price - price) / price) < 0.02;
              return (
                <div key={level} className={`fibo-level ${isNearLevel ? 'near' : ''}`}>
                  <span className="level-percent">{level}</span>
                  <div className="level-line" />
                  <span className="level-price">${price?.toLocaleString() || 'N/A'}</span>
                  {isNearLevel && <span className="near-badge">Near</span>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="fibo-section">
          <h4><Layers className="section-icon" /> Extension Levels</h4>
          <div className="fibo-levels extensions">
            {extension_levels && Object.entries(extension_levels).map(([level, price]) => (
              <div key={level} className="fibo-level extension">
                <span className="level-percent">{level}</span>
                <div className="level-line" />
                <span className="level-price">${price?.toLocaleString() || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderIchimoku = () => {
    if (!ichimoku || ichimoku.error) {
      return <div className="no-data">Ichimoku data unavailable</div>;
    }

    const { tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span, signal, cloud_color } = ichimoku;

    const getSignalClass = (sig) => {
      if (sig?.includes('bullish') || sig?.includes('above')) return 'bullish';
      if (sig?.includes('bearish') || sig?.includes('below')) return 'bearish';
      return 'neutral';
    };

    return (
      <div className="ichimoku-panel">
        <div className="ichimoku-signal">
          <BarChart3 className={`signal-icon ${getSignalClass(signal)}`} />
          <div className="signal-info">
            <span className="signal-label">Overall Signal</span>
            <span className={`signal-value ${getSignalClass(signal)}`}>
              {signal || 'Neutral'}
            </span>
          </div>
          <div className={`cloud-indicator ${cloud_color || 'neutral'}`}>
            <span>Cloud: {cloud_color || 'Neutral'}</span>
          </div>
        </div>

        <div className="ichimoku-lines">
          <div className="line-item tenkan">
            <div className="line-header">
              <span className="line-name">Tenkan-sen</span>
              <span className="line-subtitle">(Conversion Line - 9 periods)</span>
            </div>
            <span className="line-value">${tenkan_sen?.toLocaleString() || 'N/A'}</span>
          </div>

          <div className="line-item kijun">
            <div className="line-header">
              <span className="line-name">Kijun-sen</span>
              <span className="line-subtitle">(Base Line - 26 periods)</span>
            </div>
            <span className="line-value">${kijun_sen?.toLocaleString() || 'N/A'}</span>
          </div>

          <div className="line-item senkou-a">
            <div className="line-header">
              <span className="line-name">Senkou Span A</span>
              <span className="line-subtitle">(Leading Span A)</span>
            </div>
            <span className="line-value">${senkou_span_a?.toLocaleString() || 'N/A'}</span>
          </div>

          <div className="line-item senkou-b">
            <div className="line-header">
              <span className="line-name">Senkou Span B</span>
              <span className="line-subtitle">(Leading Span B - 52 periods)</span>
            </div>
            <span className="line-value">${senkou_span_b?.toLocaleString() || 'N/A'}</span>
          </div>

          <div className="line-item chikou">
            <div className="line-header">
              <span className="line-name">Chikou Span</span>
              <span className="line-subtitle">(Lagging Span)</span>
            </div>
            <span className="line-value">${chikou_span?.toLocaleString() || 'N/A'}</span>
          </div>
        </div>

        <div className="ichimoku-interpretation">
          <h4>Interpretation</h4>
          <ul>
            {tenkan_sen > kijun_sen ? (
              <li className="bullish">Tenkan above Kijun: Short-term bullish</li>
            ) : (
              <li className="bearish">Tenkan below Kijun: Short-term bearish</li>
            )}
            {senkou_span_a > senkou_span_b ? (
              <li className="bullish">Green cloud: Bullish trend</li>
            ) : (
              <li className="bearish">Red cloud: Bearish trend</li>
            )}
          </ul>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="advanced-analysis loading">
        <div className="loading-spinner" />
        <p>Loading advanced analysis...</p>
      </div>
    );
  }

  return (
    <div className="advanced-analysis">
      <div className="analysis-header">
        <h3>Advanced Technical Analysis</h3>
        <span className="symbol-badge">{symbol}</span>
      </div>

      <div className="analysis-tabs">
        <button 
          className={`tab ${activeTab === 'elliott' ? 'active' : ''}`}
          onClick={() => setActiveTab('elliott')}
        >
          <Activity size={16} />
          Elliott Wave
        </button>
        <button 
          className={`tab ${activeTab === 'fibonacci' ? 'active' : ''}`}
          onClick={() => setActiveTab('fibonacci')}
        >
          <Target size={16} />
          Fibonacci
        </button>
        <button 
          className={`tab ${activeTab === 'ichimoku' ? 'active' : ''}`}
          onClick={() => setActiveTab('ichimoku')}
        >
          <Layers size={16} />
          Ichimoku
        </button>
      </div>

      <div className="analysis-content">
        {activeTab === 'elliott' && renderElliottWave()}
        {activeTab === 'fibonacci' && renderFibonacci()}
        {activeTab === 'ichimoku' && renderIchimoku()}
      </div>
    </div>
  );
};

export default AdvancedAnalysis;
