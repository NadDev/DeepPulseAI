import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, AlertCircle } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import '../styles/AISettings.css';

export default function AISettings() {
  const [config, setConfig] = useState({
    max_daily_trades: 5,
    risk_percentage: 2,
    stop_loss_percentage: 5,
    confidence_threshold: 65,
    cooldown_minutes: 30,
    watchlist_symbols: ['BTC/USDT', 'ETH/USDT'],
    enabled: true
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [newSymbol, setNewSymbol] = useState('');

  // Fetch current config
  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const data = await aiAPI.getConfig();
      if (data && data.config) {
        setConfig(data.config);
      }
      setError('');
    } catch (err) {
      console.error('Error fetching config:', err);
      setError('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAddSymbol = () => {
    if (newSymbol.trim() && !config.watchlist_symbols.includes(newSymbol.toUpperCase())) {
      setConfig(prev => ({
        ...prev,
        watchlist_symbols: [...prev.watchlist_symbols, newSymbol.toUpperCase()]
      }));
      setNewSymbol('');
    }
  };

  const handleRemoveSymbol = (symbol) => {
    setConfig(prev => ({
      ...prev,
      watchlist_symbols: prev.watchlist_symbols.filter(s => s !== symbol)
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setMessage('');

      await aiAPI.updateConfig(config);
      setMessage('✅ Configuration saved successfully');
      
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error('Error saving config:', err);
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (window.confirm('Reset all settings to defaults?')) {
      setConfig({
        max_daily_trades: 5,
        risk_percentage: 2,
        stop_loss_percentage: 5,
        confidence_threshold: 65,
        cooldown_minutes: 30,
        watchlist_symbols: ['BTC/USDT', 'ETH/USDT'],
        enabled: true
      });
      setMessage('Settings reset to defaults');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  if (loading) {
    return (
      <div className="ai-settings-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading AI configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-settings-container">
      <div className="ai-settings-header">
        <h2>⚙️ AI Agent Configuration</h2>
        <p>Customize AI trading parameters and watchlist</p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {message && (
        <div className="alert alert-success">
          <span>{message}</span>
        </div>
      )}

      <div className="ai-settings-content">
        {/* Enable/Disable Toggle */}
        <div className="settings-section">
          <div className="section-title">Status</div>
          <div className="setting-item">
            <label>AI Agent Status</label>
            <div className="toggle-switch">
              <input
                type="checkbox"
                id="ai-enabled"
                checked={config.enabled}
                onChange={(e) => handleInputChange('enabled', e.target.checked)}
              />
              <label htmlFor="ai-enabled" className="toggle-label">
                <span className={config.enabled ? 'active' : ''}>
                  {config.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Trading Parameters */}
        <div className="settings-section">
          <div className="section-title">Trading Parameters</div>

          <div className="settings-grid">
            {/* Max Daily Trades */}
            <div className="setting-item">
              <label htmlFor="max-daily-trades">
                Max Daily Trades
                <span className="help-text">Maximum trades per day</span>
              </label>
              <div className="input-with-slider">
                <input
                  id="max-daily-trades"
                  type="number"
                  min="1"
                  max="20"
                  value={config.max_daily_trades}
                  onChange={(e) => handleInputChange('max_daily_trades', parseInt(e.target.value))}
                />
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={config.max_daily_trades}
                  onChange={(e) => handleInputChange('max_daily_trades', parseInt(e.target.value))}
                  className="slider"
                />
              </div>
              <span className="current-value">{config.max_daily_trades} trades</span>
            </div>

            {/* Risk Percentage */}
            <div className="setting-item">
              <label htmlFor="risk-percentage">
                Risk Per Trade
                <span className="help-text">% of portfolio per trade</span>
              </label>
              <div className="input-with-slider">
                <input
                  id="risk-percentage"
                  type="number"
                  min="0.5"
                  max="10"
                  step="0.5"
                  value={config.risk_percentage}
                  onChange={(e) => handleInputChange('risk_percentage', parseFloat(e.target.value))}
                />
                <input
                  type="range"
                  min="0.5"
                  max="10"
                  step="0.5"
                  value={config.risk_percentage}
                  onChange={(e) => handleInputChange('risk_percentage', parseFloat(e.target.value))}
                  className="slider"
                />
              </div>
              <span className="current-value">{config.risk_percentage.toFixed(1)}%</span>
            </div>

            {/* Stop Loss Percentage */}
            <div className="setting-item">
              <label htmlFor="stop-loss-percentage">
                Stop Loss
                <span className="help-text">Stop loss threshold</span>
              </label>
              <div className="input-with-slider">
                <input
                  id="stop-loss-percentage"
                  type="number"
                  min="1"
                  max="20"
                  step="0.5"
                  value={config.stop_loss_percentage}
                  onChange={(e) => handleInputChange('stop_loss_percentage', parseFloat(e.target.value))}
                />
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="0.5"
                  value={config.stop_loss_percentage}
                  onChange={(e) => handleInputChange('stop_loss_percentage', parseFloat(e.target.value))}
                  className="slider"
                />
              </div>
              <span className="current-value">{config.stop_loss_percentage.toFixed(1)}%</span>
            </div>

            {/* Confidence Threshold */}
            <div className="setting-item">
              <label htmlFor="confidence-threshold">
                Confidence Threshold
                <span className="help-text">Min confidence for trades</span>
              </label>
              <div className="input-with-slider">
                <input
                  id="confidence-threshold"
                  type="number"
                  min="50"
                  max="100"
                  step="5"
                  value={config.confidence_threshold}
                  onChange={(e) => handleInputChange('confidence_threshold', parseInt(e.target.value))}
                />
                <input
                  type="range"
                  min="50"
                  max="100"
                  step="5"
                  value={config.confidence_threshold}
                  onChange={(e) => handleInputChange('confidence_threshold', parseInt(e.target.value))}
                  className="slider"
                />
              </div>
              <span className="current-value">{config.confidence_threshold}%</span>
            </div>

            {/* Cooldown */}
            <div className="setting-item">
              <label htmlFor="cooldown-minutes">
                Cooldown Period
                <span className="help-text">Minutes between analysis</span>
              </label>
              <div className="input-with-slider">
                <input
                  id="cooldown-minutes"
                  type="number"
                  min="5"
                  max="120"
                  step="5"
                  value={config.cooldown_minutes}
                  onChange={(e) => handleInputChange('cooldown_minutes', parseInt(e.target.value))}
                />
                <input
                  type="range"
                  min="5"
                  max="120"
                  step="5"
                  value={config.cooldown_minutes}
                  onChange={(e) => handleInputChange('cooldown_minutes', parseInt(e.target.value))}
                  className="slider"
                />
              </div>
              <span className="current-value">{config.cooldown_minutes} min</span>
            </div>
          </div>
        </div>

        {/* Watchlist */}
        <div className="settings-section">
          <div className="section-title">Watchlist Symbols</div>
          <p className="section-description">
            Manage which crypto symbols the AI analyzes
          </p>

          <div className="watchlist-container">
            <div className="add-symbol">
              <input
                type="text"
                placeholder="e.g., BTC/USDT, ETH/USDT"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
              />
              <button onClick={handleAddSymbol} className="btn-add">
                Add Symbol
              </button>
            </div>

            <div className="symbols-list">
              {config.watchlist_symbols.map((symbol, idx) => (
                <div key={idx} className="symbol-tag">
                  <span>{symbol}</span>
                  <button
                    onClick={() => handleRemoveSymbol(symbol)}
                    className="btn-remove"
                    title="Remove symbol"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            {config.watchlist_symbols.length === 0 && (
              <p className="empty-message">No symbols added. Add at least one to enable AI analysis.</p>
            )}
          </div>
        </div>

        {/* Info Box */}
        <div className="settings-section info-box">
          <div className="section-title">📋 Configuration Guide</div>
          <ul>
            <li><strong>Max Daily Trades:</strong> Limits the number of trades AI can execute per day</li>
            <li><strong>Risk Per Trade:</strong> Maximum portfolio % risked on each trade</li>
            <li><strong>Stop Loss:</strong> Automatic exit price below entry (prevents large losses)</li>
            <li><strong>Confidence Threshold:</strong> AI only executes trades above this confidence level</li>
            <li><strong>Cooldown Period:</strong> Minimum time between consecutive analyses</li>
            <li><strong>Watchlist:</strong> Symbols AI monitors for trading opportunities</li>
          </ul>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="settings-actions">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-save"
        >
          <Save size={18} />
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="btn-reset"
        >
          <RotateCcw size={18} />
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
