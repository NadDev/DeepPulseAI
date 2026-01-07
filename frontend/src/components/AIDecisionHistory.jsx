import { useState, useEffect } from 'react';
import { Filter, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import './AIDecisionHistory.css';

function AIDecisionHistory() {
  const [decisions, setDecisions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, executed, blocked
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [filter, selectedSymbol]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const filters = {
        executed: filter === 'executed' ? true : filter === 'blocked' ? false : undefined,
        symbol: selectedSymbol || undefined
      };

      const [decisionsData, statsData] = await Promise.all([
        aiAPI.getDecisionHistory(filters),
        aiAPI.getDecisionStats()
      ]);

      setDecisions(decisionsData.decisions || []);
      setStats(statsData);
    } catch (err) {
      setError(err.message || 'Failed to load decision history');
      console.error('Error loading decisions:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (executed, blocked) => {
    if (blocked) return '🚫';
    if (executed) return '✅';
    return '⏸';
  };

  const getStatusText = (executed, blocked) => {
    if (blocked) return 'Blocked';
    if (executed) return 'Executed';
    return 'Skipped';
  };

  const formatPnL = (pnl) => {
    if (pnl === null || pnl === undefined) return 'N/A';
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}${pnl.toFixed(2)}%`;
  };

  const symbolsSet = new Set(decisions.map(d => d.symbol));

  if (loading) {
    return (
      <div className="ai-decision-history">
        <div className="loading-state">
          <p>Loading decision history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-decision-history">
      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <p className="stat-label">Total Decisions</p>
            <p className="stat-value">{stats.total_decisions || 0}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Execution Rate</p>
            <p className="stat-value">{((stats.execution_rate || 0) * 100).toFixed(1)}%</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Win Rate</p>
            <p className="stat-value">{((stats.win_rate || 0) * 100).toFixed(1)}%</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Avg P&L</p>
            <p className={`stat-value ${(stats.average_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              {formatPnL(stats.average_pnl)}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters-section">
        <div className="filter-group">
          <Filter size={18} />
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Decisions</option>
            <option value="executed">Executed Only</option>
            <option value="blocked">Blocked Only</option>
          </select>
        </div>

        {symbolsSet.size > 0 && (
          <select
            value={selectedSymbol}
            onChange={e => setSelectedSymbol(e.target.value)}
            className="filter-select"
          >
            <option value="">All Symbols</option>
            {Array.from(symbolsSet).sort().map(symbol => (
              <option key={symbol} value={symbol}>
                {symbol}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <p>{error}</p>
        </div>
      )}

      {/* Decisions Table */}
      {decisions.length > 0 ? (
        <div className="decisions-table-wrapper">
          <table className="decisions-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Action</th>
                <th>Confidence</th>
                <th>Entry Price</th>
                <th>Target</th>
                <th>Status</th>
                <th>P&L</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((decision, idx) => (
                <tr key={idx} className={`row-${getStatusText(decision.executed, decision.blocked).toLowerCase()}`}>
                  <td className="symbol-cell">
                    <strong>{decision.symbol}</strong>
                  </td>
                  <td>
                    <span className={`action-badge ${decision.action?.toLowerCase()}`}>
                      {decision.action?.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div className="confidence-cell">
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill"
                          style={{ width: `${decision.confidence}%` }}
                        ></div>
                      </div>
                      <span>{decision.confidence}%</span>
                    </div>
                  </td>
                  <td className="price-cell">
                    ${decision.entry_price?.toFixed(2) || 'N/A'}
                  </td>
                  <td className="price-cell">
                    ${decision.target_price?.toFixed(2) || 'N/A'}
                  </td>
                  <td className="status-cell">
                    <span className="status-badge">
                      {getStatusIcon(decision.executed, decision.blocked)}
                      {getStatusText(decision.executed, decision.blocked)}
                    </span>
                  </td>
                  <td className={`pnl-cell ${(decision.result_pnl_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                    {decision.result_pnl_percent ? (
                      <>
                        {(decision.result_pnl_percent) >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        {formatPnL(decision.result_pnl_percent)}
                      </>
                    ) : (
                      'Pending'
                    )}
                  </td>
                  <td className="time-cell">
                    {new Date(decision.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="no-data">
          <AlertCircle size={40} />
          <p>No decisions found matching your filters</p>
        </div>
      )}
    </div>
  );
}

export default AIDecisionHistory;
