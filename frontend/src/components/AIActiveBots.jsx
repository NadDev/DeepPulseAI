import { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, X } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import './AIActiveBots.css';

function AIActiveBots() {
  const [bots, setBots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBot, setSelectedBot] = useState(null);

  useEffect(() => {
    loadBots();
    const interval = setInterval(loadBots, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadBots = async () => {
    try {
      const botsData = await aiAPI.getActiveBots();
      setBots(botsData.bots || []);
    } catch (err) {
      setError(err.message || 'Failed to load active bots');
      console.error('Error loading bots:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case 'RUNNING':
        return 'running';
      case 'PAUSED':
        return 'paused';
      case 'CLOSED':
        return 'closed';
      default:
        return 'unknown';
    }
  };

  if (loading) {
    return (
      <div className="ai-active-bots">
        <div className="loading-state">
          <p>Loading active bots...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-active-bots">
      <div className="bots-header">
        <h2>AI-Managed Bots ({bots.length})</h2>
        <p className="header-subtitle">Bots created and controlled by the AI Agent</p>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <p>{error}</p>
        </div>
      )}

      {bots.length === 0 ? (
        <div className="no-data">
          <AlertCircle size={40} />
          <p>No active AI bots yet</p>
          <p className="no-data-meta">The AI Agent will create bots when suitable trading opportunities are identified</p>
        </div>
      ) : (
        <div className="bots-grid">
          {bots.map((bot, idx) => (
            <div
              key={bot.id || idx}
              className={`bot-card status-${getStatusColor(bot.status)}`}
              onClick={() => setSelectedBot(selectedBot?.id === bot.id ? null : bot)}
            >
              <div className="bot-header">
                <div className="bot-info">
                  <h3>{bot.name || `Bot ${idx + 1}`}</h3>
                  <span className={`status-badge status-${getStatusColor(bot.status)}`}>
                    {bot.status || 'UNKNOWN'}
                  </span>
                </div>
                {selectedBot?.id === bot.id && (
                  <button
                    className="close-detail-btn"
                    onClick={e => {
                      e.stopPropagation();
                      setSelectedBot(null);
                    }}
                  >
                    <X size={18} />
                  </button>
                )}
              </div>

              <div className="bot-summary">
                <div className="summary-item">
                  <span className="label">Created</span>
                  <span className="value">{bot.created_at ? new Date(bot.created_at).toLocaleString() : 'N/A'}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Trading</span>
                  <span className="value">{bot.symbols?.join(', ') || 'N/A'}</span>
                </div>
                <div className="summary-item">
                  <span className="label">P&L</span>
                  <span className={`value ${(bot.pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                    {formatCurrency(bot.pnl || 0)}
                  </span>
                </div>
              </div>

              {selectedBot?.id === bot.id && (
                <div className="bot-details">
                  <div className="detail-section">
                    <h4>Strategy</h4>
                    <p>{bot.strategy || 'AI-Optimized'}</p>
                  </div>

                  {bot.positions && bot.positions.length > 0 && (
                    <div className="detail-section">
                      <h4>Current Positions</h4>
                      {bot.positions.map((pos, pidx) => (
                        <div key={pidx} className="position-item">
                          <div className="position-header">
                            <span className="symbol">{pos.symbol}</span>
                            <span className={`direction ${pos.side?.toLowerCase()}`}>
                              {pos.side?.toUpperCase()}
                            </span>
                          </div>
                          <div className="position-details">
                            <div className="detail-row">
                              <span>Size:</span>
                              <strong>{pos.amount?.toFixed(4)} {pos.symbol}</strong>
                            </div>
                            <div className="detail-row">
                              <span>Entry Price:</span>
                              <strong>${pos.entry_price?.toFixed(2)}</strong>
                            </div>
                            <div className="detail-row">
                              <span>Current Price:</span>
                              <strong>${pos.current_price?.toFixed(2)}</strong>
                            </div>
                            <div className="detail-row">
                              <span>P&L:</span>
                              <strong className={(pos.pnl || 0) >= 0 ? 'positive' : 'negative'}>
                                {formatCurrency(pos.pnl || 0)}
                              </strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="detail-section">
                    <h4>Configuration</h4>
                    <div className="config-grid">
                      <div className="config-item">
                        <span>Risk Level</span>
                        <strong>{bot.config?.risk_level || 'MEDIUM'}</strong>
                      </div>
                      <div className="config-item">
                        <span>Stop Loss</span>
                        <strong>{bot.config?.stop_loss_percent || 1.5}%</strong>
                      </div>
                      <div className="config-item">
                        <span>Take Profit</span>
                        <strong>{bot.config?.take_profit_percent || 3}%</strong>
                      </div>
                      <div className="config-item">
                        <span>Mode</span>
                        <strong>{bot.config?.mode || 'PAPER'}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="bot-actions">
                    <button className="btn-adjust">⚙️ Adjust</button>
                    <button className="btn-close">❌ Close Bot</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AIActiveBots;
