import React, { useState, useEffect } from 'react';
import { 
  Plus, Trash2, RefreshCw, CheckCircle, XCircle, 
  Eye, EyeOff, AlertTriangle, Zap, TestTube,
  ExternalLink, Shield
} from 'lucide-react';
import { exchangeAPI } from '../services/exchangeAPI';
import '../styles/ExchangeSettings.css';

// Exchange logos mapping
const EXCHANGE_LOGOS = {
  binance: '🟡',
  kraken: '🟣',
  coinbase: '🔵',
  kucoin: '🟢',
  bybit: '🟠',
  okx: '⚫'
};

export default function ExchangeSettings() {
  const [exchanges, setExchanges] = useState({});
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [testingConnection, setTestingConnection] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  // Form state
  const [formData, setFormData] = useState({
    exchange: '',
    name: '',
    api_key: '',
    api_secret: '',
    passphrase: '',
    paper_trading: true,
    use_testnet: true,
    max_trade_size: 1000,
    max_daily_trades: 50,
    is_default: false
  });
  
  const [showSecrets, setShowSecrets] = useState({
    api_key: false,
    api_secret: false,
    passphrase: false
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [exchangesRes, configsRes] = await Promise.all([
        exchangeAPI.getSupportedExchanges(),
        exchangeAPI.getConfigs()
      ]);
      setExchanges(exchangesRes.exchanges || {});
      setConfigs(configsRes.configs || []);
    } catch (error) {
      showMessage('error', 'Failed to load exchange data');
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingConfig) {
        await exchangeAPI.updateConfig(editingConfig.id, formData);
        showMessage('success', 'Exchange updated successfully');
      } else {
        await exchangeAPI.createConfig(formData);
        showMessage('success', 'Exchange added successfully');
      }
      
      resetForm();
      await loadData();
    } catch (error) {
      showMessage('error', error.message);
    }
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setFormData({
      exchange: config.exchange,
      name: config.name || '',
      api_key: '', // Don't pre-fill secrets
      api_secret: '',
      passphrase: '',
      paper_trading: config.paper_trading,
      use_testnet: config.use_testnet,
      max_trade_size: config.max_trade_size,
      max_daily_trades: config.max_daily_trades,
      is_default: config.is_default
    });
    setShowForm(true);
  };

  const handleDelete = async (configId, exchangeName) => {
    if (!window.confirm(`Delete ${exchangeName} configuration? This cannot be undone.`)) {
      return;
    }
    
    try {
      await exchangeAPI.deleteConfig(configId);
      showMessage('success', `${exchangeName} configuration deleted`);
      await loadData();
    } catch (error) {
      showMessage('error', 'Failed to delete configuration');
    }
  };

  const handleTestConnection = async (configId) => {
    setTestingConnection(configId);
    
    try {
      const result = await exchangeAPI.testConnection({ exchange_id: configId });
      
      if (result.status === 'success') {
        showMessage('success', 'Connection successful!');
      } else {
        showMessage('error', result.message || 'Connection failed');
      }
      
      await loadData(); // Refresh to show updated status
    } catch (error) {
      showMessage('error', 'Connection test failed');
    } finally {
      setTestingConnection(null);
    }
  };

  const handleToggleActive = async (configId) => {
    try {
      await exchangeAPI.toggleActive(configId);
      await loadData();
    } catch (error) {
      showMessage('error', 'Failed to toggle exchange status');
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingConfig(null);
    setFormData({
      exchange: '',
      name: '',
      api_key: '',
      api_secret: '',
      passphrase: '',
      paper_trading: true,
      use_testnet: true,
      max_trade_size: 1000,
      max_daily_trades: 50,
      is_default: false
    });
    setShowSecrets({ api_key: false, api_secret: false, passphrase: false });
  };

  const selectedExchange = exchanges[formData.exchange] || {};

  if (loading) {
    return (
      <div className="exchange-settings">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading exchanges...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="exchange-settings">
      <div className="exchange-header">
        <div>
          <h2>🔗 Exchange Configuration</h2>
          <p>Connect your exchange accounts to enable live trading</p>
        </div>
        <button 
          className="btn-add-exchange"
          onClick={() => setShowForm(true)}
        >
          <Plus size={18} />
          Add Exchange
        </button>
      </div>

      {message.text && (
        <div className={`alert alert-${message.type}`}>
          {message.type === 'success' ? <CheckCircle size={18} /> : <XCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Warning Banner */}
      <div className="warning-banner">
        <AlertTriangle size={20} />
        <div>
          <strong>Security Notice:</strong> API keys are encrypted and stored securely. 
          Always use testnet/paper trading first. Never share your API secrets.
        </div>
      </div>

      {/* Configured Exchanges */}
      <div className="configured-exchanges">
        <h3>Configured Exchanges ({configs.length})</h3>
        
        {configs.length === 0 ? (
          <div className="empty-state">
            <Zap size={48} />
            <p>No exchanges configured yet</p>
            <span>Add an exchange to start trading</span>
          </div>
        ) : (
          <div className="exchange-cards">
            {configs.map(config => (
              <div 
                key={config.id} 
                className={`exchange-card ${!config.is_active ? 'inactive' : ''}`}
              >
                <div className="card-header">
                  <div className="exchange-info">
                    <span className="exchange-logo">{EXCHANGE_LOGOS[config.exchange] || '🔷'}</span>
                    <div>
                      <h4>{config.name || exchanges[config.exchange]?.name}</h4>
                      <span className="exchange-id">{config.exchange.toUpperCase()}</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button 
                      className={`btn-icon ${testingConnection === config.id ? 'testing' : ''}`}
                      onClick={() => handleTestConnection(config.id)}
                      title="Test connection"
                      disabled={testingConnection === config.id}
                    >
                      {testingConnection === config.id ? (
                        <RefreshCw size={16} className="spinning" />
                      ) : (
                        <TestTube size={16} />
                      )}
                    </button>
                    <button 
                      className="btn-icon"
                      onClick={() => handleEdit(config)}
                      title="Edit"
                    >
                      <Eye size={16} />
                    </button>
                    <button 
                      className="btn-icon danger"
                      onClick={() => handleDelete(config.id, config.name)}
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="card-body">
                  <div className="config-row">
                    <span>API Key:</span>
                    <code>{config.api_key_masked}</code>
                  </div>
                  <div className="config-row">
                    <span>Mode:</span>
                    <span className={`mode-badge ${config.paper_trading ? 'paper' : 'live'}`}>
                      {config.paper_trading ? '📝 Paper Trading' : '💰 Live Trading'}
                    </span>
                  </div>
                  <div className="config-row">
                    <span>Testnet:</span>
                    <span className={config.use_testnet ? 'yes' : 'no'}>
                      {config.use_testnet ? '✅ Yes' : '❌ No'}
                    </span>
                  </div>
                  <div className="config-row">
                    <span>Max Trade Size:</span>
                    <span>${config.max_trade_size.toLocaleString()}</span>
                  </div>
                </div>

                <div className="card-footer">
                  <div className={`connection-status status-${config.connection_status}`}>
                    {config.connection_status === 'connected' && <CheckCircle size={14} />}
                    {config.connection_status === 'failed' && <XCircle size={14} />}
                    {config.connection_status === 'untested' && <AlertTriangle size={14} />}
                    <span>{config.connection_status}</span>
                  </div>
                  <div className="footer-actions">
                    {config.is_default && <span className="default-badge">Default</span>}
                    <button 
                      className={`toggle-btn ${config.is_active ? 'active' : ''}`}
                      onClick={() => handleToggleActive(config.id)}
                    >
                      {config.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add/Edit Form Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && resetForm()}>
          <div className="exchange-form-modal">
            <div className="modal-header">
              <h3>{editingConfig ? 'Edit Exchange' : 'Add New Exchange'}</h3>
              <button className="btn-close" onClick={resetForm}>×</button>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Exchange Selection */}
              {!editingConfig && (
                <div className="form-group">
                  <label>Select Exchange</label>
                  <div className="exchange-grid">
                    {Object.entries(exchanges).map(([key, exchange]) => (
                      <button
                        key={key}
                        type="button"
                        className={`exchange-option ${formData.exchange === key ? 'selected' : ''}`}
                        onClick={() => handleInputChange('exchange', key)}
                      >
                        <span className="logo">{EXCHANGE_LOGOS[key] || '🔷'}</span>
                        <span className="name">{exchange.name}</span>
                        {exchange.has_testnet && <span className="testnet-badge">Testnet</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {(formData.exchange || editingConfig) && (
                <>
                  {/* Name */}
                  <div className="form-group">
                    <label>Account Name (optional)</label>
                    <input
                      type="text"
                      placeholder="e.g., Main Trading Account"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                    />
                  </div>

                  {/* API Key */}
                  <div className="form-group">
                    <label>API Key *</label>
                    <div className="secret-input">
                      <input
                        type={showSecrets.api_key ? 'text' : 'password'}
                        placeholder={editingConfig ? '(unchanged)' : 'Enter API Key'}
                        value={formData.api_key}
                        onChange={(e) => handleInputChange('api_key', e.target.value)}
                        required={!editingConfig}
                      />
                      <button
                        type="button"
                        className="toggle-visibility"
                        onClick={() => setShowSecrets(prev => ({ ...prev, api_key: !prev.api_key }))}
                      >
                        {showSecrets.api_key ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  {/* API Secret */}
                  <div className="form-group">
                    <label>API Secret *</label>
                    <div className="secret-input">
                      <input
                        type={showSecrets.api_secret ? 'text' : 'password'}
                        placeholder={editingConfig ? '(unchanged)' : 'Enter API Secret'}
                        value={formData.api_secret}
                        onChange={(e) => handleInputChange('api_secret', e.target.value)}
                        required={!editingConfig}
                      />
                      <button
                        type="button"
                        className="toggle-visibility"
                        onClick={() => setShowSecrets(prev => ({ ...prev, api_secret: !prev.api_secret }))}
                      >
                        {showSecrets.api_secret ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  {/* Passphrase (if required) */}
                  {(selectedExchange.requires_passphrase || 
                    (editingConfig && exchanges[editingConfig.exchange]?.requires_passphrase)) && (
                    <div className="form-group">
                      <label>Passphrase *</label>
                      <div className="secret-input">
                        <input
                          type={showSecrets.passphrase ? 'text' : 'password'}
                          placeholder={editingConfig ? '(unchanged)' : 'Enter Passphrase'}
                          value={formData.passphrase}
                          onChange={(e) => handleInputChange('passphrase', e.target.value)}
                          required={!editingConfig}
                        />
                        <button
                          type="button"
                          className="toggle-visibility"
                          onClick={() => setShowSecrets(prev => ({ ...prev, passphrase: !prev.passphrase }))}
                        >
                          {showSecrets.passphrase ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Trading Mode */}
                  <div className="form-row">
                    <div className="form-group checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.paper_trading}
                          onChange={(e) => handleInputChange('paper_trading', e.target.checked)}
                        />
                        <span>Paper Trading Mode</span>
                      </label>
                      <small>Simulated trades, no real money</small>
                    </div>

                    <div className="form-group checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.use_testnet}
                          onChange={(e) => handleInputChange('use_testnet', e.target.checked)}
                          disabled={!selectedExchange.has_testnet && !exchanges[editingConfig?.exchange]?.has_testnet}
                        />
                        <span>Use Testnet</span>
                      </label>
                      <small>Connect to sandbox environment</small>
                    </div>
                  </div>

                  {/* Limits */}
                  <div className="form-row">
                    <div className="form-group">
                      <label>Max Trade Size ($)</label>
                      <input
                        type="number"
                        min="10"
                        max="1000000"
                        value={formData.max_trade_size}
                        onChange={(e) => handleInputChange('max_trade_size', parseFloat(e.target.value))}
                      />
                    </div>

                    <div className="form-group">
                      <label>Max Daily Trades</label>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={formData.max_daily_trades}
                        onChange={(e) => handleInputChange('max_daily_trades', parseInt(e.target.value))}
                      />
                    </div>
                  </div>

                  {/* Set as Default */}
                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={formData.is_default}
                        onChange={(e) => handleInputChange('is_default', e.target.checked)}
                      />
                      <span>Set as Default Exchange</span>
                    </label>
                  </div>

                  {/* Live Trading Warning */}
                  {!formData.paper_trading && (
                    <div className="live-warning">
                      <Shield size={20} />
                      <div>
                        <strong>⚠️ Live Trading Enabled</strong>
                        <p>Real money will be used. Make sure you understand the risks.</p>
                      </div>
                    </div>
                  )}

                  {/* Form Actions */}
                  <div className="form-actions">
                    <button type="button" className="btn-cancel" onClick={resetForm}>
                      Cancel
                    </button>
                    <button type="submit" className="btn-save">
                      {editingConfig ? 'Update Exchange' : 'Add Exchange'}
                    </button>
                  </div>
                </>
              )}
            </form>

            {/* API Docs Link */}
            {formData.exchange && (
              <div className="api-docs-link">
                <ExternalLink size={14} />
                <a 
                  href={selectedExchange.api_docs || '#'} 
                  target="_blank" 
                  rel="noopener noreferrer"
                >
                  How to get API keys for {selectedExchange.name || formData.exchange}
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
