import React, { useState } from 'react';
import DashboardKPIs from './reports/DashboardKPIs';
import TradeHistoryTable from './reports/TradeHistoryTable';
import StrategyPerformanceChart from './reports/StrategyPerformanceChart';
import MarketContextAnalysis from './reports/MarketContextAnalysis';
import PerformanceCharts from './reports/PerformanceCharts';

/**
 * Reports Page - Full featured
 */
const Reports = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [days, setDays] = useState(30);

  const tabs = [
    { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
    { id: 'trades', label: '💼 Trades', icon: '💼' },
    { id: 'strategies', label: '📈 Strategies', icon: '📈' },
    { id: 'context', label: '🎯 Market Context', icon: '🎯' },
    { id: 'charts', label: '📉 Charts', icon: '📉' }
  ];

  return (
    <div style={{ padding: '40px', background: '#0a0e27', minHeight: '100vh', color: '#fff' }}>
      <h1>📊 Trading Reports & Analytics</h1>
      
      <div style={{ marginTop: '20px', marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        {tabs.map(tab => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 16px',
              background: activeTab === tab.id ? '#3b82f6' : '#1e293b',
              color: '#fff',
              border: activeTab === tab.id ? '2px solid #3b82f6' : '1px solid #334155',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === tab.id ? '600' : '400',
              transition: 'all 0.2s'
            }}
          >
            {tab.icon} {tab.label.replace(tab.icon, '').trim()}
          </button>
        ))}

        {/* Days filter */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ color: '#94a3b8', fontSize: '14px' }}>Period:</label>
          <select 
            value={days} 
            onChange={(e) => setDays(parseInt(e.target.value))}
            style={{
              padding: '8px 12px',
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '4px',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      <div style={{ marginTop: '20px' }}>
        {activeTab === 'dashboard' && <DashboardKPIs userId="default" />}
        
        {activeTab === 'trades' && <TradeHistoryTable userId="default" days={days} />}
        
        {activeTab === 'strategies' && <StrategyPerformanceChart userId="default" days={days} />}
        
        {activeTab === 'context' && <MarketContextAnalysis userId="default" days={days} />}
        
        {activeTab === 'charts' && <PerformanceCharts userId="default" days={days} />}
      </div>
    </div>
  );
};

export default Reports;
