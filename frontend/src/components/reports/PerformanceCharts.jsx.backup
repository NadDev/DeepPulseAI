import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import './PerformanceCharts.css';

/**
 * PerformanceCharts Component
 * Advanced charts: Equity curve, Drawdown, Strategy comparison, etc.
 */
const PerformanceCharts = ({ userId, days = 30 }) => {
  const [equityData, setEquityData] = useState(null);
  const [drawdownData, setDrawdownData] = useState(null);
  const [strategyData, setStrategyData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchChartsData();
  }, [days, userId]);

  const fetchChartsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('supabaseAuthToken');
      
      // Fetch equity curve data
      const equityRes = await axios.get('/api/reports/equity-curve', {
        params: { days },
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Transform equity data for chart
      const equityChartData = equityRes.data.map((item, idx) => ({
        date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        equity: parseFloat(item.equity.toFixed(2)),
        pnl: parseFloat(item.daily_pnl.toFixed(2)),
        percentChange: parseFloat(item.percent_change.toFixed(2))
      }));
      setEquityData(equityChartData);

      // Fetch drawdown data
      const drawdownRes = await axios.get('/api/reports/drawdown-history', {
        params: { days },
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const drawdownChartData = drawdownRes.data.map(item => ({
        date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        drawdown: parseFloat(item.drawdown.toFixed(2)),
        recoveryDays: item.recovery_days || 0
      }));
      setDrawdownData(drawdownChartData);

      // Fetch strategy comparison data
      const strategyRes = await axios.get('/api/reports/strategies', {
        params: { days },
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const strategyChartData = strategyRes.data.strategies.map(strat => ({
        name: strat.name,
        trades: strat.total_trades,
        wins: strat.winning_trades,
        pnl: parseFloat(strat.total_pnl.toFixed(2)),
        winRate: parseFloat((strat.win_rate * 100).toFixed(1))
      }));
      setStrategyData(strategyChartData);

    } catch (err) {
      console.error('Error fetching charts data:', err);
      setError('Failed to load charts data. ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="charts-container"><div className="loading">Loading performance charts...</div></div>;
  }

  if (error) {
    return <div className="charts-container"><div className="error-message">{error}</div></div>;
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="charts-container">
      
      {/* EQUITY CURVE CHART */}
      <div className="chart-section equity-section">
        <div className="chart-header">
          <h3>Equity Curve</h3>
          <p className="chart-description">Portfolio value over time</p>
        </div>
        {equityData && equityData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" style={{ fontSize: '12px' }} />
              <YAxis stroke="#64748b" style={{ fontSize: '12px' }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="equity" stroke="#3b82f6" fillOpacity={1} fill="url(#colorEquity)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="no-data">No equity curve data available</p>
        )}
      </div>

      {/* DAILY P&L CHART */}
      <div className="chart-section pnl-section">
        <div className="chart-header">
          <h3>Daily P&L</h3>
          <p className="chart-description">Daily profit/loss breakdown</p>
        </div>
        {equityData && equityData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={equityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" style={{ fontSize: '12px' }} />
              <YAxis stroke="#64748b" style={{ fontSize: '12px' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="pnl" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                {equityData.map((entry, index) => (
                  <Bar key={index} dataKey="pnl" fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="no-data">No daily P&L data available</p>
        )}
      </div>

      {/* DRAWDOWN CHART */}
      <div className="chart-section drawdown-section">
        <div className="chart-header">
          <h3>Drawdown Over Time</h3>
          <p className="chart-description">Peak-to-trough percentage decline</p>
        </div>
        {drawdownData && drawdownData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={drawdownData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" style={{ fontSize: '12px' }} />
              <YAxis stroke="#64748b" style={{ fontSize: '12px' }} label={{ value: 'Drawdown %', angle: -90, position: 'insideLeft' }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fillOpacity={1} fill="url(#colorDrawdown)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="no-data">No drawdown data available</p>
        )}
      </div>

      {/* STRATEGY COMPARISON CHART */}
      <div className="chart-section strategy-section">
        <div className="chart-header">
          <h3>Strategy Comparison</h3>
          <p className="chart-description">Performance by strategy</p>
        </div>
        {strategyData && strategyData.length > 0 ? (
          <>
            <div className="strategy-charts">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={strategyData} margin={{ top: 10, right: 30, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#64748b" style={{ fontSize: '12px' }} angle={-45} textAnchor="end" height={80} />
                  <YAxis stroke="#64748b" style={{ fontSize: '12px' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="pnl" fill="#3b82f6" name="Total P&L" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            <div className="strategy-table">
              <table>
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Trades</th>
                    <th>Wins</th>
                    <th>Win Rate</th>
                    <th>Total P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {strategyData.map((strat, idx) => (
                    <tr key={idx}>
                      <td><strong>{strat.name}</strong></td>
                      <td>{strat.trades}</td>
                      <td>{strat.wins}</td>
                      <td>
                        <span className={strat.winRate >= 50 ? 'positive' : 'negative'}>
                          {strat.winRate.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <span className={strat.pnl >= 0 ? 'positive' : 'negative'}>
                          ${strat.pnl.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="no-data">No strategy data available</p>
        )}
      </div>

    </div>
  );
};

export default PerformanceCharts;
