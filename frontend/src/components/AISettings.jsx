import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, AlertCircle, Plus, X, Search } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import '../styles/AISettings.css';

// Popular cryptocurrencies
const POPULAR_CRYPTOS = [
  { symbol: 'BTC/USDT', name: 'Bitcoin', icon: '₿' },
  { symbol: 'ETH/USDT', name: 'Ethereum', icon: 'Ξ' },
  { symbol: 'BNB/USDT', name: 'Binance Coin', icon: '🔶' },
  { symbol: 'SOL/USDT', name: 'Solana', icon: '◎' },
  { symbol: 'XRP/USDT', name: 'Ripple', icon: '✕' },
  { symbol: 'ADA/USDT', name: 'Cardano', icon: '₳' },
  { symbol: 'AVAX/USDT', name: 'Avalanche', icon: '🔺' },
  { symbol: 'DOGE/USDT', name: 'Dogecoin', icon: 'Ð' },
  { symbol: 'DOT/USDT', name: 'Polkadot', icon: '●' },
  { symbol: 'MATIC/USDT', name: 'Polygon', icon: '⬡' },
  { symbol: 'LINK/USDT', name: 'Chainlink', icon: '🔗' },
  { symbol: 'UNI/USDT', name: 'Uniswap', icon: '🦄' },
  { symbol: 'LTC/USDT', name: 'Litecoin', icon: 'Ł' },
  { symbol: 'ATOM/USDT', name: 'Cosmos', icon: '⚛' },
  { symbol: 'XLM/USDT', name: 'Stellar', icon: '✱' }
];

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
  const [searchTerm, setSearchTerm] = useState('');
  const [showCryptoSelector, setShowCryptoSelector] = useState(false);

  // Fetch current config
  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const data = await aiAPI.getConfig();
      if (data && data.config) {
        // Ensure all numeric values are valid
        setConfig({
          ...data.config,
          max_daily_trades: data.config.max_daily_trades || 5,
          risk_percentage: data.config.risk_percentage || 2,
          stop_loss_percentage: data.config.stop_loss_percentage || 5,
          confidence_threshold: data.config.confidence_threshold || 65,
          cooldown_minutes: data.config.cooldown_minutes || 30,
          watchlist_symbols: data.config.watchlist_symbols || ['BTC/USDT', 'ETH/USDT'],
          enabled: data.config.enabled !== undefined ? data.config.enabled : true
        });
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
    // Protect against NaN for numeric fields
    let safeValue = value;
    if (typeof value === 'number' && isNaN(value)) {
      const defaults = {
        max_daily_trades: 5,
        risk_percentage: 2,
        stop_loss_percentage: 5,
        confidence_threshold: 65,
        cooldown_minutes: 30
      };
      safeValue = defaults[field] || 0;
    }
    
    setConfig(prev => ({
      ...prev,
      [field]: safeValue
    }));
  };

  const handleAddSymbol = (symbol) => {
    if (!config.watchlist_symbols.includes(symbol)) {
      setConfig(prev => ({
        ...prev,
        watchlist_symbols: [...prev.watchlist_symbols, symbol]
      }));
      setShowCryptoSelector(false);
      setSearchTerm('');
    }
  };

  const handleRemoveSymbol = (symbol) => {
    setConfig(prev => ({
      ...prev,
      watchlist_symbols: prev.watchlist_symbols.filter(s => s !== symbol)
    }));
  };

  const getFilteredCryptos = () => {
    const search = searchTerm.toLowerCase();
    return POPULAR_CRYPTOS.filter(crypto => 
      !config.watchlist_symbols.includes(crypto.symbol) &&
      (crypto.symbol.toLowerCase().includes(search) ||
       crypto.name.toLowerCase().includes(search))
    );
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
              <span className="current-value">{config.risk_percentage?.toFixed(1) || '2.0'}%</span>
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
              <span className="current-value">{config.stop_loss_percentage?.toFixed(1) || '5.0'}%</span>
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
            Select cryptocurrencies for AI to analyze
          </p>

          <div className="watchlist-container">
            {/* Current symbols */}
            <div className="symbols-list">
              {config.watchlist_symbols.map((symbol, idx) => {
                const crypto = POPULAR_CRYPTOS.find(c => c.symbol === symbol);
                return (
                  <div key={idx} className="symbol-tag">
                    <span className="symbol-icon">{crypto?.icon || '💎'}</span>
                    <span className="symbol-name">{symbol}</span>
                    <button
                      onClick={() => handleRemoveSymbol(symbol)}
                      className="btn-remove"
                      title="Remove symbol"
                    >
                      <X size={14} />
                    </button>
                  </div>
                );
              })}
              
              {/* Add button */}
              <button 
                className="symbol-tag add-button"
                onClick={() => setShowCryptoSelector(!showCryptoSelector)}
              >
                <Plus size={16} />
                <span>Add Crypto</span>
              </button>
            </div>

            {/* Crypto selector dropdown */}
            {showCryptoSelector && (
              <div className="crypto-selector">
                <div className="selector-header">
                  <div className="search-box">
                    <Search size={16} />
                    <input
                      type="text"
                      placeholder="Search cryptocurrencies..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <button 
                    className="btn-close"
                    onClick={() => {
                      setShowCryptoSelector(false);
                      setSearchTerm('');
                    }}
                  >
                    <X size={18} />
                  </button>
                </div>
                
                <div className="crypto-list">
                  {getFilteredCryptos().map((crypto) => (
                    <button
                      key={crypto.symbol}
                      className="crypto-item"
                      onClick={() => handleAddSymbol(crypto.symbol)}
                    >
                      <span className="crypto-icon">{crypto.icon}</span>
                      <div className="crypto-info">
                        <span className="crypto-symbol">{crypto.symbol}</span>
                        <span className="crypto-name">{crypto.name}</span>
                      </div>
                      <Plus size={16} className="add-icon" />
                    </button>
                  ))}
                  
                  {getFilteredCryptos().length === 0 && (
                    <div className="empty-search">
                      <p>No cryptocurrencies found</p>
                      <small>Try a different search term</small>
                    </div>
                  )}
                </div>
              </div>
            )}

            {config.watchlist_symbols.length === 0 && (
              <p className="empty-message">
                No symbols added. Click "Add Crypto" to select cryptocurrencies.
              </p>
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
