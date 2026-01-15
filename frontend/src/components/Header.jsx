import React, { useState, useEffect } from 'react';
import { Globe, User, Settings, Activity, LogOut, ChevronDown, Zap, Play, Square, Menu, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import aiAPI from '../services/aiAPI';
import './Header.css';

function Header({ onToggleSidebar }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = useState(false);
  const [aiRunning, setAiRunning] = useState(false);
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Fetch AI status on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await aiAPI.getStatus();
        setAiRunning(status.running || status.ai_agent?.running || false);
        
        const config = await aiAPI.getAutonomousConfig();
        setAutoTradeEnabled(config.autonomous_mode || false);
      } catch (error) {
        console.error('Failed to fetch AI status:', error);
      }
    };
    if (user) {
      fetchStatus();
    }
  }, [user]);

  // Toggle AI Agent (same as AIAgent.jsx)
  const handleToggleAI = async () => {
    setIsLoading(true);
    try {
      const result = await aiAPI.toggleAgent();
      console.log('🔄 Toggle AI result:', result);
      setAiRunning(result.running);
    } catch (error) {
      console.error('Failed to toggle AI:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle Auto Trade (same as AIAgent.jsx)
  const handleToggleAutoTrade = async () => {
    setIsLoading(true);
    try {
      const result = await aiAPI.toggleAutonomousMode(!autoTradeEnabled);
      console.log('🤖 Toggle AutoTrade result:', result);
      setAutoTradeEnabled(result.autonomous_mode);
    } catch (error) {
      console.error('Failed to toggle auto trade:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const getUserDisplayName = () => {
    if (!user) return 'Guest';
    return user.user_metadata?.username || user.email?.split('@')[0] || 'User';
  };

  return (
    <header className="app-header">
      <div className="header-content">
        {/* Mobile Menu Button */}
        <button 
          className="mobile-menu-btn"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          title="Toggle menu"
        >
          {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <div className="header-spacer"></div> {/* Spacer to push actions to right */}
        
        <div className="header-actions">
          <div className="header-ai-controls">
            <button 
              className={`ai-btn ${aiRunning ? 'active' : ''}`}
              onClick={handleToggleAI}
              disabled={isLoading}
              title={aiRunning ? 'Stop AI Agent' : 'Start AI Agent'}
            >
              {aiRunning ? <Square size={14} /> : <Play size={14} />}
              <span>{aiRunning ? 'Stop AI' : 'Run AI'}</span>
            </button>
            <button 
              className={`auto-trade-btn ${autoTradeEnabled ? 'active' : ''}`}
              onClick={handleToggleAutoTrade}
              disabled={isLoading}
              title={autoTradeEnabled ? 'Disable Auto Trading' : 'Enable Auto Trading'}
            >
              <Zap size={14} />
              <span>{autoTradeEnabled ? 'Auto: ON' : 'Auto Trade'}</span>
            </button>
          </div>
          
          <div className="language-selector">
            <Globe size={16} className="text-gray" />
            <select className="lang-select">
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="es">Español</option>
            </select>
          </div>
          
          <div className="api-status online">
            <Activity size={14} />
            <span>API: LIVE</span>
          </div>
          
          {user ? (
            <div className="user-dropdown-container">
              <button 
                className="user-menu-btn" 
                onClick={() => setShowDropdown(!showDropdown)}
              >
                <User size={18} />
                <span className="user-name">{getUserDisplayName()}</span>
                <ChevronDown size={16} />
              </button>
              
              {showDropdown && (
                <>
                  <div 
                    className="dropdown-backdrop" 
                    onClick={() => setShowDropdown(false)}
                  />
                  <div className="user-dropdown">
                    <div className="dropdown-header">
                      <div className="user-avatar">
                        {getUserDisplayName()[0].toUpperCase()}
                      </div>
                      <div className="user-info">
                        <div className="user-name-full">{getUserDisplayName()}</div>
                        <div className="user-email">{user.email}</div>
                      </div>
                    </div>
                    <div className="dropdown-divider" />
                    <button className="dropdown-item" onClick={() => { navigate('/settings'); setShowDropdown(false); }}>
                      <Settings size={16} />
                      Settings
                    </button>
                    <button className="dropdown-item logout" onClick={handleSignOut}>
                      <LogOut size={16} />
                      Sign Out
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="user-actions">
              <button className="icon-btn" onClick={() => navigate('/login')}>
                <User size={20} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
