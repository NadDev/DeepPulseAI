import { Activity, Brain, Zap, TrendingUp } from 'lucide-react';
import './AIStatus.css';

function AIStatus({ status, mode, isRunning }) {
  if (!status) return null;

  const formatTime = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="ai-status-grid">
      {/* AI Status */}
      <div className="status-card">
        <div className="status-header">
          <Brain size={24} />
          <span className={`status-indicator ${isRunning ? 'active' : 'inactive'}`}>
            {isRunning ? '🟢' : '🔴'}
          </span>
        </div>
        <div className="status-content">
          <p className="status-label">AI Agent</p>
          <p className="status-value">{isRunning ? 'Running' : 'Paused'}</p>
          <p className="status-meta">Mode: {mode}</p>
        </div>
      </div>

      {/* Active Bots */}
      <div className="status-card">
        <div className="status-header">
          <Zap size={24} />
        </div>
        <div className="status-content">
          <p className="status-label">Active Bots</p>
          <p className="status-value">
            {status.controller?.ai_bots_count || 0}/{status.controller?.config?.max_active_bots || 10}
          </p>
          <p className="status-meta">
            {status.controller?.active_ai_bots || 0} currently trading
          </p>
        </div>
      </div>

      {/* Confidence Level */}
      <div className="status-card">
        <div className="status-header">
          <Activity size={24} />
        </div>
        <div className="status-content">
          <p className="status-label">Min Confidence</p>
          <p className="status-value">
            {status.controller?.config?.min_confidence || 60}%
          </p>
          <p className="status-meta">Decision threshold</p>
        </div>
      </div>

      {/* Last Analysis */}
      <div className="status-card">
        <div className="status-header">
          <TrendingUp size={24} />
        </div>
        <div className="status-content">
          <p className="status-label">Last Analysis</p>
          <p className="status-value">{formatTime(status.last_analysis)}</p>
          <p className="status-meta">
            {status.recommendations_count || 0} recommendations
          </p>
        </div>
      </div>

      {/* Daily Trades */}
      <div className="status-card">
        <div className="status-header">
          <Brain size={24} />
        </div>
        <div className="status-content">
          <p className="status-label">Daily Trades</p>
          <p className="status-value">
            {status.controller?.daily_trades || 0}/{status.controller?.config?.max_daily_trades || 50}
          </p>
          <p className="status-meta">Today's decisions</p>
        </div>
      </div>

      {/* Risk Level */}
      <div className="status-card">
        <div className="status-header">
          <Activity size={24} />
        </div>
        <div className="status-content">
          <p className="status-label">Risk Per Trade</p>
          <p className="status-value">
            {status.controller?.config?.default_risk_percent || 1.0}%
          </p>
          <p className="status-meta">Portfolio risk limit</p>
        </div>
      </div>
    </div>
  );
}

export default AIStatus;
