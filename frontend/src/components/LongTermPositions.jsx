import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, Target, DollarSign, Activity } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './LongTermPositions.css';

const LongTermPositions = () => {
  const { session } = useAuth();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState('symbol');
  const [sortOrder, setSortOrder] = useState('asc');

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadPositions();
    const interval = setInterval(loadPositions, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, [statusFilter]);

  const getAuthToken = () => localStorage.getItem('access_token');

  const loadPositions = async () => {
    try {
      const token = getAuthToken();
      if (!token) return;

      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);

      const response = await fetch(`${API_URL}/api/long-term/positions?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPositions(data.positions || []);
      }
    } catch (error) {
      console.error('Error loading LT positions:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    if (!val) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Apply sorting
  let sortedPositions = [...positions];
  sortedPositions.sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'unrealized_pnl_pct':
        aVal = a.unrealized_pnl_pct || 0;
        bVal = b.unrealized_pnl_pct || 0;
        break;
      case 'total_invested':
        aVal = a.total_invested || 0;
        bVal = b.total_invested || 0;
        break;
      case 'dca_count':
        aVal = a.dca_count || 0;
        bVal = b.dca_count || 0;
        break;
      default:
        aVal = a.symbol;
        bVal = b.symbol;
    }

    if (typeof aVal === 'string') {
      return sortOrder === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }
    
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  const handleResetFilters = () => {
    setStatusFilter('');
    setSortBy('symbol');
    setSortOrder('asc');
  };

  if (loading) {
    return (
      <div className="lt-positions-container">
        <div className="lt-positions-header">
          <h3>Long-Term Positions</h3>
        </div>
        <div className="lt-loading">Loading long-term positions...</div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="lt-positions-container">
        <div className="lt-positions-header">
          <h3>Long-Term Positions</h3>
          <span className="position-count">(0 positions)</span>
        </div>
        <div className="lt-empty">
          <TrendingUp size={48} style={{color: '#6b7280'}} />
          <p>No long-term positions</p>
          <span>Enable long-term strategy in Settings to start accumulating</span>
        </div>
      </div>
    );
  }

  return (
    <div className="lt-positions-container">
      <div className="lt-positions-header">
        <div className="header-left">
          <h3>Long-Term Positions</h3>
          <span className="position-count">({positions.length} positions)</span>
        </div>
        <div className="header-right">
          <TrendingUp size={20} style={{color: '#10b981'}} />
        </div>
      </div>

      {/* Filters */}
      <div className="lt-controls">
        <div className="filter-group">
          <div className="filter-item">
            <label>Status</label>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Status</option>
              <option value="ACCUMULATING">Accumulating</option>
              <option value="HOLDING">Holding</option>
              <option value="PARTIAL_EXIT">Partial Exit</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Sort By</label>
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
            >
              <option value="symbol">Symbol</option>
              <option value="unrealized_pnl_pct">PnL %</option>
              <option value="total_invested">Invested</option>
              <option value="dca_count">DCA Count</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Order</label>
            <select 
              value={sortOrder} 
              onChange={(e) => setSortOrder(e.target.value)}
              className="filter-select"
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>

          <button 
            onClick={handleResetFilters}
            className="reset-btn"
            title="Reset filters"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="table-responsive">
        <table className="lt-positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Status</th>
              <th>Quantity</th>
              <th>Avg Entry</th>
              <th>Invested</th>
              <th>Unrealized PnL</th>
              <th>DCA Count</th>
              <th>Last DCA</th>
              <th>TP Levels</th>
            </tr>
          </thead>
          <tbody>
            {sortedPositions.map((pos) => (
              <tr key={pos.id}>
                <td className="symbol-cell">
                  <span className="symbol-name">{pos.symbol}</span>
                </td>
                <td>
                  <span className={`lt-status-badge ${pos.status.toLowerCase()}`}>
                    {pos.status}
                  </span>
                </td>
                <td>
                  <span className="quantity-value">
                    {parseFloat(pos.total_quantity).toFixed(6)}
                  </span>
                </td>
                <td>
                  <span className="price-value">
                    {formatCurrency(pos.avg_entry_price)}
                  </span>
                </td>
                <td>
                  <span className="invested-value">
                    {formatCurrency(pos.total_invested)}
                  </span>
                </td>
                <td>
                  <div className={`pnl-cell ${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                    <span className="pnl-amount">
                      {formatCurrency(pos.unrealized_pnl)}
                    </span>
                    <span className="pnl-percent">
                      ({pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct?.toFixed(2)}%)
                    </span>
                  </div>
                </td>
                <td>
                  <div className="dca-count">
                    <Calendar size={14} />
                    <span>{pos.dca_count}</span>
                  </div>
                </td>
                <td>
                  <span className="date-value">
                    {formatDate(pos.last_dca_at)}
                  </span>
                </td>
                <td>
                  <div className="tp-levels">
                    <div className="tp-item">
                      <Target size={12} />
                      <span className={pos.tp1_hit ? 'tp-hit' : 'tp-pending'}>
                        TP1 {pos.tp1_hit ? '✓' : ''}
                      </span>
                    </div>
                    <div className="tp-item">
                      <Target size={12} />
                      <span className={pos.tp2_hit ? 'tp-hit' : 'tp-pending'}>
                        TP2 {pos.tp2_hit ? '✓' : ''}
                      </span>
                    </div>
                    <div className="tp-item">
                      <Target size={12} />
                      <span className={pos.tp3_hit ? 'tp-hit' : 'tp-pending'}>
                        TP3 {pos.tp3_hit ? '✓' : ''}
                      </span>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LongTermPositions;
