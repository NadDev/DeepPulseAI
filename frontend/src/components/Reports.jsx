import React, { useState } from 'react';
import TradeHistoryTable from './reports/TradeHistoryTable';
import StrategyPerformanceChart from './reports/StrategyPerformanceChart';
import MarketContextAnalysis from './reports/MarketContextAnalysis';
import DashboardKPIs from './reports/DashboardKPIs';
import PerformanceCharts from './reports/PerformanceCharts';
import ExportReports from './reports/ExportReports';
import './Reports.css';

/**
 * Reports Page
 * Central hub for all reporting and analytics
 * Tabs: Dashboard, Trades, Strategies, Context, Charts
 */
const Reports = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [days, setDays] = useState(30);
  const userId = localStorage.getItem('user_id') || 'unknown';

  const tabs = [
    { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
    { id: 'trades', label: '💼 Trades', icon: '💼' },
    { id: 'strategies', label: '📈 Strategies', icon: '📈' },
    { id: 'context', label: '🎯 Market Context', icon: '🎯' },
    { id: 'charts', label: '📉 Charts', icon: '📉' },
    { id: 'export', label: '📥 Export', icon: '📥' }
  ];

  const renderTabContent = () => {
    console.log('Rendering tab:', activeTab);
    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            <div style={{ color: '#ccc', fontSize: '14px', marginBottom: '20px' }}>
              🔄 Loading Dashboard KPIs...
            </div>
            <DashboardKPIs userId={userId} />
          </>
        );
      case 'trades':
        return <TradeHistoryTable userId={userId} />;
      case 'strategies':
        return <StrategyPerformanceChart userId={userId} />;
      case 'context':
        return <MarketContextAnalysis userId={userId} />;
      case 'charts':
        return <PerformanceCharts userId={userId} days={days} />;
      case 'export':
        return <ExportReports userId={userId} days={days} />;
      default:
        return <div className="tab-placeholder">Select a tab</div>;
    }
  };

  return (
    <div className="reports-page" style={{ minHeight: '100vh', background: '#0a0e27' }}>
      <div className="reports-container" style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
        {/* Header */}
        <div style={{ 
          marginBottom: '32px',
          padding: '24px',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <h1 style={{ 
            margin: '0 0 8px 0',
            fontSize: '28px',
            color: '#fff'
          }}>📊 Trading Reports & Analytics</h1>
          <p style={{ margin: 0, color: '#94a3b8' }}>
            Comprehensive analysis of your trading performance
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ 
          display: 'flex', 
          gap: '10px', 
          marginBottom: '20px',
          flexWrap: 'wrap'
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 20px',
                background: activeTab === tab.id ? '#3b82f6' : '#1e293b',
                border: activeTab === tab.id ? '2px solid #3b82f6' : '1px solid #334155',
                borderRadius: '8px',
                color: activeTab === tab.id ? '#fff' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: activeTab === tab.id ? '600' : '400',
                transition: 'all 0.2s'
              }}
            >
              {tab.icon} {tab.label.replace(tab.icon, '').trim()}
            </button>
          ))}
        </div>

        {/* Active Tab Indicator */}
        <div style={{ 
          padding: '15px', 
          background: '#1e293b', 
          borderRadius: '8px', 
          marginBottom: '20px',
          border: '1px solid #334155'
        }}>
          <p style={{ margin: 0, color: '#10b981', fontSize: '14px' }}>
            ✅ Active Tab: <strong>{activeTab}</strong> | User: {userId}
          </p>
        </div>

        {/* Tab Content */}
        <div style={{ 
          background: '#0f172a', 
          borderRadius: '8px', 
          padding: '20px',
          border: '1px solid #334155',
          minHeight: '400px'
        }}>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default Reports;
