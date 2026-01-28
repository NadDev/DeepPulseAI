import React from 'react';
import '../styles/CryptoScoreCard.css';

/**
 * Reusable crypto score card component
 * Displays symbol, score, and 4 component breakdown
 */
const CryptoScoreCard = ({
  symbol,
  score,
  action,
  components = {},
  reasoning,
  price,
  priceChange7d,
  onClick,
  className = ''
}) => {
  const getActionColor = (action) => {
    switch(action?.toUpperCase()) {
      case 'ADD': return 'add';
      case 'REMOVE': return 'remove';
      default: return 'hold';
    }
  };

  const actionColor = getActionColor(action);

  return (
    <div className={`crypto-score-card ${actionColor} ${className}`} onClick={onClick}>
      <div className="card-top">
        <div className="symbol-badge">
          <span className="symbol">{symbol}</span>
          {action && (
            <span className={`action-label ${actionColor}`}>
              {action === 'ADD' ? '⬆️' : action === 'REMOVE' ? '⬇️' : '→'} {action}
            </span>
          )}
        </div>
        
        <div className="score-display">
          <div className="score-circle">
            <span className="score-number">{score.toFixed(1)}</span>
            <span className="score-max">/100</span>
          </div>
        </div>
      </div>

      {(price || priceChange7d !== undefined) && (
        <div className="price-info">
          {price && <span className="price">${price.toFixed(2)}</span>}
          {priceChange7d !== undefined && (
            <span className={`change ${priceChange7d >= 0 ? 'positive' : 'negative'}`}>
              {priceChange7d >= 0 ? '📈' : '📉'} {priceChange7d > 0 ? '+' : ''}{priceChange7d.toFixed(1)}%
            </span>
          )}
        </div>
      )}

      <div className="components-breakdown">
        <div className="component-item">
          <span className="label">Momentum</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${components.momentum || 0}%` }} />
          </div>
          <span className="value">{(components.momentum || 0).toFixed(0)}</span>
        </div>

        <div className="component-item">
          <span className="label">Volume</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${components.volume || 0}%` }} />
          </div>
          <span className="value">{(components.volume || 0).toFixed(0)}</span>
        </div>

        <div className="component-item">
          <span className="label">Volatility</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${components.volatility || 0}%` }} />
          </div>
          <span className="value">{(components.volatility || 0).toFixed(0)}</span>
        </div>

        <div className="component-item">
          <span className="label">RSI</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${components.rsi || 0}%` }} />
          </div>
          <span className="value">{(components.rsi || 0).toFixed(0)}</span>
        </div>
      </div>

      {reasoning && (
        <div className="reasoning-box">
          <strong>Analysis</strong>
          <p>{reasoning}</p>
        </div>
      )}

      <div className="score-bar-bottom">
        <div className="bar">
          <div className="fill" style={{ width: `${score}%` }} />
        </div>
      </div>
    </div>
  );
};

export default CryptoScoreCard;
