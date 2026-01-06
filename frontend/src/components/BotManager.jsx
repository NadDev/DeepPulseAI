import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  Plus, 
  Edit, 
  Trash2, 
  Bot, 
  TrendingUp, 
  Activity,
  DollarSign,
  Target,
  Settings,
  X,
  Search
} from 'lucide-react';
import './BotManager.css';
import { cryptoAPI } from '../services/api';

// Popular trading pairs on Binance
const POPULAR_SYMBOLS = [
  { symbol: 'BTCUSDT', name: 'Bitcoin' },
  { symbol: 'ETHUSDT', name: 'Ethereum' },
  { symbol: 'SOLUSDT', name: 'Solana' },
  { symbol: 'BNBUSDT', name: 'BNB' },
  { symbol: 'XRPUSDT', name: 'XRP' },
  { symbol: 'ADAUSDT', name: 'Cardano' },
  { symbol: 'DOGEUSDT', name: 'Dogecoin' },
  { symbol: 'AVAXUSDT', name: 'Avalanche' },
  { symbol: 'DOTUSDT', name: 'Polkadot' },
  { symbol: 'MATICUSDT', name: 'Polygon' },
  { symbol: 'LINKUSDT', name: 'Chainlink' },
  { symbol: 'LTCUSDT', name: 'Litecoin' },
  { symbol: 'ATOMUSDT', name: 'Cosmos' },
  { symbol: 'UNIUSDT', name: 'Uniswap' },
  { symbol: 'NEARUSDT', name: 'NEAR Protocol' },
  { symbol: 'AAVEUSDT', name: 'Aave' },
  { symbol: 'ARBUSDT', name: 'Arbitrum' },
  { symbol: 'OPUSDT', name: 'Optimism' },
  { symbol: 'APTUSDT', name: 'Aptos' },
  { symbol: 'SUIUSDT', name: 'Sui' },
];

