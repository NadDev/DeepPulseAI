import React, { useState, useEffect } from 'react';
import { cryptoAPI as api } from '../../services/api';

/**
 * StrategyPerformanceChart - Simplified
 * Shows performance by strategy
 */
const StrategyPerformanceChart = ({ userId, days = 30 }) => {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStrategies = async () => {
    try {
      console.log('🎯 [STRATEGIES] Fetching with days:', days);
      const data = await api.getStrategiesReport(days);
      console.log('✅ [STRATEGIES] Data received:', data);
      setStrategies(data.strategies || []);
      setError(null);
    } catch (err) {
      console.error('❌ [STRATEGIES] Error:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🎯 [STRATEGIES] useEffect triggered, days =', days);
    fetchStrategies();
  }, [days]);

  if (loading) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⏳ Loading strategies...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', background: '#7f1d1d', borderRadius: '4px', color: '#fca5a5' }}>
        <p><strong>❌ Error:</strong> {error}</p>
      </div>
    );
  }

  return (
    <div style={{ color: '#fff' }}>
      <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Strategy Performance</h2>

      {strategies.length === 0 ? (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          background: '#1e293b',
          borderRadius: '8px',
          color: '#94a3b8'
        }}>
          <p>📭 No strategy data available</p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px'
        }}>
          {strategies.map((strategy, idx) => (
            <div key={idx} style={{
              padding: '20px',
              background: '#1e293b',
              borderRadius: '8px',
              border: '1px solid #334155'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '15px', color: '#3b82f6' }}>
                {strategy.name || `Strategy ${idx + 1}`}
              </h3>
              
              <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                <span style={{ color: '#94a3b8' }}>Trades:</span>
                <span style={{ fontWeight: '600', color: '#fff' }}>{strategy.total_trades || 0}</span>
              </div>

              <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                <span style={{ color: '#94a3b8' }}>Win Rate:</span>
                <span style={{
                  fontWeight: '600',
                  color: (strategy.win_rate || 0) >= 50 ? '#10b981' : '#ef4444'
                }}>
                  {(strategy.win_rate || 0).toFixed(1)}%
                </span>
              </div>

              <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                <span style={{ color: '#94a3b8' }}>Total P&L:</span>
                <span style={{
                  fontWeight: '600',
                  color: (strategy.total_pnl || 0) >= 0 ? '#10b981' : '#ef4444'
                }}>
                  ${(strategy.total_pnl || 0).toFixed(2)}
                </span>
              </div>

              <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                <span style={{ color: '#94a3b8' }}>Profit Factor:</span>
                <span style={{
                  fontWeight: '600',
                  color: (strategy.profit_factor || 0) > 1 ? '#10b981' : '#ef4444'
                }}>
                  {(strategy.profit_factor || 0).toFixed(2)}
                </span>
              </div>

              <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #334155', fontSize: '12px', color: '#64748b' }}>
                {strategy.description && <p style={{ margin: 0 }}>{strategy.description}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StrategyPerformanceChart;
