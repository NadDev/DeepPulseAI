import React, { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * MarketContextAnalysis - Simplified
 * Shows trade performance by market context
 */
const MarketContextAnalysis = ({ userId, days = 30 }) => {
  const [contextStats, setContextStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchContextAnalysis = async () => {
    try {
      const token = localStorage.getItem('access_token');
      console.log('🌍 [CONTEXT] Fetching with token:', token ? 'YES' : 'NO');
      
      const response = await axios.get('/api/reports/trades', {
        params: { days, limit: 1000 },
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log('✅ [CONTEXT] Trades received:', response.data.trades?.length || 0);
      
      // Group trades by market context
      const trades = response.data.trades || [];
      const grouped = {};
      
      trades.forEach(trade => {
        const context = trade.market_context || 'UNKNOWN';
        if (!grouped[context]) {
          grouped[context] = {
            name: context,
            trades: 0,
            winning: 0,
            total_pnl: 0,
            trades_list: []
          };
        }
        grouped[context].trades++;
        if (trade.pnl && trade.pnl > 0) grouped[context].winning++;
        grouped[context].total_pnl += (trade.pnl || 0);
        grouped[context].trades_list.push(trade);
      });

      setContextStats(grouped);
      setError(null);
    } catch (err) {
      console.error('❌ [CONTEXT] Error:', err.response?.status, err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🌍 [CONTEXT] useEffect triggered, days =', days);
    fetchContextAnalysis();
  }, [days]);

  if (loading) {
    return <div style={{ padding: '20px', color: '#94a3b8' }}>⏳ Loading market context analysis...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', background: '#7f1d1d', borderRadius: '4px', color: '#fca5a5' }}>
        <p><strong>❌ Error:</strong> {error}</p>
      </div>
    );
  }

  const contexts = Object.values(contextStats);

  return (
    <div style={{ color: '#fff' }}>
      <h2 style={{ marginTop: 0, marginBottom: '20px' }}>Market Context Analysis</h2>

      {contexts.length === 0 ? (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          background: '#1e293b',
          borderRadius: '8px',
          color: '#94a3b8'
        }}>
          <p>📭 No market context data available</p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px'
        }}>
          {contexts.map((ctx, idx) => {
            const winRate = ctx.trades > 0 ? (ctx.winning / ctx.trades * 100) : 0;
            const avgPnl = ctx.trades > 0 ? ctx.total_pnl / ctx.trades : 0;
            
            return (
              <div key={idx} style={{
                padding: '20px',
                background: '#1e293b',
                borderRadius: '8px',
                border: '1px solid #334155'
              }}>
                <h3 style={{ marginTop: 0, marginBottom: '15px', color: '#10b981' }}>
                  🎯 {ctx.name}
                </h3>
                
                <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span style={{ color: '#94a3b8' }}>Trades:</span>
                  <span style={{ fontWeight: '600', color: '#fff' }}>{ctx.trades}</span>
                </div>

                <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span style={{ color: '#94a3b8' }}>Win Rate:</span>
                  <span style={{
                    fontWeight: '600',
                    color: winRate >= 50 ? '#10b981' : '#ef4444'
                  }}>
                    {winRate.toFixed(1)}%
                  </span>
                </div>

                <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span style={{ color: '#94a3b8' }}>Total P&L:</span>
                  <span style={{
                    fontWeight: '600',
                    color: ctx.total_pnl >= 0 ? '#10b981' : '#ef4444'
                  }}>
                    ${ctx.total_pnl.toFixed(2)}
                  </span>
                </div>

                <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span style={{ color: '#94a3b8' }}>Avg P&L:</span>
                  <span style={{
                    fontWeight: '600',
                    color: avgPnl >= 0 ? '#10b981' : '#ef4444'
                  }}>
                    ${avgPnl.toFixed(2)}
                  </span>
                </div>

                <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #334155' }}>
                  <div style={{
                    width: '100%',
                    height: '20px',
                    background: '#0f172a',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, winRate)}%`,
                      background: winRate >= 50 ? '#10b981' : '#ef4444',
                      transition: 'width 0.3s'
                    }} />
                  </div>
                  <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#64748b' }}>
                    Win rate: {winRate.toFixed(1)}%
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MarketContextAnalysis;
