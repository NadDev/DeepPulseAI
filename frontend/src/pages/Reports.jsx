import React, { useState } from 'react';
import TradeHistoryTable from '../components/reports/TradeHistoryTable';
import StrategyPerformanceChart from '../components/reports/StrategyPerformanceChart';
import MarketContextAnalysis from '../components/reports/MarketContextAnalysis';
import DashboardKPIs from '../components/reports/DashboardKPIs';
import PerformanceCharts from '../components/reports/PerformanceCharts';
import ExportReports from '../components/reports/ExportReports';
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
    <div className="reports-page">
      <div className="reports-container">
        {/* Header */}
        <div className="reports-page-header">
          <div className="header-content">
            <h1>📊 Trading Reports & Analytics</h1>
            <p>Comprehensive analysis of your trading performance, strategies, and market conditions</p>
          </div>
          <div className="header-controls">
            <label htmlFor="period-select">Period:</label>
            <select 
              id="period-select"
              value={days} 
              onChange={(e) => setDays(parseInt(e.target.value))}
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
            </select>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="tab-navigation">
          <div className="tab-list">
            {tabs.map(tab => (
              <button
                key={tab.id}
                className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="tab-icon">{tab.icon}</span>
                <span className="tab-label">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default Reports;
