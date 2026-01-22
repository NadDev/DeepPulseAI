import React, { useState } from 'react';
import TradeHistoryTable from '../components/reports/TradeHistoryTable';
import StrategyPerformanceChart from '../components/reports/StrategyPerformanceChart';
import MarketContextAnalysis from '../components/reports/MarketContextAnalysis';
import DashboardKPIs from '../components/reports/DashboardKPIs';
import './Reports.css';

/**
 * Reports Page
 * Central hub for all reporting and analytics
 * Tabs: Trades, Strategies, Context, Dashboard
 */
const Reports = () => {
  const [activeTab, setActiveTab] = useState('trades');
  const userId = localStorage.getItem('user_id') || 'unknown';

  const tabs = [
    { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
    { id: 'trades', label: '💼 Trades', icon: '💼' },
    { id: 'strategies', label: '📈 Strategies', icon: '📈' },
    { id: 'context', label: '🎯 Market Context', icon: '🎯' }
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardKPIs userId={userId} />;
      case 'trades':
        return <TradeHistoryTable userId={userId} />;
      case 'strategies':
        return <StrategyPerformanceChart userId={userId} />;
      case 'context':
        return <MarketContextAnalysis userId={userId} />;
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
