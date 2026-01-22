import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TradeHistoryTable.css';

/**
 * TradeHistoryTable Component
 * Displays trades with filters, sorting, and market context
 */
const TradeHistoryTable = ({ userId }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Filter state
  const [filters, setFilters] = useState({
    days: 30,
    strategy: '',
    symbol: '',
    market_context: '',
    min_pnl: null,
    max_pnl: null,
    status: ''
  });
  
  // Sorting state
  const [sortBy, setSortBy] = useState('entry_time');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Summary stats
  const [stats, setStats] = useState(null);

  // Fetch trades from API
  useEffect(() => {
    fetchTrades();
  }, [filters]);

  const fetchTrades = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Build query params
      const params = new URLSearchParams();
      params.append('days', filters.days);
      if (filters.strategy) params.append('strategy', filters.strategy);
      if (filters.symbol) params.append('symbol', filters.symbol);
      if (filters.market_context) params.append('market_context', filters.market_context);
      if (filters.min_pnl !== null) params.append('min_pnl', filters.min_pnl);
      if (filters.max_pnl !== null) params.append('max_pnl', filters.max_pnl);
      if (filters.status) params.append('status', filters.status);
      
      const response = await axios.get(
        `/api/reports/trades?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setTrades(response.data.trades || []);
      setStats({
        total_trades: response.data.total_trades,
        closed_trades: response.data.closed_trades,
        open_trades: response.data.open_trades,
        total_pnl: response.data.total_pnl,
        win_rate: response.data.win_rate,
        average_pnl: response.data.average_pnl,
        context_breakdown: response.data.context_breakdown
      });
    } catch (err) {
      setError(err.message || 'Failed to fetch trades');
      console.error('Error fetching trades:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle filter changes
  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle sort
  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  // Sort trades
  const sortedTrades = [...trades].sort((a, b) => {
    let aVal = a[sortBy];
    let bVal = b[sortBy];
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  // Get unique values for filter dropdowns
  const strategies = [...new Set(trades.map(t => t.strategy))].sort();
  const symbols = [...new Set(trades.map(t => t.symbol))].sort();
  const contexts = [...new Set(trades.map(t => t.market_context).filter(Boolean))].sort();

  const renderPnL = (pnl, pnlPercent) => {
    if (!pnl && pnl !== 0) return '-';
    const className = pnl >= 0 ? 'text-green' : 'text-red';
    return (
      <span className={className}>
        ${pnl.toFixed(2)} ({pnlPercent ? pnlPercent.toFixed(2) : '0.00'}%)
      </span>
    );
  };

  const renderContextBadge = (context) => {
    if (!context) return <span className="badge badge-gray">Unknown</span>;
    
    const contextClass = {
      'STRONG_BULLISH': 'badge-green',
      'WEAK_BULLISH': 'badge-light-green',
      'NEUTRAL': 'badge-gray',
      'WEAK_BEARISH': 'badge-light-red',
      'STRONG_BEARISH': 'badge-red'
    };
    
    return (
      <span className={`badge ${contextClass[context] || 'badge-gray'}`}>
        {context}
      </span>
    );
  };

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  return (
    <div className="trade-history-container">
      <div className="trade-history-header">
        <h2>📊 Trade History</h2>
      </div>

      {/* Summary Stats */}
      {stats && (
        <div className="summary-stats">
          <div className="stat-card">
            <div className="stat-label">Total Trades</div>
            <div className="stat-value">{stats.total_trades}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Closed</div>
            <div className="stat-value">{stats.closed_trades}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Win Rate</div>
            <div className="stat-value text-green">{stats.win_rate.toFixed(1)}%</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total P&L</div>
            <div className={`stat-value ${stats.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
              ${stats.total_pnl.toFixed(2)}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg P&L</div>
            <div className={`stat-value ${stats.average_pnl >= 0 ? 'text-green' : 'text-red'}`}>
              ${stats.average_pnl.toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters-section">
        <h3>Filters</h3>
        <div className="filter-row">
          <div className="filter-group">
            <label>Days</label>
            <input
              type="number"
              value={filters.days}
              onChange={(e) => handleFilterChange('days', parseInt(e.target.value))}
              min="1"
              max="365"
            />
          </div>

          <div className="filter-group">
            <label>Strategy</label>
            <select
              value={filters.strategy}
              onChange={(e) => handleFilterChange('strategy', e.target.value)}
            >
              <option value="">All Strategies</option>
              {strategies.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Symbol</label>
            <select
              value={filters.symbol}
              onChange={(e) => handleFilterChange('symbol', e.target.value)}
            >
              <option value="">All Symbols</option>
              {symbols.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Market Context</label>
            <select
              value={filters.market_context}
              onChange={(e) => handleFilterChange('market_context', e.target.value)}
            >
              <option value="">All Contexts</option>
              {contexts.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
            >
              <option value="">All Status</option>
              <option value="OPEN">Open</option>
              <option value="CLOSED">Closed</option>
              <option value="CLOSING">Closing</option>
            </select>
          </div>
        </div>

        <div className="filter-row">
          <div className="filter-group">
            <label>Min P&L</label>
            <input
              type="number"
              value={filters.min_pnl === null ? '' : filters.min_pnl}
              onChange={(e) => handleFilterChange('min_pnl', e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="No limit"
            />
          </div>

          <div className="filter-group">
            <label>Max P&L</label>
            <input
              type="number"
              value={filters.max_pnl === null ? '' : filters.max_pnl}
              onChange={(e) => handleFilterChange('max_pnl', e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="No limit"
            />
          </div>

          <button className="btn-reset" onClick={() => setFilters({
            days: 30,
            strategy: '',
            symbol: '',
            market_context: '',
            min_pnl: null,
            max_pnl: null,
            status: ''
          })}>
            Reset Filters
          </button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="loading">Loading trades...</div>
      ) : sortedTrades.length === 0 ? (
        <div className="no-data">No trades found</div>
      ) : (
        <div className="table-wrapper">
          <table className="trade-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('entry_time')} className="sortable">
                  Entry Time {sortBy === 'entry_time' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('symbol')} className="sortable">
                  Symbol {sortBy === 'symbol' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('side')} className="sortable">
                  Side {sortBy === 'side' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('entry_price')} className="sortable">
                  Entry {sortBy === 'entry_price' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('exit_price')} className="sortable">
                  Exit {sortBy === 'exit_price' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('pnl')} className="sortable">
                  P&L {sortBy === 'pnl' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('strategy')} className="sortable">
                  Strategy {sortBy === 'strategy' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('market_context')} className="sortable">
                  Context {sortBy === 'market_context' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('status')} className="sortable">
                  Status {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedTrades.map(trade => (
                <tr key={trade.id} className={`trade-row ${trade.status.toLowerCase()}`}>
                  <td className="mono">{new Date(trade.entry_time).toLocaleString()}</td>
                  <td className="bold">{trade.symbol}</td>
                  <td>
                    <span className={`badge ${trade.side === 'BUY' ? 'badge-blue' : 'badge-orange'}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td className="mono">${trade.entry_price.toFixed(8)}</td>
                  <td className="mono">{trade.exit_price ? `$${trade.exit_price.toFixed(8)}` : '-'}</td>
                  <td>{renderPnL(trade.pnl, trade.pnl_percent)}</td>
                  <td>{trade.strategy}</td>
                  <td>{renderContextBadge(trade.market_context)}</td>
                  <td>
                    <span className={`badge ${trade.status === 'CLOSED' ? 'badge-success' : 'badge-warning'}`}>
                      {trade.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TradeHistoryTable;