const BotManager = () => {
  const [bots, setBots] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingBot, setEditingBot] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    strategy: 'trend_following',
    symbols: ['BTCUSDT'],
    paper_trading: true,
    risk_percent: 2.0,
    max_drawdown: 20.0,
    config: {}
  });

  useEffect(() => {
    loadBots();
    loadStrategies();
  }, []);

  const loadBots = async () => {
    try {
      const response = await cryptoAPI.getBots();
      setBots(response.bots || []);
    } catch (error) {
      console.error('Error loading bots:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStrategies = async () => {
    try {
      const response = await cryptoAPI.getStrategies();
      setStrategies(response.strategies || []);
    } catch (error) {
      console.error('Error loading strategies:', error);
    }
  };

  const handleStartBot = async (botId) => {
    try {
      await cryptoAPI.startBot(botId);
      loadBots();
    } catch (error) {
      console.error('Error starting bot:', error);
      alert('Failed to start bot');
    }
  };

  const handlePauseBot = async (botId) => {
    try {
      await cryptoAPI.pauseBot(botId);
      loadBots();
    } catch (error) {
      console.error('Error pausing bot:', error);
      alert('Failed to pause bot');
    }
  };

  const handleStopBot = async (botId) => {
    try {
      await cryptoAPI.stopBot(botId);
      loadBots();
    } catch (error) {
      console.error('Error stopping bot:', error);
      alert('Failed to stop bot');
    }
  };

  const handleDeleteBot = async (botId) => {
    if (!window.confirm('Are you sure you want to delete this bot?')) {
      return;
    }

    try {
      await cryptoAPI.deleteBot(botId);
      loadBots();
    } catch (error) {
      console.error('Error deleting bot:', error);
      alert('Failed to delete bot');
    }
  };

  const handleCreateBot = async (e) => {
    e.preventDefault();

    try {
      await cryptoAPI.createBot(formData);
      setShowCreateModal(false);
      resetForm();
      loadBots();
    } catch (error) {
      console.error('Error creating bot:', error);
      alert('Failed to create bot: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleUpdateBot = async (e) => {
    e.preventDefault();

    try {
      await cryptoAPI.updateBot(editingBot.id, formData);
      setEditingBot(null);
      resetForm();
      loadBots();
    } catch (error) {
      console.error('Error updating bot:', error);
      alert('Failed to update bot: ' + (error.response?.data?.detail || error.message));
    }
  };

  const openEditModal = (bot) => {
    setEditingBot(bot);
    setFormData({
      name: bot.name,
      strategy: bot.strategy,
      symbols: bot.symbols || ['BTCUSDT'],
      paper_trading: bot.paper_trading,
      risk_percent: bot.risk_percent,
      max_drawdown: bot.max_drawdown,
      config: bot.config || {}
    });
  };

  const resetForm = () => {
    setFormData({
      name: '',
      strategy: 'trend_following',
      symbols: ['BTCUSDT'],
      paper_trading: true,
      risk_percent: 2.0,
      max_drawdown: 20.0,
      config: {}
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'RUNNING': return 'status-active';
      case 'ACTIVE': return 'status-active';
      case 'PAUSED': return 'status-paused';
      case 'IDLE': return 'status-inactive';
      case 'INACTIVE': return 'status-inactive';
      case 'ERROR': return 'status-error';
      default: return 'status-inactive';
    }
  };

  const getStrategyLabel = (strategyName) => {
    const strategy = strategies.find(s => s.name === strategyName);
    return strategy ? strategy.class_name : strategyName;
  };

  if (loading) {
    return <div className="bot-manager-loading">Loading bots...</div>;
  }

  return (
    <div className="bot-manager">
      <div className="bot-manager-header">
        <div>
          <h1><Bot size={32} /> Bot Manager</h1>
          <p>Manage your trading bots and strategies</p>
        </div>
        <button 
          className="btn-create-bot"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={18} /> Create New Bot
        </button>
      </div>

      {bots.length === 0 ? (
        <div className="empty-state">
          <Bot size={64} />
          <h2>No Bots Yet</h2>
          <p>Create your first trading bot to get started</p>
          <button 
            className="btn-create-bot"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={18} /> Create Bot
          </button>
        </div>
      ) : (
        <div className="bots-grid">
          {bots.map(bot => (
            <div key={bot.id} className="bot-card">
              <div className="bot-card-header">
                <div className="bot-info">
                  <h3>{bot.name}</h3>
                  <span className={`bot-status ${getStatusColor(bot.status)}`}>
                    {bot.status}
                  </span>
                </div>
                <div className="bot-actions">
                  {(bot.status === 'IDLE' || bot.status === 'INACTIVE' || bot.status === 'PAUSED' || bot.status === 'ERROR') && bot.status !== 'RUNNING' && (
                    <button 
                      className="btn-icon btn-success"
                      onClick={() => handleStartBot(bot.id)}
                      title="Start Bot"
                    >
                      <Play size={16} />
                    </button>
                  )}
                  {(bot.status === 'RUNNING' || bot.status === 'ACTIVE') && (
                    <>
                      <button 
                        className="btn-icon btn-warning"
                        onClick={() => handlePauseBot(bot.id)}
                        title="Pause Bot"
                      >
                        <Pause size={16} />
                      </button>
                      <button 
                        className="btn-icon btn-danger"
                        onClick={() => handleStopBot(bot.id)}
                        title="Stop Bot"
                      >
                        <Square size={16} />
                      </button>
                    </>
                  )}
                  {bot.status !== 'RUNNING' && bot.status !== 'ACTIVE' && (
                    <>
                      <button 
                        className="btn-icon"
                        onClick={() => openEditModal(bot)}
                        title="Edit Bot"
                      >
                        <Edit size={16} />
                      </button>
                      <button 
                        className="btn-icon btn-danger"
                        onClick={() => handleDeleteBot(bot.id)}
                        title="Delete Bot"
                      >
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div className="bot-details">
                <div className="detail-item">
                  <TrendingUp size={16} />
                  <span>Strategy: {getStrategyLabel(bot.strategy)}</span>
                </div>
                <div className="detail-item">
                  <Activity size={16} />
                  <span>Trades: {bot.total_trades} ({bot.open_trades} open)</span>
                </div>
                <div className="detail-item">
                  <DollarSign size={16} />
                  <span className={bot.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                    PnL: ${bot.total_pnl.toFixed(2)}
                  </span>
                </div>
                <div className="detail-item">
                  <Target size={16} />
                  <span>Win Rate: {bot.win_rate.toFixed(1)}%</span>
                </div>
              </div>

              <div className="bot-config">
                <div className="config-item">
                  <span>Paper Trading:</span>
                  <strong>{bot.paper_trading ? 'Yes' : 'No'}</strong>
                </div>
                <div className="config-item">
                  <span>Risk:</span>
                  <strong>{bot.risk_percent}%</strong>
                </div>
                <div className="config-item">
                  <span>Max Drawdown:</span>
                  <strong>{bot.max_drawdown}%</strong>
                </div>
              </div>

              {bot.symbols && bot.symbols.length > 0 && (
                <div className="bot-symbols">
                  {bot.symbols.map((symbol, idx) => (
                    <span key={idx} className="symbol-tag">{symbol}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editingBot) && (
        <div className="modal-overlay" onClick={() => {
          setShowCreateModal(false);
          setEditingBot(null);
          resetForm();
        }}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>{editingBot ? 'Edit Bot' : 'Create New Bot'}</h2>
            
            <form onSubmit={editingBot ? handleUpdateBot : handleCreateBot}>
              <div className="form-group">
                <label>Bot Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="My Trading Bot"
                  required
                />
              </div>

              <div className="form-group">
                <label>Strategy</label>
                <select
                  value={formData.strategy}
                  onChange={e => setFormData({...formData, strategy: e.target.value})}
                  required
                >
                  {strategies.map(strategy => (
                    <option key={strategy.name} value={strategy.name}>
                      {strategy.class_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Trading Pairs</label>
                <div className="symbol-selector">
                  <div className="selected-symbols">
                    {formData.symbols.map((symbol, idx) => (
                      <span key={idx} className="selected-symbol-tag">
                        {symbol}
                        <button 
                          type="button"
                          onClick={() => setFormData({
                            ...formData,
                            symbols: formData.symbols.filter((_, i) => i !== idx)
                          })}
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="symbol-dropdown">
                    <select
                      value=""
                      onChange={e => {
                        if (e.target.value && !formData.symbols.includes(e.target.value)) {
                          setFormData({
                            ...formData,
                            symbols: [...formData.symbols, e.target.value]
                          });
                        }
                      }}
                    >
                      <option value="">+ Add trading pair...</option>
                      {POPULAR_SYMBOLS.filter(s => !formData.symbols.includes(s.symbol)).map(s => (
                        <option key={s.symbol} value={s.symbol}>
                          {s.symbol} - {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {formData.symbols.length === 0 && (
                  <span className="form-error">Select at least one trading pair</span>
                )}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Risk per Trade (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="10"
                    value={formData.risk_percent}
                    onChange={e => setFormData({...formData, risk_percent: parseFloat(e.target.value)})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Max Drawdown (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="5"
                    max="50"
                    value={formData.max_drawdown}
                    onChange={e => setFormData({...formData, max_drawdown: parseFloat(e.target.value)})}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.paper_trading}
                    onChange={e => setFormData({...formData, paper_trading: e.target.checked})}
                  />
                  <span>Paper Trading Mode (Recommended for testing)</span>
                </label>
              </div>

              <div className="modal-actions">
                <button 
                  type="button" 
                  className="btn-secondary"
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingBot(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editingBot ? 'Update Bot' : 'Create Bot'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BotManager;
