import React, { useState, useEffect } from 'react';
import { cryptoAPI as api } from '../../services/api';

/**
 * TradeHistoryTable - Simplified
 * Shows recent trades
 */
const TradeHistoryTable = ({ userId }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  const fetchTrades = async () => {
    try {
      console.log('📋 [TRADES] Fetching with days:', days);
      const data = await api.getTradesReport({ days, limit: 50 });
      console.log('✅ [TRADES] Trades received:', data.trades?.length || 0);
      setTrades(data.trades || []);
      setError(null);
    } catch (err) {
      console.error('❌ [TRADES] Error:', err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('📋 [TRADES] useEffect triggered, days =', days);
    fetchTrades();
  }, [days]);

  if (loading) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⏳ Loading trades...</div>;
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
      <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Trade History</h2>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ color: '#94a3b8', marginRight: '10px' }}>Period:</label>
        <select 
          value={days} 
          onChange={(e) => setDays(parseInt(e.target.value))}
          style={{
            padding: '8px 12px',
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer'
          }}
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {trades.length === 0 ? (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          background: '#1e293b',
          borderRadius: '8px',
          color: '#94a3b8'
        }}>
          <p>📭 No trades found</p>
        </div>
      ) : (
        <div style={{
          overflowX: 'auto',
          background: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '14px'
          }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #334155', background: '#0f172a' }}>
                <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8', fontWeight: '600' }}>Symbol</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8', fontWeight: '600' }}>Strategy</th>
                <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontWeight: '600' }}>Entry</th>
                <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontWeight: '600' }}>Exit</th>
                <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontWeight: '600' }}>Qty</th>
                <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontWeight: '600' }}>P&L</th>
                <th style={{ padding: '12px', textAlign: 'center', color: '#94a3b8', fontWeight: '600' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '12px', color: '#fff', fontWeight: '600' }}>{trade.symbol}</td>
                  <td style={{ padding: '12px', color: '#94a3b8' }}>{trade.strategy || '-'}</td>
                  <td style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontSize: '12px' }}>
                    ${trade.entry_price?.toFixed(4) || '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontSize: '12px' }}>
                    ${trade.exit_price?.toFixed(4) || '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', color: '#94a3b8' }}>
                    {trade.quantity?.toFixed(2) || '-'}
                  </td>
                  <td style={{
                    padding: '12px',
                    textAlign: 'right',
                    fontWeight: '600',
                    color: (trade.pnl || 0) >= 0 ? '#10b981' : '#ef4444'
                  }}>
                    ${(trade.pnl || 0).toFixed(2)}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: trade.status === 'CLOSED' ? '#065f46' : '#1e40af',
                      color: trade.status === 'CLOSED' ? '#d1fae5' : '#bfdbfe',
                      fontSize: '12px',
                      fontWeight: '600'
                    }}>
                      {trade.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#64748b' }}>
        📊 Showing {trades.length} trades from last {days} days
      </div>
    </div>
  );
};

export default TradeHistoryTable;
