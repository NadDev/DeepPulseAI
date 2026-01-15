import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  LineChart, 
  BarChart2, 
  Bot, 
  Brain,
  FileText, 
  ShieldAlert, 
  Settings,
  Wallet,
  ChevronLeft,
  ChevronRight,
  Play,
  Zap,
  Square
} from 'lucide-react';
import './Sidebar.css';

function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [aiRunning, setAiRunning] = useState(false);
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const menuItems = [
    { path: '/', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
    { path: '/charts', icon: <LineChart size={20} />, label: 'Charts' },
    { path: '/portfolio', icon: <Wallet size={20} />, label: 'Portfolio' },
    { path: '/markets', icon: <BarChart2 size={20} />, label: 'Markets' },
    { path: '/bots', icon: <Bot size={20} />, label: 'Bot Manager' },
    { path: '/ai-agent', icon: <Brain size={20} />, label: 'AI Agent' },
    { path: '/reports', icon: <FileText size={20} />, label: 'Reports' },
    { path: '/risk', icon: <ShieldAlert size={20} />, label: 'Risk Mgmt' },
    { path: '/settings', icon: <Settings size={20} />, label: 'Settings' },
  ];

  // Fetch initial state on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/ai-agent/status');
        if (response.ok) {
          const data = await response.json();
          setAiRunning(data.running || false);
        }
      } catch (error) {
        console.error('Failed to fetch AI status:', error);
      }

      try {
        const response = await fetch('/api/ai-agent/autonomous/config');
        if (response.ok) {
          const data = await response.json();
          setAutoTradeEnabled(data.autonomous_enabled || false);
        }
      } catch (error) {
        console.error('Failed to fetch auto trade status:', error);
      }
    };

    fetchStatus();
  }, []);

  // Toggle AI Agent
  const handleToggleAI = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/ai-agent/toggle', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setAiRunning(data.running || !aiRunning);
      }
    } catch (error) {
      console.error('Failed to toggle AI:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle Auto Trade
  const handleToggleAutoTrade = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/ai-agent/autonomous/toggle', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setAutoTradeEnabled(data.autonomous_enabled || !autoTradeEnabled);
      }
    } catch (error) {
      console.error('Failed to toggle auto trade:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside className={`app-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <button 
        className="sidebar-toggle-btn"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>

      <div className="sidebar-logo">
        <div className="logo-icon">
          <Bot size={32} />
        </div>
        <h1 className="logo-text">DeepPulseAI</h1>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="sidebar-quick-actions">
        <div className="quick-actions-label">Quick Actions</div>
        
        <button 
          className={`quick-action-btn ${aiRunning ? 'active' : ''} ${isLoading ? 'loading' : ''}`}
          onClick={handleToggleAI}
          disabled={isLoading}
          title={aiRunning ? 'Stop AI Agent' : 'Start AI Agent'}
        >
          {aiRunning ? (
            <>
              <Square size={16} fill="currentColor" />
              <span>Stop AI</span>
            </>
          ) : (
            <>
              <Play size={16} />
              <span>Run AI</span>
            </>
          )}
        </button>
        
        <button 
          className={`quick-action-btn ${autoTradeEnabled ? 'active' : ''} ${isLoading ? 'loading' : ''}`}
          onClick={handleToggleAutoTrade}
          disabled={isLoading}
          title={autoTradeEnabled ? 'Disable Auto Trade' : 'Enable Auto Trade'}
        >
          {autoTradeEnabled ? (
            <>
              <Zap size={16} fill="currentColor" />
              <span>Disable Auto</span>
            </>
          ) : (
            <>
              <Zap size={16} />
              <span>Auto Trade</span>
            </>
          )}
        </button>
      </div>
      
      <div className="sidebar-footer">
        <div className="sidebar-stats">
          <p>Version: <span className="highlight">v1.2.0</span></p>
          <p>Env: <span className="highlight">Production</span></p>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
