import React, { useState } from 'react';
import { Settings as SettingsIcon, Cpu, Lock, HelpCircle, Link2, Star, TrendingUp } from 'lucide-react';
import AISettings from './AISettings';
import ExchangeSettings from './ExchangeSettings';
import WatchlistManager from './WatchlistManager';
import TradingSettings from './TradingSettings';
import '../styles/Settings.css';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('ai');

  const tabs = [
    {
      id: 'ai',
      label: 'AI Agent',
      icon: <Cpu size={18} />,
      component: <AISettings />
    },
    {
      id: 'trading',
      label: 'Trading',
      icon: <TrendingUp size={18} />,
      component: <TradingSettings />
    },
    {
      id: 'exchange',
      label: 'Exchanges',
      icon: <Link2 size={18} />,
      component: <ExchangeSettings />
    },
    {
      id: 'watchlist',
      label: 'Watchlist',
      icon: <Star size={18} />,
      component: <WatchlistManager />
    },
    {
      id: 'security',
      label: 'Security',
      icon: <Lock size={18} />,
      component: <SecuritySettings />
    },
    {
      id: 'help',
      label: 'Help',
      icon: <HelpCircle size={18} />,
      component: <HelpSettings />
    }
  ];

  const activeTabData = tabs.find(t => t.id === activeTab);

  return (
    <div className="settings-page">
      <div className="settings-container">
        <div className="settings-header">
          <div className="header-content">
            <SettingsIcon size={32} />
            <div>
              <h1>Settings</h1>
              <p>Configure your CRBot AI Trading Agent</p>
            </div>
          </div>
        </div>

        <div className="settings-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <div className="settings-content-wrapper">
          {activeTabData && activeTabData.component}
        </div>
      </div>
    </div>
  );
}

// Security Settings Component
function SecuritySettings() {
  return (
    <div className="settings-page-section">
      <div className="section-header">
        <h2>🔐 Security Settings</h2>
        <p>Manage authentication and security preferences</p>
      </div>

      <div className="security-info">
        <div className="info-item">
          <h3>API Key Management</h3>
          <p>Your API keys are stored securely and never sent to the client.</p>
          <button className="btn-secondary">Rotate API Keys</button>
        </div>

        <div className="info-item">
          <h3>Two-Factor Authentication</h3>
          <p>Enable 2FA to add an extra layer of security to your account.</p>
          <button className="btn-secondary">Enable 2FA</button>
        </div>

        <div className="info-item">
          <h3>Session Management</h3>
          <p>View and manage your active sessions.</p>
          <button className="btn-secondary">View Sessions</button>
        </div>

        <div className="info-item warning">
          <h3>Danger Zone</h3>
          <p>Delete your account and all associated data permanently.</p>
          <button className="btn-danger">Delete Account</button>
        </div>
      </div>
    </div>
  );
}

// Help Settings Component
function HelpSettings() {
  return (
    <div className="settings-page-section">
      <div className="section-header">
        <h2>❓ Help & Documentation</h2>
        <p>Learn more about CRBot and how to use it</p>
      </div>

      <div className="help-content">
        <div className="faq-item">
          <h3>What is the AI Trading Agent?</h3>
          <p>
            The AI Trading Agent uses DeepSeek AI to analyze cryptocurrency markets and provide trading recommendations.
            It can operate in three modes: observation (analysis only), paper trading (simulated), and autonomous trading.
          </p>
        </div>

        <div className="faq-item">
          <h3>What is the difference between Advisory and Autonomous modes?</h3>
          <p>
            <strong>Advisory Mode:</strong> AI makes recommendations that you can accept or reject before execution.
            <br />
            <strong>Autonomous Mode:</strong> AI executes trades automatically based on configured parameters (for advanced users only).
          </p>
        </div>

        <div className="faq-item">
          <h3>How does risk management work?</h3>
          <p>
            Risk per trade is limited to a percentage of your portfolio. Stop loss automatically exits losing positions.
            The AI respects all configured limits and never uses leverage or margin trading.
          </p>
        </div>

        <div className="faq-item">
          <h3>Can I lose all my money?</h3>
          <p>
            Trading carries risk. The AI Bot includes multiple safeguards:
            <ul>
              <li>Stop loss limits per-trade losses</li>
              <li>Daily trade limits prevent overtrading</li>
              <li>Confidence thresholds prevent low-confidence trades</li>
              <li>Spot trading only - no leverage or futures</li>
            </ul>
          </p>
        </div>

        <div className="faq-item">
          <h3>Where can I get more help?</h3>
          <p>
            <a href="#" target="_blank" rel="noopener noreferrer">View documentation</a>
            <br />
            <a href="#" target="_blank" rel="noopener noreferrer">Contact support</a>
            <br />
            <a href="#" target="_blank" rel="noopener noreferrer">Community forums</a>
          </p>
        </div>
      </div>
    </div>
  );
}
