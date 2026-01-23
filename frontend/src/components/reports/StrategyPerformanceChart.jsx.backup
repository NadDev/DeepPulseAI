import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './StrategyPerformanceChart.css';

/**
 * StrategyPerformanceChart Component
 * Displays strategy performance comparison with market context breakdown
 */
const StrategyPerformanceChart = ({ userId }) => {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [view, setView] = useState('comparison'); // 'comparison' or 'detail'

  useEffect(() => {
    fetchStrategies();
  }, [days]);

  const fetchStrategies = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(
        `/api/reports/strategies?days=${days}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setStrategies(response.data.strategies || []);
      if (!selectedStrategy && response.data.strategies.length > 0) {
        setSelectedStrategy(response.data.strategies[0]);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch strategies');
      console.error('Error fetching strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStrategyDetail = async (strategyName) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(
        `/api/reports/strategies/${strategyName}?days=${days}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setSelectedStrategy(response.data);
      setView('detail');
    } catch (err) {
      setError(err.message || 'Failed to fetch strategy details');
      console.error('Error fetching strategy details:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderContextCell = (contextData) => {
    if (!contextData) return <td className="no-data">-</td>;
    
    const winRateClass = contextData.win_rate >= 50 ? 'text-green' : 'text-red';
    
    return (
      <div className="context-cell">
        <div className="context-trades">{contextData.trades} trades</div>
        <div className={`context-winrate ${winRateClass}`}>
          {contextData.win_rate.toFixed(1)}% WR
        </div>
        <div className={`context-pnl ${contextData.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
          ${contextData.total_pnl.toFixed(2)}
        </div>
      </div>
    );
  };

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  if (view === 'detail' && selectedStrategy && selectedStrategy.context_performance) {
    return (
      <div className="strategy-detail-container">
        <div className="detail-header">
          <button className="btn-back" onClick={() => setView('comparison')}>← Back</button>
          <h2>{selectedStrategy.strategy}</h2>
        </div>

        <div className="detail-stats">
          <div className="stat-card">
            <div className="stat-label">Total Trades</div>
            <div className="stat-value">{selectedStrategy.total_trades}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Win Rate</div>
            <div className={`stat-value ${selectedStrategy.win_rate >= 50 ? 'text-green' : 'text-red'}`}>
              {selectedStrategy.win_rate.toFixed(1)}%
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total P&L</div>
            <div className={`stat-value ${selectedStrategy.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
              ${selectedStrategy.total_pnl.toFixed(2)}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Profit Factor</div>
            <div className="stat-value">{selectedStrategy.profit_factor.toFixed(2)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg P&L</div>
            <div className={`stat-value ${selectedStrategy.avg_pnl >= 0 ? 'text-green' : 'text-red'}`}>
              ${selectedStrategy.avg_pnl.toFixed(2)}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Best Trade</div>
            <div className="stat-value text-green">${selectedStrategy.best_trade.toFixed(2)}</div>
          </div>
        </div>

        <div className="context-performance">
          <h3>Performance by Market Context</h3>
          <div className="context-grid">
            {Object.entries(selectedStrategy.context_performance).map(([context, data]) => (
              <div key={context} className="context-card">
                <div className="context-name">{context}</div>
                <div className="context-info">
                  <div className="info-row">
                    <span className="label">Trades:</span>
                    <span className="value">{data.trades}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Win Rate:</span>
                    <span className={`value ${data.win_rate >= 50 ? 'text-green' : 'text-red'}`}>
                      {data.win_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">Total P&L:</span>
                    <span className={`value ${data.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                      ${data.total_pnl.toFixed(2)}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">Avg P&L:</span>
                    <span className={`value ${data.avg_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                      ${data.avg_pnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {selectedStrategy.recent_trades && (
          <div className="recent-trades">
            <h3>Recent Trades</h3>
            <div className="trades-list">
              {selectedStrategy.recent_trades.map(trade => (
                <div key={trade.id} className="trade-item">
                  <div className="trade-symbol">{trade.symbol}</div>
                  <div className="trade-price">
                    {trade.entry_price.toFixed(8)} → {trade.exit_price ? trade.exit_price.toFixed(8) : '-'}
                  </div>
                  <div className={`trade-pnl ${trade.pnl >= 0 ? 'text-green' : 'text-red'}`}>
                    {trade.pnl ? `$${trade.pnl.toFixed(2)}` : '-'} ({trade.pnl_percent ? `${trade.pnl_percent.toFixed(2)}%` : '-'})
                  </div>
                  <div className="trade-context">{trade.market_context || 'N/A'}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="strategy-performance-container">
      <div className="performance-header">
        <h2>📈 Strategy Performance</h2>
        <div className="header-controls">
          <label>Last</label>
          <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
            <option value={7}>7 Days</option>
            <option value={30}>30 Days</option>
            <option value={60}>60 Days</option>
            <option value={90}>90 Days</option>
            <option value={180}>6 Months</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading strategies...</div>
      ) : strategies.length === 0 ? (
        <div className="no-data">No strategy data available</div>
      ) : (
        <>
          {/* Comparison Table */}
          <div className="strategy-comparison">
            <div className="table-wrapper">
              <table className="strategy-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Trades</th>
                    <th>Wins</th>
                    <th>Win Rate</th>
                    <th>Total P&L</th>
                    <th>Avg P&L</th>
                    <th>Best Trade</th>
                    <th>Profit Factor</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map(strategy => (
                    <tr key={strategy.strategy} className="strategy-row">
                      <td className="strategy-name bold">{strategy.strategy}</td>
                      <td className="mono">{strategy.total_trades}</td>
                      <td className="mono">{strategy.winning_trades}</td>
                      <td className={`mono ${strategy.win_rate >= 50 ? 'text-green' : 'text-red'}`}>
                        {strategy.win_rate.toFixed(1)}%
                      </td>
                      <td className={`mono ${strategy.total_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        ${strategy.total_pnl.toFixed(2)}
                      </td>
                      <td className={`mono ${strategy.avg_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        ${strategy.avg_pnl.toFixed(2)}
                      </td>
                      <td className="mono text-green">${strategy.best_trade ? strategy.best_trade.toFixed(2) : '-'}</td>
                      <td className="mono">{strategy.profit_factor.toFixed(2)}</td>
                      <td>
                        <button 
                          className="btn-detail"
                          onClick={() => fetchStrategyDetail(strategy.strategy)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Context Matrix */}
          {strategies.length > 0 && (
            <div className="context-matrix-section">
              <h3>Performance by Market Context</h3>
              <div className="context-matrix-wrapper">
                <table className="context-matrix">
                  <thead>
                    <tr>
                      <th>Strategy</th>
                      <th>STRONG_BULLISH</th>
                      <th>WEAK_BULLISH</th>
                      <th>NEUTRAL</th>
                      <th>WEAK_BEARISH</th>
                      <th>STRONG_BEARISH</th>
                      <th>UNKNOWN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {strategies.map(strategy => (
                      <tr key={strategy.strategy}>
                        <td className="strategy-name bold">{strategy.strategy}</td>
                        {['STRONG_BULLISH', 'WEAK_BULLISH', 'NEUTRAL', 'WEAK_BEARISH', 'STRONG_BEARISH', 'UNKNOWN'].map(context => (
                          renderContextCell(strategies[0].context_breakdown?.[strategy.strategy]?.[context])
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default StrategyPerformanceChart;
