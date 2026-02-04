import React, { useState, useEffect } from 'react';
import {
  Download,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import '../styles/RecommendationHistory.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const RecommendationHistory = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize] = useState(50);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');
  
  // Stats
  const [stats, setStats] = useState({
    total: 0,
    accepted: 0,
    rejected: 0,
    acceptanceRate: 0,
    avgScore: 0
  });

  // Get auth headers from localStorage JWT token
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('Not authenticated');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  };

  // Load history
  const loadHistory = async (page = 0) => {
    try {
      setLoading(true);
      setError(null);
      const headers = getAuthHeaders();
      
      const offset = page * pageSize;
      const response = await fetch(
        `${API_URL}/api/watchlist/recommendations/history?limit=${pageSize}&offset=${offset}&status=${statusFilter}`,
        { headers }
      );

      if (!response.ok) {
        throw new Error(`Failed to load history: ${response.status}`);
      }

      const data = await response.json();
      setRecommendations(data.recommendations || []);
      
      // Update stats
      if (data.stats) {
        setStats(data.stats);
      }
      
      setCurrentPage(page);
    } catch (err) {
      setError(err.message);
      console.error('Error loading recommendation history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory(0);
  }, [statusFilter]);

  const filteredRecs = recommendations.filter(rec => {
    if (searchSymbol && !rec.symbol.toUpperCase().includes(searchSymbol.toUpperCase())) {
      return false;
    }
    if (dateStart && new Date(rec.created_at) < new Date(dateStart)) {
      return false;
    }
    if (dateEnd && new Date(rec.created_at) > new Date(dateEnd)) {
      return false;
    }
    return true;
  });

  const downloadCSV = () => {
    const headers = ['Date', 'Symbol', 'Score', 'Action', 'Decision', 'Reasoning'];
    const rows = recommendations.map(rec => [
      new Date(rec.created_at).toLocaleDateString(),
      rec.symbol,
      rec.score.toFixed(1),
      rec.action,
      rec.accepted ? 'Accepted' : rec.accepted === false ? 'Rejected' : 'Pending',
      rec.reasoning || ''
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `recommendation_history_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading && recommendations.length === 0) {
    return (
      <div className="history-container">
        <div className="loading-spinner">
          <Loader2 className="spinner-icon" />
          <p>Loading history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h1>Recommendation History</h1>
        <button onClick={downloadCSV} className="download-btn">
          <Download size={16} />
          Export CSV
        </button>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Total Recommendations</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Accepted</span>
          <span className="stat-value accepted">{stats.accepted}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Rejected</span>
          <span className="stat-value rejected">{stats.rejected}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Acceptance Rate</span>
          <span className="stat-value">{stats.acceptanceRate?.toFixed(1) || 0}%</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Average Score</span>
          <span className="stat-value">{stats.avgScore?.toFixed(1) || 0}/100</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <div className="filter-group">
          <label>
            <Filter size={16} />
            Status
          </label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="filter-group">
          <label>
            <Search size={16} />
            Symbol
          </label>
          <input
            type="text"
            placeholder="BTCUSDT, ETHUSDT..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Start Date</label>
          <input
            type="date"
            value={dateStart}
            onChange={(e) => setDateStart(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>End Date</label>
          <input
            type="date"
            value={dateEnd}
            onChange={(e) => setDateEnd(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="error-message">
          <p>⚠️ {error}</p>
        </div>
      )}

      {/* Table */}
      <div className="table-wrapper">
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Symbol</th>
              <th>Score</th>
              <th>Action</th>
              <th>Decision</th>
              <th>Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {filteredRecs.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">
                  No recommendations found
                </td>
              </tr>
            ) : (
              filteredRecs.map((rec) => (
                <tr key={rec.id} className={`status-${rec.accepted ? 'accepted' : rec.accepted === false ? 'rejected' : 'pending'}`}>
                  <td>
                    <span className="date">
                      {new Date(rec.created_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td>
                    <span className="symbol">{rec.symbol}</span>
                  </td>
                  <td>
                    <div className="score-mini">
                      <div className="score-bar">
                        <div className="fill" style={{ width: `${rec.score}%` }} />
                      </div>
                      <span>{rec.score.toFixed(1)}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`action ${rec.action?.toLowerCase()}`}>
                      {rec.action === 'ADD' ? '⬆️ Add' : '⬇️ Remove'}
                    </span>
                  </td>
                  <td>
                    <span className={`decision ${rec.accepted ? 'accepted' : rec.accepted === false ? 'rejected' : 'pending'}`}>
                      {rec.accepted ? '✓ Accepted' : rec.accepted === false ? '✗ Rejected' : '• Pending'}
                    </span>
                  </td>
                  <td>
                    <span className="reasoning-text" title={rec.reasoning}>
                      {rec.reasoning ? rec.reasoning.substring(0, 40) + '...' : '—'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="pagination">
        <button
          onClick={() => loadHistory(currentPage - 1)}
          disabled={currentPage === 0}
          className="pagination-btn"
        >
          <ChevronLeft size={16} />
          Previous
        </button>

        <span className="pagination-info">
          Page {currentPage + 1} ({filteredRecs.length} items)
        </span>

        <button
          onClick={() => loadHistory(currentPage + 1)}
          disabled={filteredRecs.length < pageSize}
          className="pagination-btn"
        >
          Next
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
};

export default RecommendationHistory;
