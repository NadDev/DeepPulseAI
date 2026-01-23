import React, { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * DashboardKPIs Component - Simplified
 * Shows key trading metrics
 */
const DashboardKPIs = ({ userId }) => {
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      console.log('📊 Fetching KPIs with token:', token ? 'YES' : 'NO');
      
      const response = await axios.get('/api/reports/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log('✅ KPI data:', response.data);
      setKpis(response.data);
      setError(null);
    } catch (err) {
      console.error('❌ Error:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⏳ Loading KPIs...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', background: '#7f1d1d', borderRadius: '4px', color: '#fca5a5' }}>
        <p><strong>❌ Error:</strong> {error}</p>
        <button 
          onClick={fetchDashboardData}
          style={{
            marginTop: '10px',
            padding: '8px 16px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          🔄 Retry
        </button>
      </div>
    );
  }

  if (!kpis) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⚠️ No data available</div>;
  }

  return (
    <div style={{ color: '#fff' }}>
      <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Performance Metrics</h2>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '20px',
        marginBottom: '30px'
      }}>
        {/* Total P&L */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Total P&L</div>
          <div style={{
            fontSize: '28px',
            fontWeight: 'bold',
            color: (kpis.total_pnl || 0) >= 0 ? '#10b981' : '#ef4444'
          }}>
            ${(kpis.total_pnl || 0).toFixed(2)}
          </div>
        </div>

        {/* Win Rate */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Win Rate</div>
          <div style={{
            fontSize: '28px',
            fontWeight: 'bold',
            color: (kpis.win_rate || 0) >= 50 ? '#10b981' : '#ef4444'
          }}>
            {(kpis.win_rate || 0).toFixed(1)}%
          </div>
        </div>

        {/* Profit Factor */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Profit Factor</div>
          <div style={{
            fontSize: '28px',
            fontWeight: 'bold',
            color: (kpis.profit_factor || 0) > 1 ? '#10b981' : '#ef4444'
          }}>
            {(kpis.profit_factor || 0).toFixed(2)}
          </div>
        </div>

        {/* Total Trades */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Total Trades</div>
          <div style={{
            fontSize: '28px',
            fontWeight: 'bold',
            color: '#3b82f6'
          }}>
            {kpis.total_trades || 0}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '8px' }}>
            ✅ {kpis.winning_trades || 0} | ❌ {kpis.losing_trades || 0}
          </div>
        </div>

        {/* Avg Win */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Avg Win</div>
          <div style={{
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#10b981'
          }}>
            ${(kpis.average_win || 0).toFixed(2)}
          </div>
        </div>

        {/* Avg Loss */}
        <div style={{
          padding: '20px',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Avg Loss</div>
          <div style={{
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#ef4444'
          }}>
            -${Math.abs(kpis.average_loss || 0).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Summary Table */}
      <div style={{
        padding: '20px',
        background: '#1e293b',
        borderRadius: '8px',
        border: '1px solid #334155'
      }}>
        <h3 style={{ marginTop: 0 }}>Summary</h3>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '14px'
        }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #334155' }}>
              <td style={{ padding: '12px 0', color: '#94a3b8' }}>Best Trade</td>
              <td style={{ padding: '12px 0', textAlign: 'right', color: '#10b981', fontWeight: 'bold' }}>
                ${(kpis.best_trade || 0).toFixed(2)}
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #334155' }}>
              <td style={{ padding: '12px 0', color: '#94a3b8' }}>Worst Trade</td>
              <td style={{ padding: '12px 0', textAlign: 'right', color: '#ef4444', fontWeight: 'bold' }}>
                -${Math.abs(kpis.worst_trade || 0).toFixed(2)}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '12px 0', color: '#94a3b8' }}>Avg Trade P&L</td>
              <td style={{
                padding: '12px 0',
                textAlign: 'right',
                color: (kpis.avg_trade_pnl || 0) >= 0 ? '#10b981' : '#ef4444',
                fontWeight: 'bold'
              }}>
                ${(kpis.avg_trade_pnl || 0).toFixed(2)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#64748b' }}>
        ℹ️ Data updated at {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};

export default DashboardKPIs;
