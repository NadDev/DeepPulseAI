import React, { useState } from 'react';
import DashboardKPIs from './reports/DashboardKPIs';
import TradeHistoryTable from './reports/TradeHistoryTable';

/**
 * Reports Page - With DashboardKPIs and TradeHistoryTable
 */
const Reports = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div style={{ padding: '40px', background: '#0a0e27', minHeight: '100vh', color: '#fff' }}>
      <h1>📊 Trading Reports & Analytics</h1>
      
      <div style={{ marginTop: '20px', marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button 
          onClick={() => setActiveTab('dashboard')}
          style={{
            padding: '10px 20px',
            background: activeTab === 'dashboard' ? '#3b82f6' : '#1e293b',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: activeTab === 'dashboard' ? '600' : '400'
          }}
        >
          📊 Dashboard
        </button>
        <button 
          onClick={() => setActiveTab('trades')}
          style={{
            padding: '10px 20px',
            background: activeTab === 'trades' ? '#3b82f6' : '#1e293b',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: activeTab === 'trades' ? '600' : '400'
          }}
        >
          💼 Trades
        </button>
        <button 
          onClick={() => setActiveTab('strategies')}
          style={{
            padding: '10px 20px',
            background: activeTab === 'strategies' ? '#3b82f6' : '#1e293b',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: activeTab === 'strategies' ? '600' : '400'
          }}
        >
          📈 Strategies
        </button>
      </div>

      <div style={{ marginTop: '20px' }}>
        {activeTab === 'dashboard' && <DashboardKPIs userId="default" />}
        
        {activeTab === 'trades' && <TradeHistoryTable userId="default" />}
        
        {activeTab === 'strategies' && (
          <div style={{ padding: '20px', background: '#1e293b', borderRadius: '8px' }}>
            <h2>📈 Strategy Performance</h2>
            <p style={{ color: '#94a3b8' }}>Coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;
