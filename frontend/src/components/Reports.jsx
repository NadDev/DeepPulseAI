import React, { useState } from 'react';
import DashboardKPIs from './reports/DashboardKPIs';

/**
 * Reports Page - With DashboardKPIs
 */
const Reports = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div style={{ padding: '40px', background: '#0a0e27', minHeight: '100vh', color: '#fff' }}>
      <h1>📊 Trading Reports & Analytics</h1>
      
      <div style={{ marginTop: '20px', marginBottom: '20px' }}>
        <button 
          onClick={() => setActiveTab('dashboard')}
          style={{
            padding: '10px 20px',
            marginRight: '10px',
            background: activeTab === 'dashboard' ? '#3b82f6' : '#1e293b',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
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
            cursor: 'pointer'
          }}
        >
          💼 Trades
        </button>
      </div>

      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '8px', marginTop: '20px' }}>
        {activeTab === 'dashboard' && (
          <div>
            <DashboardKPIs userId="default" />
          </div>
        )}
        
        {activeTab === 'trades' && (
          <div>
            <h2>Trades Content</h2>
            <p>📊 Trades analysis coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;
