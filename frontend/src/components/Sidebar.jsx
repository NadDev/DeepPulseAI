import React, { useState } from 'react';
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
  ChevronRight
} from 'lucide-react';
import './Sidebar.css';

function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
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
