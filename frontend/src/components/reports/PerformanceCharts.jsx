import React, { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * PerformanceCharts - Simplified
 * Shows equity curve and performance charts
 */
const PerformanceCharts = ({ userId, days = 30 }) => {
  const [equityData, setEquityData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEquityData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      console.log('📈 [CHARTS] Fetching equity curve with token:', token ? 'YES' : 'NO');
      
      const response = await axios.get('/api/reports/equity-curve', {
        params: { days },
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log('✅ [CHARTS] Equity data received:', response.data?.length || 0, 'points');
      setEquityData(response.data || []);
      setError(null);
    } catch (err) {
      console.error('❌ [CHARTS] Error:', err.response?.status, err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('📈 [CHARTS] useEffect triggered, days =', days);
    fetchEquityData();
  }, [days]);

  if (loading) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⏳ Loading performance charts...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', background: '#7f1d1d', borderRadius: '4px', color: '#fca5a5' }}>
        <p><strong>❌ Error:</strong> {error}</p>
      </div>
    );
  }

  if (equityData.length === 0) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        background: '#1e293b',
        borderRadius: '8px',
        color: '#94a3b8'
      }}>
        <p>📭 No equity data available</p>
      </div>
    );
  }

  // Calculate statistics
  const startValue = equityData[0]?.value || 0;
  const endValue = equityData[equityData.length - 1]?.value || 0;
  const totalReturn = ((endValue - startValue) / startValue * 100) || 0;

  // Find max and min for chart scaling
  const values = equityData.map(d => d.value);
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const range = maxValue - minValue || 1;

  // Sample data for better visualization (limit to 50 points)
  const sampledData = equityData.length > 50 
    ? equityData.filter((_, i) => i % Math.ceil(equityData.length / 50) === 0)
    : equityData;

  return (
    <div style={{ color: '#fff' }}>
      <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Performance Charts</h2>

      {/* Key Metrics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '20px',
        marginBottom: '30px'
      }}>
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Total Return</div>
          <div style={{
            fontSize: '28px',
            fontWeight: 'bold',
            color: totalReturn >= 0 ? '#10b981' : '#ef4444'
          }}>
            {totalReturn.toFixed(2)}%
          </div>
        </div>

        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Start Value</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6' }}>
            ${startValue.toFixed(2)}
          </div>
        </div>

        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>End Value</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981' }}>
            ${endValue.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Equity Curve Chart */}
      <div style={{
        padding: '20px',
        background: '#1e293b',
        borderRadius: '8px',
        border: '1px solid #334155'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Equity Curve</h3>
        
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', height: '250px', gap: '2px' }}>
          {sampledData.map((point, idx) => {
            const height = ((point.value - minValue) / range * 100) || 0;
            const isPositive = point.pnl >= 0;
            
            return (
              <div
                key={idx}
                style={{
                  flex: 1,
                  height: `${height}%`,
                  background: isPositive ? '#10b981' : '#ef4444',
                  borderRadius: '2px',
                  opacity: 0.8,
                  transition: 'all 0.2s',
                  cursor: 'pointer',
                  minHeight: '4px'
                }}
                title={`${point.date}: $${point.value.toFixed(2)}`}
              />
            );
          })}
        </div>

        <div style={{
          marginTop: '15px',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '12px',
          color: '#64748b'
        }}>
          <span>Min: ${minValue.toFixed(2)}</span>
          <span>Max: ${maxValue.toFixed(2)}</span>
          <span>{equityData.length} data points</span>
        </div>
      </div>

      {/* Daily Returns */}
      <div style={{
        padding: '20px',
        background: '#1e293b',
        borderRadius: '8px',
        border: '1px solid #334155',
        marginTop: '20px'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '15px' }}>Recent Daily Changes</h3>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '10px'
        }}>
          {equityData.slice(-10).reverse().map((point, idx) => (
            <div key={idx} style={{
              padding: '12px',
              background: '#0f172a',
              borderRadius: '6px',
              border: `1px solid ${point.pnl >= 0 ? '#10b981' : '#ef4444'}`,
              fontSize: '12px'
            }}>
              <div style={{ color: '#94a3b8', marginBottom: '4px' }}>{point.date}</div>
              <div style={{ color: point.pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                {point.pnl >= 0 ? '+' : ''}{point.pnl.toFixed(2)}
              </div>
              <div style={{ color: '#64748b', fontSize: '11px' }}>
                ${point.value.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PerformanceCharts;
