import React, { useState } from 'react';
import { TrendingUp, TrendingDown, XCircle } from 'lucide-react';
import './ActivePositions.css';

const ActivePositions = ({ positions, onClosePosition }) => {
  const [sortBy, setSortBy] = useState('symbol');
  const [sortOrder, setSortOrder] = useState('asc');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [minPnL, setMinPnL] = useState('');
  const [maxPnL, setMaxPnL] = useState('');

  if (!positions || positions.length === 0) {
    return (
      <div className="positions-empty">
        <p>No active positions</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };

  // Apply filters
  let filtered = positions.filter(pos => {
    if (symbolFilter && !pos.symbol.includes(symbolFilter.toUpperCase())) {
      return false;
    }
    if (minPnL !== '' && pos.unrealized_pnl < parseFloat(minPnL)) {
      return false;
    }
    if (maxPnL !== '' && pos.unrealized_pnl > parseFloat(maxPnL)) {
      return false;
    }
    return true;
  });

  // Apply sorting
  filtered.sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'symbol':
        aVal = a.symbol;
        bVal = b.symbol;
        break;
      case 'entry_price':
        aVal = a.entry_price;
        bVal = b.entry_price;
        break;
      case 'current_price':
        aVal = a.current_price;
        bVal = b.current_price;
        break;
      case 'unrealized_pnl':
        aVal = a.unrealized_pnl;
        bVal = b.unrealized_pnl;
        break;
      case 'value':
        aVal = a.value;
        bVal = b.value;
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
    setSymbolFilter('');
    setMinPnL('');
    setMaxPnL('');
    setSortBy('symbol');
    setSortOrder('asc');
  };

  return (
    <div className="positions-container">
      <div className="positions-header">
        <h3>Active Positions</h3>
        <span className="position-count">({filtered.length} positions)</span>
      </div>

      {/* Filter & Sort Controls */}
      <div className="positions-controls">
        <div className="filter-group">
          <div className="filter-item">
            <label>Symbol</label>
            <input
              type="text"
              placeholder="Filter by symbol..."
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Min PnL ($)</label>
            <input
              type="number"
              placeholder="Min"
              value={minPnL}
              onChange={(e) => setMinPnL(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Max PnL ($)</label>
            <input
              type="number"
              placeholder="Max"
              value={maxPnL}
              onChange={(e) => setMaxPnL(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Sort By</label>
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
            >
              <option value="symbol">Symbol</option>
              <option value="entry_price">Entry Price</option>
              <option value="current_price">Current Price</option>
              <option value="unrealized_pnl">PnL</option>
              <option value="value">Position Value</option>
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
            title="Reset all filters"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="table-responsive">
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Size</th>
              <th>Entry Price</th>
              <th>Current Price</th>
              <th>Value</th>
              <th>Unrealized PnL</th>
              <th>Strategy</th>
              <th>Bot Name</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((pos) => (
              <tr key={pos.id}>
                <td className="symbol-cell">
                  <span className="symbol-name">{pos.symbol}</span>
                </td>
                <td>
                  <span className={`badge ${pos.side.toLowerCase()}`}>
                    {pos.side}
                  </span>
                </td>
                <td>{parseFloat(pos.quantity).toFixed(8)}</td>
                <td>{formatCurrency(pos.entry_price)}</td>
                <td className={pos.current_price > pos.entry_price ? 'price-up' : 'price-down'}>
                  {formatCurrency(pos.current_price)}
                </td>
                <td>{formatCurrency(pos.value)}</td>
                <td>
                  <div className={`pnl-cell ${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                    {pos.unrealized_pnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    <span>{formatCurrency(pos.unrealized_pnl)}</span>
                    <span className="pnl-percent">({pos.unrealized_pnl_percent.toFixed(2)}%)</span>
                  </div>
                </td>
                <td>{pos.strategy}</td>
                <td>{pos.bot_name || '-'}</td>
                <td>
                  <button 
                    className="close-btn"
                    onClick={() => onClosePosition(pos)}
                    title="Close Position"
                  >
                    <XCircle size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ActivePositions;