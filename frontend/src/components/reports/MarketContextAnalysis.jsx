import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MarketContextAnalysis.css';

/**
 * MarketContextAnalysis Component
 * Displays market context timeline and strategy performance per context
 */
const MarketContextAnalysis = ({ userId }) => {
  const [trades, setTrades] = useState([]);
  const [contextStats, setContextStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchContextData();
  }, [days]);

  const fetchContextData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(
        `/api/reports/trades?days=${days}&limit=1000`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setTrades(response.data.trades || []);
      setContextStats(response.data.context_breakdown || {});
    } catch (err) {
      setError(err.message || 'Failed to fetch context data');
      console.error('Error fetching context data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getContextColor = (context) => {
    const colors = {
      'STRONG_BULLISH': '#10b981',
      'WEAK_BULLISH': '#22c55e',
      'NEUTRAL': '#94a3b8',
      'WEAK_BEARISH': '#f87171',
      'STRONG_BEARISH': '#ef4444'
    };
    return colors[context] || '#94a3b8';
  };

  const contextOrder = ['STRONG_BULLISH', 'WEAK_BULLISH', 'NEUTRAL', 'WEAK_BEARISH', 'STRONG_BEARISH'];
  const sortedContexts = Object.keys(contextStats).sort((a, b) => {
    const aIdx = contextOrder.indexOf(a);
    const bIdx = contextOrder.indexOf(b);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });

  // Calculate timeline data
  const timelineData = [];
  let lastContext = null;
  let contextStartDate = null;

  const sortedTrades = [...trades].sort((a, b) => 
    new Date(a.entry_time) - new Date(b.entry_time)
  );

  sortedTrades.forEach((trade, idx) => {
    const context = trade.market_context || 'UNKNOWN';
    if (context !== lastContext) {
      if (lastContext && contextStartDate) {
        timelineData.push({
          context: lastContext,
          startDate: contextStartDate,
          endDate: trade.entry_time,
          trades: sortedTrades.slice(
            Math.max(0, idx - 10),
            idx
          ).filter(t => t.market_context === lastContext).length
        });
      }
      lastContext = context;
      contextStartDate = trade.entry_time;
    }
  });

  if (lastContext && contextStartDate) {
    timelineData.push({
      context: lastContext,
      startDate: contextStartDate,
      endDate: new Date().toISOString(),
      trades: sortedTrades.filter(t => t.market_context === lastContext).length
    });
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  return (
    <div className="market-context-container">
      <div className="context-header">
        <h2>🎯 Market Context Analysis</h2>
        <div className="header-controls">
          <label>Period</label>
          <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={60}>Last 60 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading context data...</div>
      ) : (
        <>
          {/* Context Distribution */}
          <div className="context-distribution-section">
            <h3>Context Distribution</h3>
            <div className="distribution-grid">
              {sortedContexts.map(context => {
                const stats = contextStats[context];
                const totalTrades = Object.values(contextStats).reduce((sum, s) => sum + (s.total_trades || 0), 0);
                const percentage = totalTrades > 0 ? (stats.total_trades / totalTrades) * 100 : 0;

                return (
                  <div key={context} className="distribution-card">
                    <div className="card-header">
                      <div className="context-indicator" style={{ backgroundColor: getContextColor(context) }}></div>
                      <h4>{context}</h4>
                    </div>
                    <div className="card-content">
                      <div className="stat-row">
                        <span>Trades</span>
                        <strong>{stats.total_trades}</strong>
                      </div>
                      <div className="stat-row">
                        <span>% of Total</span>
                        <strong>{percentage.toFixed(1)}%</strong>
                      </div>
                      <div className="progress-bar">
                        <div 
                          className="progress-fill" 
                          style={{ 
                            width: `${percentage}%`,
                            backgroundColor: getContextColor(context)
                          }}
                        ></div>
                      </div>
                      <div className="stat-row">
                        <span>Win Rate</span>
                        <strong className={stats.win_rate >= 50 ? 'text-green' : 'text-red'}>
                          {stats.win_rate ? stats.win_rate.toFixed(1) : 0}%
                        </strong>
                      </div>
                      <div className="stat-row">
                        <span>Total P&L</span>
                        <strong className={stats.total_pnl >= 0 ? 'text-green' : 'text-red'}>
                          ${stats.total_pnl ? stats.total_pnl.toFixed(2) : '0.00'}
                        </strong>
                      </div>
                      <div className="stat-row">
                        <span>Avg P&L</span>
                        <strong className={stats.avg_pnl >= 0 ? 'text-green' : 'text-red'}>
                          ${stats.avg_pnl ? stats.avg_pnl.toFixed(2) : '0.00'}
                        </strong>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Performance Comparison */}
          <div className="context-comparison-section">
            <h3>Context Performance Comparison</h3>
            <div className="comparison-table-wrapper">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Market Context</th>
                    <th>Trades</th>
                    <th>Wins</th>
                    <th>Losses</th>
                    <th>Win Rate</th>
                    <th>Total P&L</th>
                    <th>Avg P&L</th>
                    <th>Best Trade</th>
                    <th>Worst Trade</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedContexts.map(context => {
                    const stats = contextStats[context];
                    const wins = stats.total_trades > 0 
                      ? Math.round((stats.win_rate / 100) * stats.total_trades)
                      : 0;
                    const losses = stats.total_trades - wins;

                    return (
                      <tr key={context} className="comparison-row">
                        <td className="context-name">
                          <div className="context-badge">
                            <div 
                              className="badge-dot" 
                              style={{ backgroundColor: getContextColor(context) }}
                            ></div>
                            {context}
                          </div>
                        </td>
                        <td className="mono">{stats.total_trades}</td>
                        <td className="mono text-green">{wins}</td>
                        <td className="mono text-red">{losses}</td>
                        <td className={`mono ${stats.win_rate >= 50 ? 'text-green' : 'text-red'}`}>
                          {stats.win_rate ? stats.win_rate.toFixed(1) : 0}%
                        </td>
                        <td className={`mono ${stats.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                          ${stats.total_pnl ? stats.total_pnl.toFixed(2) : '0.00'}
                        </td>
                        <td className={`mono ${stats.avg_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                          ${stats.avg_pnl ? stats.avg_pnl.toFixed(2) : '0.00'}
                        </td>
                        <td className="mono text-green">${stats.best_pnl ? stats.best_pnl.toFixed(2) : '-'}</td>
                        <td className="mono text-red">${stats.worst_pnl ? stats.worst_pnl.toFixed(2) : '-'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Timeline */}
          <div className="timeline-section">
            <h3>Context Timeline</h3>
            <div className="timeline">
              {timelineData.map((period, idx) => {
                const duration = Math.abs(
                  new Date(period.endDate) - new Date(period.startDate)
                ) / (1000 * 60 * 60 * 24);

                return (
                  <div key={idx} className="timeline-entry">
                    <div 
                      className="timeline-marker" 
                      style={{ backgroundColor: getContextColor(period.context) }}
                    ></div>
                    <div className="timeline-content">
                      <h4>{period.context}</h4>
                      <div className="timeline-details">
                        <span>{new Date(period.startDate).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>{duration.toFixed(1)} days</span>
                        <span>•</span>
                        <span>{period.trades} trades</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Best and Worst Contexts */}
          <div className="context-insights">
            <div className="insight-card best">
              <h4>🚀 Best Performing Context</h4>
              {sortedContexts.length > 0 && (() => {
                const best = sortedContexts.reduce((prev, current) => {
                  return (contextStats[current].win_rate > contextStats[prev].win_rate) ? current : prev;
                });
                return (
                  <div className="insight-content">
                    <p className="context-name">{best}</p>
                    <p className="text-green">{contextStats[best].win_rate.toFixed(1)}% win rate</p>
                    <p className="text-green">${contextStats[best].total_pnl.toFixed(2)} total P&L</p>
                  </div>
                );
              })()}
            </div>

            <div className="insight-card worst">
              <h4>⚠️ Challenging Context</h4>
              {sortedContexts.length > 0 && (() => {
                const worst = sortedContexts.reduce((prev, current) => {
                  return (contextStats[current].win_rate < contextStats[prev].win_rate) ? current : prev;
                });
                return (
                  <div className="insight-content">
                    <p className="context-name">{worst}</p>
                    <p className="text-red">{contextStats[worst].win_rate.toFixed(1)}% win rate</p>
                    <p className="text-red">${contextStats[worst].total_pnl.toFixed(2)} total P&L</p>
                  </div>
                );
              })()}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default MarketContextAnalysis;
