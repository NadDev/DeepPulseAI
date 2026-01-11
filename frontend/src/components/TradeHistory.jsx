import React, { useState, useEffect } from 'react';
import './TradeHistory.css';
import { apiRequest } from '../services/api';

const TradeHistory = ({ userId, refreshTrigger }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTrades, setTotalTrades] = useState(0);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('CLOSED');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [minPnL, setMinPnL] = useState('');
  const [maxPnL, setMaxPnL] = useState('');
  
  // Sorting
  const [sortBy, setSortBy] = useState('entry_time');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Fetch trade history
  const fetchTradeHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
        status_filter: statusFilter
      });
      
      if (symbolFilter) params.append('symbol_filter', symbolFilter);
      if (minPnL) params.append('min_pnl', minPnL);
      if (maxPnL) params.append('max_pnl', maxPnL);
      
      const response = await apiRequest(`/portfolio/trade-history?${params.toString()}`, {
        method: 'GET'
      });
      
      if (response.trades) {
        setTrades(response.trades);
        setTotalPages(response.pagination.total_pages);
        setTotalTrades(response.pagination.total_trades);
      }
    } catch (err) {
      setError(err.message || 'Failed to load trade history');
      console.error('Trade history error:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch when filters or page changes
  useEffect(() => {
    fetchTradeHistory();
  }, [page, pageSize, statusFilter, symbolFilter, minPnL, maxPnL, sortBy, sortOrder, refreshTrigger]);
  
  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };
  
  const formatDuration = (minutes) => {
    if (!minutes || minutes === null) return '-';
    const totalSeconds = Math.round(minutes * 60);
    const hours = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
    } else if (mins > 0) {
      return `${mins}m ${String(secs).padStart(2, '0')}s`;
    }
    return `${secs}s`;
  };
  
  const handleReset = () => {
    setPage(1);
    setSymbolFilter('');
    setMinPnL('');
    setMaxPnL('');
    setStatusFilter('CLOSED');
    setSortBy('entry_time');
    setSortOrder('desc');
  };
  
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };
  
  if (loading && trades.length === 0) {
    return <div className="history-loading">Loading trade history...</div>;
  }
  
  return (
    <div className="trade-history-container">
      <div className="history-header">
        <h3>Trade History</h3>
        <div className="total-info">
          {totalTrades} total trades
        </div>
      </div>
      
      {/* FILTERS SECTION - Compact Design */}
      <div className="filters-section-compact">
        <div className="filters-toolbar">
          <div className="filters-compact-group">
            <select 
              className="filter-select-compact"
              value={statusFilter} 
              onChange={(e) => {setStatusFilter(e.target.value); setPage(1);}}
              title="Filter by status"
            >
              <option value="CLOSED">Closed</option>
              <option value="OPEN">Open</option>
              <option value="ALL">All</option>
            </select>
            
            <input 
              type="text" 
              className="filter-input-compact"
              placeholder="Symbol"
              value={symbolFilter}
              onChange={(e) => {setSymbolFilter(e.target.value.toUpperCase()); setPage(1);}}
              maxLength="10"
            />
            
            <input 
              type="number" 
              className="filter-input-compact"
              placeholder="Min $"
              value={minPnL}
              onChange={(e) => {setMinPnL(e.target.value); setPage(1);}}
            />
            
            <input 
              type="number" 
              className="filter-input-compact"
              placeholder="Max $"
              value={maxPnL}
              onChange={(e) => {setMaxPnL(e.target.value); setPage(1);}}
            />
            
            <select 
              className="filter-select-compact"
              value={sortBy} 
              onChange={(e) => {setSortBy(e.target.value); setPage(1);}}
            >
              <option value="entry_time">Date</option>
              <option value="symbol">Symbol</option>
              <option value="pnl">PnL</option>
            </select>
            
            <select 
              className="filter-select-compact"
              value={sortOrder} 
              onChange={(e) => setSortOrder(e.target.value)}
            >
              <option value="desc">↓</option>
              <option value="asc">↑</option>
            </select>
            
            <select 
              className="filter-select-compact"
              value={pageSize} 
              onChange={(e) => {setPageSize(parseInt(e.target.value)); setPage(1);}}
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
            
            <button className="btn-reset-compact" onClick={handleReset} title="Reset">
              ✕
            </button>
          </div>
        </div>
      </div>
      
      {/* TABLE SECTION */}
      <div className="table-responsive">
        {trades.length === 0 ? (
          <div className="history-empty">
            <p>No trades found matching your filters</p>
          </div>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Qty</th>
                <th>Duration</th>
                <th>Status</th>
                <th>PnL</th>
                <th>PnL %</th>
                <th>Strategy</th>
                <th>Bot</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className={`status-${trade.status.toLowerCase()}`}>
                  <td className="date-cell">{formatDate(trade.entry_time)}</td>
                  <td className="symbol-cell">
                    <strong>{trade.symbol}</strong>
                  </td>
                  <td>
                    <span className={`badge ${trade.side.toLowerCase()}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td>{formatCurrency(trade.entry_price)}</td>
                  <td>{trade.exit_price ? formatCurrency(trade.exit_price) : '-'}</td>
                  <td className="qty-cell">{parseFloat(trade.quantity).toFixed(4)}</td>
                  <td className="duration-cell">{formatDuration(trade.duration_minutes)}</td>
                  <td>
                    <span className={`status-badge ${trade.status.toLowerCase()}`}>
                      {trade.status}
                    </span>
                  </td>
                  <td>
                    <span className={trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                      {formatCurrency(trade.pnl)}
                    </span>
                  </td>
                  <td>
                    <span className={trade.pnl_percent >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                      {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent.toFixed(2)}%
                    </span>
                  </td>
                  <td className="strategy-cell">{trade.strategy}</td>
                  <td className="bot-cell">{trade.bot_name || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      
      {/* PAGINATION SECTION */}
      {totalPages > 1 && (
        <div className="pagination-section">
          <div className="pagination-info">
            {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalTrades)} of {totalTrades}
          </div>
          
          <div className="pagination-controls">
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(1)}
              disabled={page === 1}
              title="First"
            >
              ⟨⟨
            </button>
            
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(page - 1)}
              disabled={page === 1}
              title="Previous"
            >
              ⟨
            </button>
            
            <div className="page-numbers">
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }
                
                return (
                  <button
                    key={pageNum}
                    className={`page-btn ${page === pageNum ? 'active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(page + 1)}
              disabled={page === totalPages}
              title="Next"
            >
              ⟩
            </button>
            
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(totalPages)}
              disabled={page === totalPages}
              title="Last"
            >
              ⟩⟩
            </button>
            
            <span className="page-counter">
              {page}/{totalPages}
            </span>
          </div>
        </div>
            
            <div className="page-numbers">
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }
                
                return (
                  <button
                    key={pageNum}
                    className={`page-btn ${page === pageNum ? 'active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(page + 1)}
              disabled={page === totalPages}
              title="Next"
            >
              ⟩
            </button>
            
            <button 
              className="btn-page-nav"
              onClick={() => handlePageChange(totalPages)}
              disabled={page === totalPages}
              title="Last"
            >
              ⟩⟩
            </button>
            
            <span className="page-counter">
              {page}/{totalPages}
            </span>
          </div>
        </div>
      )}
      
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
};

export default TradeHistory;
