import { useState, useEffect } from 'react';
import { cryptoAPI } from '../services/api';
import { Brain, TrendingUp, Activity, AlertCircle, RefreshCw } from 'lucide-react';
import './MLPredictions.css';

function MLPredictions({ symbol = 'BTC' }) {
  const [data, setData] = useState(null);
  const [signal, setSignal] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [trainingState, setTrainingState] = useState({ status: 'idle', progress: 0, message: '' });

  useEffect(() => {
    const fetchData = async () => {
      // Don't set loading to true on refresh to avoid flickering
      if (!data) setLoading(true);
      try {
        const [predData, signalData, patternsData] = await Promise.all([
          cryptoAPI.getPredictions(symbol),
          cryptoAPI.getSignals(symbol),
          cryptoAPI.getPatterns(symbol)
        ]);

        setData(predData);
        setSignal(signalData);
        setPatterns(patternsData.patterns || []);
      } catch (error) {
        console.error("Error fetching ML data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [symbol]);

  // Poll training status
  useEffect(() => {
    let interval;
    if (trainingState.status === 'training' || trainingState.status === 'started') {
      interval = setInterval(async () => {
        try {
          const status = await cryptoAPI.getTrainingStatus();
          setTrainingState(status);
          if (status.status === 'completed' || status.status === 'error') {
            clearInterval(interval);
            if (status.status === 'completed') {
                // Wait a bit then clear status
                setTimeout(() => setTrainingState({ status: 'idle', progress: 0, message: '' }), 5000);
            }
          }
        } catch (e) {
          console.error(e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [trainingState.status]);

  const handleRetrain = async () => {
    try {
      setTrainingState({ status: 'training', progress: 0, message: 'Starting...' });
      // Default to BTCUSDT for now as per backend default, or construct from symbol
      const pair = symbol.includes('USDT') ? symbol : `${symbol}USDT`;
      await cryptoAPI.trainModel(pair, 365);
    } catch (e) {
      console.error(e);
      setTrainingState({ status: 'error', message: 'Failed to start training' });
    }
  };

  if (loading && !data) return (
    <div className="ml-loading-container">
      <div className="ml-spinner"></div>
      <span>Analyzing {symbol}...</span>
    </div>
  );

  const formatPrice = (price) => {
    if (!price || isNaN(price)) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price);
  };

  // Helper to safely get price value whether it's a number or object
  const getPredValue = (pred) => {
    if (!pred) return 0;
    if (typeof pred === 'number') return pred;
    if (typeof pred === 'object' && pred.price) return pred.price;
    return 0;
  };

  // Helper to get confidence
  const getConfidence = () => {
    if (!data) return 0;
    if (data.confidence) return data.confidence;
    // Calculate average confidence from predictions if available
    if (data.predictions && data.predictions['1h'] && data.predictions['1h'].confidence) {
      return (data.predictions['1h'].confidence + data.predictions['24h'].confidence) / 2;
    }
    return 0;
  };

  const pred1h = data ? getPredValue(data.predictions['1h']) : 0;
  const pred24h = data ? getPredValue(data.predictions['24h']) : 0;
  const currentPrice = data ? data.current_price : 0;

  return (
    <div className="ml-integrated-card">
      <div className="ml-header-int">
        <div className="ml-title-group">
			<h3><Brain size={18} className="text-purple" /> ML Engine</h3>
            <button 
                onClick={handleRetrain} 
                disabled={trainingState.status === 'training'}
                className="ml-retrain-btn"
                title="Retrain Model on 1y Data"
            >
                <RefreshCw size={14} className={trainingState.status === 'training' ? 'spin' : ''} />
            </button>
        </div>
        {data && (
          <span className="confidence-badge">
            {(getConfidence() * 100).toFixed(0)}% Conf.
          </span>
        )}
      </div>

      {trainingState.status === 'training' && (
        <div className="training-progress-container">
            <div className="training-progress-bar">
                <div className="training-progress-fill" style={{width: `${trainingState.progress}%`}}></div>
            </div>
            <span className="training-status-text">{trainingState.message} ({trainingState.progress}%)</span>
        </div>
      )}

      {data && (
        <div className="ml-content-grid">
          {/* Predictions */}
          <div className="ml-sub-section">
            <h4>Price Forecast</h4>
            <div className="forecast-row">
              <div className="forecast-item">
                <span className="f-label">1h</span>
                <span className={`f-value ${pred1h > currentPrice ? 'text-green' : 'text-red'}`}>
                  {formatPrice(pred1h)}
                </span>
              </div>
              <div className="forecast-item">
                <span className="f-label">24h</span>
                <span className={`f-value ${pred24h > currentPrice ? 'text-green' : 'text-red'}`}>
                  {formatPrice(pred24h)}
                </span>
              </div>
            </div>
          </div>

          {/* Signal */}
          <div className="ml-sub-section">
            <h4>Trading Signal</h4>
            <div className="signal-display">
              <span className={`signal-badge ${signal?.signal === 'BUY' ? 'bg-green' : signal?.signal === 'SELL' ? 'bg-red' : 'bg-gray'}`}>
                {signal?.signal || 'NEUTRAL'}
              </span>
              <span className="signal-reason">{signal?.reason || 'No clear signal'}</span>
            </div>
          </div>

          {/* Patterns */}
          <div className="ml-sub-section">
            <h4>Detected Patterns</h4>
            <div className="patterns-tags">
              {patterns.length > 0 ? (
                patterns.slice(0, 3).map((p, i) => (
                  <span key={i} className="pattern-tag">
                    {p.pattern} ({(p.confidence * 100).toFixed(0)}%)
                  </span>
                ))
              ) : (
                <span className="no-patterns">No patterns detected</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MLPredictions;
