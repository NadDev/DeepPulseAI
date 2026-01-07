import { useState } from 'react';
import { TrendingUp, TrendingDown, Target, AlertCircle } from 'lucide-react';
import './AIAnalysis.css';

function AIAnalysis({ recommendations = [], onRefresh }) {
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  const getActionColor = (action) => {
    switch (action?.toUpperCase()) {
      case 'BUY':
        return 'buy';
      case 'SELL':
        return 'sell';
      case 'HOLD':
        return 'hold';
      default:
        return 'neutral';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 75) return 'high';
    if (confidence >= 60) return 'medium';
    return 'low';
  };

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="ai-analysis">
        <div className="no-data">
          <AlertCircle size={48} />
          <p>No recommendations yet. Run analysis to get started.</p>
          <button className="btn-refresh" onClick={onRefresh}>
            Run Analysis Now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-analysis">
      <div className="analysis-header">
        <h2>Market Recommendations</h2>
        <button className="btn-refresh" onClick={onRefresh}>
          Refresh Analysis
        </button>
      </div>

      <div className="recommendations-container">
        {recommendations.map((rec, idx) => (
          <div
            key={idx}
            className={`recommendation-card action-${getActionColor(rec.action)}`}
            onClick={() => setSelectedSymbol(selectedSymbol === rec.symbol ? null : rec.symbol)}
          >
            <div className="rec-header">
              <div className="rec-symbol">
                <h3>{rec.symbol}</h3>
                <span className={`action-badge ${getActionColor(rec.action)}`}>
                  {rec.action?.toUpperCase()}
                </span>
              </div>
              <div className="rec-confidence">
                <div className={`confidence-bar ${getConfidenceColor(rec.confidence)}`}>
                  <div
                    className="confidence-fill"
                    style={{ width: `${rec.confidence}%` }}
                  ></div>
                </div>
                <p className="confidence-text">{rec.confidence}% Confidence</p>
              </div>
            </div>

            {selectedSymbol === rec.symbol && (
              <div className="rec-details">
                <div className="detail-row">
                  <span className="detail-label">Entry Price:</span>
                  <span className="detail-value">${rec.entry_price?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Target Price:</span>
                  <span className="detail-value">${rec.target_price?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Stop Loss:</span>
                  <span className="detail-value">${rec.stop_loss?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Timeframe:</span>
                  <span className="detail-value">{rec.timeframe || '1h'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Risk Level:</span>
                  <span className="detail-value">{rec.risk_level || 'MEDIUM'}</span>
                </div>
                {rec.reasoning && (
                  <div className="detail-reasoning">
                    <p className="reasoning-label">Analysis:</p>
                    <p className="reasoning-text">{rec.reasoning}</p>
                  </div>
                )}
              </div>
            )}

            <div className="rec-footer">
              {rec.action?.toUpperCase() === 'BUY' && <TrendingUp size={16} className="icon-buy" />}
              {rec.action?.toUpperCase() === 'SELL' && <TrendingDown size={16} className="icon-sell" />}
              {rec.action?.toUpperCase() === 'HOLD' && <Target size={16} className="icon-hold" />}
              <span className="rec-timestamp">
                {rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : 'Just now'}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="analysis-footer">
        <p className="footer-note">
          💡 Click on a recommendation to see full analysis details
        </p>
      </div>
    </div>
  );
}

export default AIAnalysis;
