import React, { useState, useEffect, useCallback } from 'react';
import { 
  Star, 
  Plus, 
  Trash2, 
  Search, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown,
  Bell,
  BellOff,
  Edit2,
  Check,
  X,
  Eye,
  Filter,
  ArrowUpDown,
  Sparkles,
  AlertTriangle,
  Loader2
} from 'lucide-react';
import { supabase } from '../services/supabaseClient';
import WatchlistRecommendations from './WatchlistRecommendations';
import '../styles/WatchlistManager.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const POPULAR_CRYPTOS = [
  { symbol: 'BTC', name: 'Bitcoin' },
  { symbol: 'ETH', name: 'Ethereum' },
  { symbol: 'SOL', name: 'Solana' },
  { symbol: 'XRP', name: 'Ripple' },
  { symbol: 'ADA', name: 'Cardano' },
  { symbol: 'DOGE', name: 'Dogecoin' },
  { symbol: 'AVAX', name: 'Avalanche' },
  { symbol: 'DOT', name: 'Polkadot' },
  { symbol: 'LINK', name: 'Chainlink' },
  { symbol: 'MATIC', name: 'Polygon' },
  { symbol: 'SHIB', name: 'Shiba Inu' },
  { symbol: 'LTC', name: 'Litecoin' },
  { symbol: 'ATOM', name: 'Cosmos' },
  { symbol: 'UNI', name: 'Uniswap' },
  { symbol: 'XLM', name: 'Stellar' }
];

