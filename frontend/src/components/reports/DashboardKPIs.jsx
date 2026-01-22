import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './DashboardKPIs.css';

/**
 * DashboardKPIs Component
 * High-level KPI metrics for trading performance
 * Shows Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown, Total P&L, etc.
 */
const DashboardKPIs = ({ userId }) => {
  const [kpis, setKpis] = useState(null);
  const [equityData, setEquityData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchDashboardData();
  }, [days]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch KPIs
      const kpiResponse = await axios.get(
        '/api/reports/performance',
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setKpis(kpiResponse.data);
      
      // Fetch equity curve
      const equityResponse = await axios.get(
        `/api/reports/equity-curve?days=${days}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      setEquityData(equityResponse.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch dashboard data');
      console.error('Error fetching dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateSharpeRatio = () => {
    if (!equityData || equityData.length < 2) return 'N/A';
    
    const returns = [];
    for (let i = 1; i < equityData.length; i++) {
      const dayReturn = (equityData[i].value - equityData[i - 1].value) / equityData[i - 1].value;
      returns.push(dayReturn);
    }
    
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((sum, ret) => sum + Math.pow(ret - avgReturn, 2), 0) / returns.length;
    const stdDev = Math.sqrt(variance);
    
    if (stdDev === 0) return 'N/A';
    const sharpeRatio = (avgReturn / stdDev) * Math.sqrt(252); // Annualized
    return sharpeRatio.toFixed(2);
  };

  const calculateMaxDrawdown = () => {
    if (!equityData || equityData.length === 0) return 'N/A';
    
    let maxDrawdown = 0;
    let peak = equityData[0].value;
    
    for (let i = 1; i < equityData.length; i++) {
      const currentValue = equityData[i].value;
      if (currentValue > peak) {
        peak = currentValue;
      }
      const drawdown = (peak - currentValue) / peak;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
    
    return (maxDrawdown * 100).toFixed(2);
  };

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  const sharpe = calculateSharpeRatio();
  const maxDD = calculateMaxDrawdown();

  return (
    <div className="dashboard-kpis-container">
      <div className="dashboard-header">
        <h2>📊 Performance Dashboard</h2>
        <div className="header-controls">
          <label>Period</label>
          <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={60}>Last 60 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
        </div>
      </div>

      {/* Primary KPIs */}
      <div className="kpi-grid-primary">
        <div className="kpi-card large">
          <div className="kpi-header">
            <h3>Total P&L</h3>
          </div>
          <div className={`kpi-value large ${(kpis?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
            ${kpis ? kpis.total_pnl.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">USD</div>
        </div>

        <div className="kpi-card large">
          <div className="kpi-header">
            <h3>Win Rate</h3>
          </div>
          <div className={`kpi-value large ${(kpis?.win_rate || 0) >= 50 ? 'positive' : 'negative'}`}>
            {kpis ? kpis.win_rate.toFixed(1) : '0.0'}%
          </div>
          <div className="kpi-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${Math.min(100, kpis?.win_rate || 0)}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="kpi-card large">
          <div className="kpi-header">
            <h3>Profit Factor</h3>
          </div>
          <div className={`kpi-value large ${(kpis?.profit_factor || 0) > 1 ? 'positive' : 'negative'}`}>
            {kpis ? kpis.profit_factor.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Wins / Losses</div>
        </div>

        <div className="kpi-card large">
          <div className="kpi-header">
            <h3>Sharpe Ratio</h3>
          </div>
          <div className="kpi-value large positive">
            {sharpe}
          </div>
          <div className="kpi-unit">Risk-Adjusted Return</div>
        </div>
      </div>

      {/* Secondary KPIs */}
      <div className="kpi-grid-secondary">
        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Total Trades</h3>
          </div>
          <div className="kpi-value">
            {kpis?.total_trades || 0}
          </div>
          <div className="kpi-breakdown">
            <span className="break-item">
              ✅ {kpis?.winning_trades || 0} wins
            </span>
            <span className="break-item">
              ❌ {kpis?.losing_trades || 0} losses
            </span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Avg Win</h3>
          </div>
          <div className="kpi-value positive">
            ${kpis ? kpis.average_win.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Per winning trade</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Avg Loss</h3>
          </div>
          <div className="kpi-value negative">
            ${kpis ? Math.abs(kpis.average_loss).toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Per losing trade</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Max Drawdown</h3>
          </div>
          <div className="kpi-value negative">
            {maxDD}%
          </div>
          <div className="kpi-unit">Peak to trough</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Best Trade</h3>
          </div>
          <div className="kpi-value positive">
            ${kpis ? kpis.best_trade.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Largest gain</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Worst Trade</h3>
          </div>
          <div className="kpi-value negative">
            ${kpis ? kpis.worst_trade.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Largest loss</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Avg Trade P&L</h3>
          </div>
          <div className={`kpi-value ${(kpis?.avg_trade_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
            ${kpis ? kpis.avg_trade_pnl.toFixed(2) : '0.00'}
          </div>
          <div className="kpi-unit">Average per trade</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <h3>Win/Loss Ratio</h3>
          </div>
          <div className="kpi-value">
            {kpis?.losing_trades ? (kpis.winning_trades / kpis.losing_trades).toFixed(2) : 'N/A'}
          </div>
          <div className="kpi-unit">Winners per loser</div>
        </div>
      </div>

      {/* Equity Curve Chart */}
      {equityData && equityData.length > 0 && (
        <div className="equity-chart-section">
          <h3>Equity Curve</h3>
          <div className="chart-container">
            <div className="simple-chart">
              {/* Simple ASCII-style chart */}
              <div className="chart-bars">
                {equityData.slice(-20).map((point, idx) => {
                  const min = Math.min(...equityData.map(d => d.value));
                  const max = Math.max(...equityData.map(d => d.value));
                  const range = max - min || 1;
                  const height = ((point.value - min) / range) * 100;
                  
                  return (
                    <div key={idx} className="chart-bar-container">
                      <div 
                        className={`chart-bar ${point.pnl >= 0 ? 'positive' : 'negative'}`}
                        style={{ height: `${height}%` }}
                        title={`${point.date}: $${point.value.toFixed(2)}`}
                      ></div>
                    </div>
                  );
                })}
              </div>
              <div className="chart-labels">
                <span className="label-left">${Math.min(...equityData.map(d => d.value)).toFixed(2)}</span>
                <span className="label-right">${Math.max(...equityData.map(d => d.value)).toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="summary-section">
        <h3>Summary</h3>
        <div className="summary-cards">
          <div className="summary-card">
            <h4>📈 Trend</h4>
            <p>
              {equityData && equityData.length > 1
                ? (equityData[equityData.length - 1].value > equityData[0].value ? '↗️ Uptrend' : '↘️ Downtrend')
                : 'N/A'}
            </p>
          </div>
          <div className="summary-card">
            <h4>💪 Strength</h4>
            <p>
              {kpis?.profit_factor > 1.5 ? '💎 Excellent' : kpis?.profit_factor > 1 ? '✅ Good' : '⚠️ Needs work'}
            </p>
          </div>
          <div className="summary-card">
            <h4>🎯 Consistency</h4>
            <p>
              {kpis?.win_rate > 60 ? '🔥 Highly consistent' : kpis?.win_rate > 50 ? '📊 Balanced' : '🌊 Variable'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardKPIs;