const WatchlistManager = ({ updateButtons }) => {
  const [watchlists, setWatchlists] = useState([]);
  const [activeWatchlist, setActiveWatchlist] = useState(null);
  const [activeTab, setActiveTab] = useState('watchlist'); // 'watchlist' or 'recommendations'
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  
  // Form states
  const [searchQuery, setSearchQuery] = useState('');
  const [newSymbol, setNewSymbol] = useState('');
  const [symbolNotes, setSymbolNotes] = useState('');
  const [symbolPriority, setSymbolPriority] = useState('medium');
  const [alertPriceAbove, setAlertPriceAbove] = useState('');
  const [alertPriceBelow, setAlertPriceBelow] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [validatingSymbol, setValidatingSymbol] = useState(false);
  const [symbolValid, setSymbolValid] = useState(null);
  
  // Filter/Sort states
  const [sortBy, setSortBy] = useState('symbol');
  const [sortOrder, setSortOrder] = useState('asc');
  const [filterPriority, setFilterPriority] = useState('all');

  // Get auth token from localStorage
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token || ''}`
    };
  };

  // Fetch watchlists
  const fetchWatchlists = useCallback(async () => {
    try {
      setLoading(true);
      const headers = getAuthHeaders();
      const response = await fetch(`${API_URL}/api/watchlist`, { headers });
      
      if (!response.ok) throw new Error('Failed to fetch watchlists');
      
      const data = await response.json();
      setWatchlists(data);
      
      // Set active watchlist to default or first
      const defaultList = data.find(w => w.is_default) || data[0];
      if (defaultList) {
        setActiveWatchlist(defaultList);
        setItems(defaultList.items || []);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching watchlists:', err);
      setError('Erreur lors du chargement des watchlists');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlists();
  }, [fetchWatchlists]);

  // Add symbol to watchlist
  const handleAddSymbol = async () => {
    if (!newSymbol.trim()) {
      setError('Veuillez entrer un symbole');
      return;
    }
    
    if (symbolValid === false) {
      setError(`${newSymbol} n'existe pas sur Binance`);
      return;
    }
    
    if (symbolValid === null) {
      setError('Veuillez attendre la validation du symbole');
      return;
    }
    
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_URL}/api/watchlist/add`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          symbol: newSymbol.toUpperCase(),
          watchlist_id: activeWatchlist?.id,
          notes: symbolNotes,
          priority: symbolPriority
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add symbol');
      }
      
      setSuccess(`${newSymbol.toUpperCase()} ajouté à la watchlist`);
      setShowAddModal(false);
      resetAddForm();
      fetchWatchlists();
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    }
  };
  
  // Validate symbol exists on Binance
  const validateSymbol = async (symbol) => {
    if (!symbol) {
      setSymbolValid(null);
      return;
    }
    
    setValidatingSymbol(true);
    setSymbolValid(null);
    
    try {
      // Try to fetch ticker data from Binance to verify symbol exists
      const binanceSymbol = symbol.toUpperCase().endsWith('USDT') ? symbol.toUpperCase() : `${symbol.toUpperCase()}USDT`;
      const response = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${binanceSymbol}`, {
        method: 'GET'
      });
      
      if (response.ok) {
        setSymbolValid(true);
        console.log(`✅ Symbol ${binanceSymbol} is valid on Binance`);
      } else {
        setSymbolValid(false);
        console.log(`❌ Symbol ${binanceSymbol} not found on Binance`);
      }
    } catch (err) {
      console.error('Error validating symbol:', err);
      setSymbolValid(false);
    } finally {
      setValidatingSymbol(false);
    }
  };
  
  // Handle symbol input change with autocomplete
  const handleSymbolChange = (value) => {
    const upper = value.toUpperCase();
    setNewSymbol(upper);
    
    // Generate suggestions from popular cryptos
    if (upper.length > 0) {
      const filtered = POPULAR_CRYPTOS.filter(c => 
        c.symbol.includes(upper) || c.name.toUpperCase().includes(upper)
      );
      setSuggestions(filtered);
      setShowSuggestions(true);
    } else {
      setSuggestions(POPULAR_CRYPTOS.slice(0, 5)); // Show first 5 by default
      setShowSuggestions(false);
    }
    
    // Validate after debounce
    if (upper.length >= 2) {
      setTimeout(() => validateSymbol(upper), 500);
    } else {
      setSymbolValid(null);
    }
  };

  // Remove symbol from watchlist
  const handleRemoveSymbol = async (itemId) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_URL}/api/watchlist/${itemId}`, {
        method: 'DELETE',
        headers
      });
      
      if (!response.ok) throw new Error('Failed to remove symbol');
      
      setSuccess('Symbole supprimé');
      fetchWatchlists();
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Erreur lors de la suppression');
      setTimeout(() => setError(null), 5000);
    }
  };

  // Note: Single watchlist per user - no need to create multiple lists

  // Toggle alerts for item
  const handleToggleAlerts = async (item) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_URL}/api/watchlist/${item.id}/alerts`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          alerts_enabled: !item.alerts_enabled,
          alert_price_above: item.alert_price_above,
          alert_price_below: item.alert_price_below
        })
      });
      
      if (!response.ok) throw new Error('Failed to toggle alerts');
      
      fetchWatchlists();
    } catch (err) {
      setError('Erreur lors de la mise à jour');
      setTimeout(() => setError(null), 5000);
    }
  };

  // Sync with AI Agent
  const handleSyncWithAI = async () => {
    try {
      setSyncing(true);
      const headers = getAuthHeaders();
      
      const symbols = items.map(item => item.symbol);
      
      const response = await fetch(`${API_URL}/api/watchlist/sync`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ symbols })
      });
      
      if (!response.ok) throw new Error('Failed to sync with AI');
      
      setSuccess('Watchlist synchronisée avec l\'agent AI');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Erreur lors de la synchronisation');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSyncing(false);
    }
  };

  // Reset add form
  const resetAddForm = () => {
    setNewSymbol('');
    setSymbolNotes('');
    setSymbolPriority('medium');
  };

  // Filter and sort items
  const getFilteredItems = () => {
    let filtered = [...items];
    
    // Filter by search
    if (searchQuery) {
      filtered = filtered.filter(item => 
        item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.notes && item.notes.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }
    
    // Filter by priority
    if (filterPriority !== 'all') {
      filtered = filtered.filter(item => item.priority === filterPriority);
    }
    
    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'symbol':
          comparison = a.symbol.localeCompare(b.symbol);
          break;
        case 'priority':
          const priorityOrder = { high: 0, medium: 1, low: 2 };
          comparison = priorityOrder[a.priority] - priorityOrder[b.priority];
          break;
        case 'added':
          comparison = new Date(b.added_at) - new Date(a.added_at);
          break;
        default:
          comparison = 0;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return filtered;
  };

  // Get priority badge class
  const getPriorityClass = (priority) => {
    switch (priority) {
      case 'high': return 'priority-high';
      case 'low': return 'priority-low';
      default: return 'priority-medium';
    }
  };

  // Get priority label
  const getPriorityLabel = (priority) => {
    switch (priority) {
      case 'high': return 'Haute';
      case 'low': return 'Basse';
      default: return 'Moyenne';
    }
  };

  // Get suggested cryptos (not in watchlist)
  const getSuggestedCryptos = () => {
    const currentSymbols = items.map(i => i.symbol.toUpperCase());
    return POPULAR_CRYPTOS.filter(c => !currentSymbols.includes(c.symbol));
  };

  if (loading) {
    return (
      <div className="watchlist-loading">
        <Loader2 className="spin" size={32} />
        <p>Chargement des watchlists...</p>
      </div>
    );
  }

  return (
    <div className="watchlist-manager">
      {/* Header */}
      <div className="watchlist-header">
        <div className="header-left">
          <Star className="header-icon" />
          <h2>Gestion des Watchlists</h2>
        </div>
        <div className="header-actions">
          {updateButtons}
          <button 
            className="btn-sync"
            onClick={handleSyncWithAI}
            disabled={syncing || items.length === 0}
          >
            {syncing ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Sparkles size={16} />
            )}
            Sync avec AI
          </button>
          {/* Single watchlist per user - button removed */}
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert alert-error">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          <Check size={16} />
          {success}
        </div>
      )}

      {/* Watchlist Tabs */}
      {watchlists.length > 0 && (
        <div className="watchlist-tabs">
          {watchlists.map(list => (
            <button
              key={list.id}
              className={`watchlist-tab ${activeWatchlist?.id === list.id ? 'active' : ''}`}
              onClick={() => {
                setActiveWatchlist(list);
                setItems(list.items || []);
              }}
            >
              <Star size={14} className={list.is_default ? 'star-filled' : ''} />
              {list.name}
              <span className="tab-count">{list.symbols_count || 0}</span>
            </button>
          ))}
        </div>
      )}

      {/* Content Tabs (Watchlist vs Recommendations) */}
      <div className="content-tabs">
        <button
          className={`content-tab ${activeTab === 'watchlist' ? 'active' : ''}`}
          onClick={() => setActiveTab('watchlist')}
        >
          My Watchlist
        </button>
        <button
          className={`content-tab ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          <Sparkles size={16} />
          Recommendations
        </button>
      </div>

      {/* Recommendations Tab */}
      {activeTab === 'recommendations' && (
        <WatchlistRecommendations onRecommendationAccepted={(symbol) => {
          setSuccess(`✓ ${symbol} ajouté à la watchlist`);
          setTimeout(() => setSuccess(null), 3000);
          fetchWatchlists(); // Refresh watchlist
        }} />
      )}

      {/* Watchlist Tab */}
      {activeTab === 'watchlist' && (
      <>

      {/* Toolbar */}
      <div className="watchlist-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Rechercher un symbole..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        <div className="toolbar-actions">
          <select 
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="filter-select"
          >
            <option value="all">Toutes priorités</option>
            <option value="high">Haute priorité</option>
            <option value="medium">Moyenne priorité</option>
            <option value="low">Basse priorité</option>
          </select>
          
          <select 
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="symbol">Trier par symbole</option>
            <option value="priority">Trier par priorité</option>
            <option value="added">Trier par date</option>
          </select>
          
          <button 
            className="btn-sort-order"
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            title={sortOrder === 'asc' ? 'Ordre croissant' : 'Ordre décroissant'}
          >
            <ArrowUpDown size={16} />
          </button>
          
          <button 
            className="btn-add"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={16} />
            Ajouter
          </button>
        </div>
      </div>

      {/* Items List */}
      <div className="watchlist-items">
        {getFilteredItems().length === 0 ? (
          <div className="empty-state">
            <Star size={48} />
            <h3>Watchlist vide</h3>
            <p>Ajoutez des cryptomonnaies pour commencer à les suivre</p>
            <button 
              className="btn-primary"
              onClick={() => setShowAddModal(true)}
            >
              <Plus size={16} />
              Ajouter un symbole
            </button>
          </div>
        ) : (
          <table className="items-table">
            <thead>
              <tr>
                <th>Symbole</th>
                <th>Priorité</th>
                <th>Notes</th>
                <th>Alertes</th>
                <th>Ajouté le</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {getFilteredItems().map(item => (
                <tr key={item.id}>
                  <td className="symbol-cell">
                    <div className="symbol-info">
                      <span className="symbol-name">{item.symbol}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`priority-badge ${getPriorityClass(item.priority)}`}>
                      {getPriorityLabel(item.priority)}
                    </span>
                  </td>
                  <td className="notes-cell">
                    {item.notes || <span className="no-notes">-</span>}
                  </td>
                  <td>
                    <button 
                      className={`btn-alert ${item.alerts_enabled ? 'active' : ''}`}
                      onClick={() => handleToggleAlerts(item)}
                      title={item.alerts_enabled ? 'Alertes actives' : 'Alertes désactivées'}
                    >
                      {item.alerts_enabled ? <Bell size={16} /> : <BellOff size={16} />}
                    </button>
                  </td>
                  <td className="date-cell">
                    {new Date(item.added_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="actions-cell">
                    <button 
                      className="btn-action delete"
                      onClick={() => handleRemoveSymbol(item.id)}
                      title="Supprimer"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Suggested Cryptos */}
      {getSuggestedCryptos().length > 0 && (
        <div className="suggested-section">
          <h4>Suggestions populaires</h4>
          <div className="suggested-cryptos">
            {getSuggestedCryptos().slice(0, 8).map(crypto => (
              <button
                key={crypto.symbol}
                className="suggested-chip"
                onClick={() => {
                  setNewSymbol(crypto.symbol);
                  setShowAddModal(true);
                }}
              >
                <Plus size={12} />
                {crypto.symbol}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Add Symbol Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Ajouter un symbole</h3>
              <button className="btn-close" onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Symbole *</label>
                <div className="input-wrapper" style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={newSymbol}
                    onChange={(e) => handleSymbolChange(e.target.value)}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                    placeholder="BTC, ETH, SOL..."
                    autoFocus
                    style={{
                      paddingRight: '32px'
                    }}
                  />
                  <div style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)' }}>
                    {validatingSymbol && <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                    {symbolValid === true && <Check size={16} style={{ color: '#10b981' }} />}
                    {symbolValid === false && <AlertTriangle size={16} style={{ color: '#ef4444' }} />}
                  </div>
                </div>
                
                {showSuggestions && suggestions.length > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '4px',
                    marginTop: '4px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    zIndex: 10
                  }}>
                    {suggestions.map(crypto => (
                      <div
                        key={crypto.symbol}
                        onClick={() => {
                          setNewSymbol(crypto.symbol);
                          setShowSuggestions(false);
                          validateSymbol(crypto.symbol);
                        }}
                        style={{
                          padding: '8px 12px',
                          cursor: 'pointer',
                          borderBottom: '1px solid #374151',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#374151'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                      >
                        <span style={{ fontWeight: 'bold', color: '#10b981' }}>{crypto.symbol}</span>
                        <span style={{ fontSize: '12px', color: '#9ca3af' }}>{crypto.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {symbolValid === false && (
                  <p style={{ color: '#ef4444', fontSize: '12px', marginTop: '4px' }}>
                    ⚠️ Ce symbole n'existe pas sur Binance
                  </p>
                )}
              </div>
              
              <div className="form-group">
                <label>Priorité</label>
                <select 
                  value={symbolPriority}
                  onChange={(e) => setSymbolPriority(e.target.value)}
                >
                  <option value="high">Haute - Surveiller activement</option>
                  <option value="medium">Moyenne - Suivi régulier</option>
                  <option value="low">Basse - Observer</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Notes (optionnel)</label>
                <textarea
                  value={symbolNotes}
                  onChange={(e) => setSymbolNotes(e.target.value)}
                  placeholder="Raison de l'ajout, stratégie..."
                  rows={3}
                />
              </div>
              
              {/* Quick add popular */}
              <div className="quick-add">
                <label>Ajout rapide</label>
                <div className="quick-chips">
                  {getSuggestedCryptos().slice(0, 6).map(crypto => (
                    <button
                      key={crypto.symbol}
                      type="button"
                      className={`quick-chip ${newSymbol === crypto.symbol ? 'selected' : ''}`}
                      onClick={() => setNewSymbol(crypto.symbol)}
                    >
                      {crypto.symbol}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-cancel" onClick={() => {
                setShowAddModal(false);
                resetAddForm();
              }}>
                Annuler
              </button>
              <button 
                className="btn-submit"
                onClick={handleAddSymbol}
                disabled={!newSymbol.trim()}
              >
                <Plus size={16} />
                Ajouter
              </button>
            </div>
          </div>
        </div>
      )}

      </>
      )}

      {/* Create Watchlist Modal removed - single watchlist per user */}
    </div>
  );
};

export default WatchlistManager;
