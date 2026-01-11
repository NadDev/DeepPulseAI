import { useState, useEffect } from 'react';
import { Brain, Play, Pause, Settings, TrendingUp, MessageCircle, History, Zap, AlertTriangle, Shield } from 'lucide-react';
import { aiAPI } from '../services/aiAPI';
import AIStatus from './AIStatus';
import AIAnalysis from './AIAnalysis';
import AIChat from './AIChat';
import AIDecisionHistory from './AIDecisionHistory';
import AIActiveBots from './AIActiveBots';
import './AIAgent.css';

function AIAgent() {
  const [activeTab, setActiveTab] = useState('analysis');
  const [isRunning, setIsRunning] = useState(false);
  const [mode, setMode] = useState('observation');
  const [aiStatus, setAiStatus] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // Autonomous mode state
  const [autonomousMode, setAutonomousMode] = useState(false);
  const [autonomousConfig, setAutonomousConfig] = useState(null);
  const [autonomousStats, setAutonomousStats] = useState(null);
  const [showAutonomousModal, setShowAutonomousModal] = useState(false);
  const [togglingAutonomous, setTogglingAutonomous] = useState(false);

  // Load initial data
  useEffect(() => {
    loadData();
    // Poll status every 30 seconds
    const interval = setInterval(() => {
      loadAIStatus();
      loadAutonomousConfig();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([
        loadAIStatus(),
        loadRecommendations(),
        loadAutonomousConfig(),
        loadAutonomousStats()
      ]);
    } catch (err) {
      setError(err.message || 'Failed to load AI Agent data');
      console.error('Error loading AI data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAutonomousConfig = async () => {
    try {
      const config = await aiAPI.getAutonomousConfig();
      setAutonomousConfig(config);
      setAutonomousMode(config.autonomous_mode || false);
    } catch (err) {
      console.error('Error fetching autonomous config:', err);
    }
  };

  const loadAutonomousStats = async () => {
    try {
      const stats = await aiAPI.getAutonomousStats();
      setAutonomousStats(stats);
    } catch (err) {
      console.error('Error fetching autonomous stats:', err);
    }
  };

  const loadAIStatus = async () => {
    try {
      const status = await aiAPI.getStatus();
      setAiStatus(status);
      // Use the running state from AI Agent, not controller
      setIsRunning(status.running || status.ai_agent?.running || false);
      setMode(status.ai_agent?.mode || status.controller?.mode || 'observation');
    } catch (err) {
      console.error('Error fetching AI status:', err);
    }
  };

  const loadRecommendations = async () => {
    try {
      console.log('🔍 Loading recommendations from watchlist analysis...');
      // Use the new analyze-watchlist endpoint with lower threshold to show HOLD recommendations
      const result = await aiAPI.analyzeWatchlist(10, 40);  // Lowered from 50 to 40
      console.log('✅ Watchlist analysis result:', result);
      console.log('📊 Recommendations count:', result.recommendations?.length || 0);
      console.log('📝 Recommendations data:', result.recommendations);
      
      setRecommendations(result.recommendations || []);
      console.log('✅ State updated with recommendations');
    } catch (err) {
      console.error('❌ Error analyzing watchlist:', err);
      // Fallback to old endpoint if new one fails
      try {
        const recs = await aiAPI.getRecommendations();
        console.log('📋 Fallback recommendations:', recs);
        setRecommendations(recs.recommendations || []);
      } catch (fallbackErr) {
        console.error('❌ Fallback also failed:', fallbackErr);
      }
    }
  };

  const handleToggleAI = async () => {
    try {
      setRefreshing(true);
      setError(null);
      
      // Toggle AI Agent on/off
      const result = await aiAPI.toggleAgent();
      console.log('🔄 Toggle result:', result);
      
      // Update local state
      setIsRunning(result.running);
      
      // Refresh status
      await loadAIStatus();
    } catch (err) {
      setError(err.message || 'Failed to toggle AI Agent');
      console.error('Error toggling AI:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to refresh data');
    } finally {
      setRefreshing(false);
    }
  };

  // Handle Autonomous Mode Toggle
  const handleAutonomousToggle = async () => {
    // If enabling, show confirmation modal first
    if (!autonomousMode) {
      setShowAutonomousModal(true);
      return;
    }
    
    // If disabling, do it directly
    await confirmAutonomousToggle(false);
  };

  const confirmAutonomousToggle = async (enable) => {
    try {
      setTogglingAutonomous(true);
      setShowAutonomousModal(false);
      
      const result = await aiAPI.toggleAutonomousMode(enable);
      console.log('🤖 Autonomous toggle result:', result);
      
      setAutonomousMode(result.autonomous_mode);
      await loadAutonomousConfig();
      await loadAutonomousStats();
    } catch (err) {
      setError(err.message || 'Failed to toggle autonomous mode');
      console.error('Error toggling autonomous mode:', err);
    } finally {
      setTogglingAutonomous(false);
    }
  };

  if (loading) {
    return (
      <div className="ai-agent-page">
        <div className="ai-loading">
          <div className="spinner"></div>
          <p>Loading AI Agent Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-agent-page">
      {/* Header */}
      <div className="ai-header">
        <div className="ai-title-section">
          <Brain size={32} className="ai-icon" />
          <div>
            <h1>AI Trading Agent</h1>
            <p>Autonomous market analysis and trading recommendations</p>
          </div>
        </div>

        <div className="ai-controls">
          {/* Autonomous Mode Toggle */}
          <div className={`autonomous-toggle ${autonomousMode ? 'active' : ''}`}>
            <div className="autonomous-label">
              <Shield size={16} />
              <span>Auto-Trade</span>
            </div>
            <button
              className={`toggle-switch ${autonomousMode ? 'on' : 'off'} ${togglingAutonomous ? 'loading' : ''}`}
              onClick={handleAutonomousToggle}
              disabled={togglingAutonomous || !isRunning}
              title={!isRunning ? 'Start AI Agent first' : autonomousMode ? 'Disable autonomous trading' : 'Enable autonomous trading'}
            >
              <span className="toggle-slider"></span>
            </button>
          </div>

          <div className="controls-divider"></div>

          <button
            className={`ai-btn btn-primary ${refreshing ? 'loading' : ''}`}
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh all data"
          >
            ↻
          </button>
          <button
            className={`ai-btn btn-toggle ${isRunning ? 'active' : 'inactive'}`}
            onClick={handleToggleAI}
            disabled={refreshing}
          >
            {isRunning ? <Pause size={20} /> : <Play size={20} />}
            <span>{isRunning ? 'Running' : 'Paused'}</span>
          </button>
          <button
            className="ai-btn btn-settings"
            title="Configure AI settings"
          >
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Autonomous Mode Warning Banner */}
      {autonomousMode && (
        <div className="autonomous-banner">
          <AlertTriangle size={20} />
          <span>
            <strong>Autonomous Trading Active</strong> — AI is executing trades automatically based on analysis.
            {autonomousStats && ` ${autonomousStats.trades_executed_today || 0} trades today.`}
          </span>
          <button 
            className="btn-disable"
            onClick={() => confirmAutonomousToggle(false)}
            disabled={togglingAutonomous}
          >
            Disable
          </button>
        </div>
      )}

      {/* Status and Stats */}
      <AIStatus status={aiStatus} mode={mode} isRunning={isRunning} />

      {/* Error Display */}
      {error && (
        <div className="ai-error-banner">
          <p>⚠️ {error}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="ai-tabs">
        <button
          className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          <TrendingUp size={18} />
          <span>Analysis</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageCircle size={18} />
          <span>Chat</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'decisions' ? 'active' : ''}`}
          onClick={() => setActiveTab('decisions')}
        >
          <History size={18} />
          <span>Decisions</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'bots' ? 'active' : ''}`}
          onClick={() => setActiveTab('bots')}
        >
          <Zap size={18} />
          <span>Active Bots</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="ai-tab-content">
        {activeTab === 'analysis' && (
          <AIAnalysis recommendations={recommendations} onRefresh={loadRecommendations} />
        )}
        {activeTab === 'chat' && <AIChat />}
        {activeTab === 'decisions' && <AIDecisionHistory />}
        {activeTab === 'bots' && <AIActiveBots />}
      </div>

      {/* Autonomous Mode Confirmation Modal */}
      {showAutonomousModal && (
        <div className="modal-overlay" onClick={() => setShowAutonomousModal(false)}>
          <div className="autonomous-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <AlertTriangle size={32} className="warning-icon" />
              <h2>Enable Autonomous Trading?</h2>
            </div>
            
            <div className="modal-content">
              <p className="warning-text">
                <strong>⚠️ Warning:</strong> Enabling autonomous mode will allow the AI to execute real trades 
                automatically without manual confirmation.
              </p>
              
              <div className="risk-limits">
                <h4>Risk Limits (Active):</h4>
                <ul>
                  <li>Max position size: <strong>10%</strong> of portfolio</li>
                  <li>Max open positions: <strong>15</strong></li>
                  <li>Max daily trades: <strong>30</strong></li>
                  <li>Min confidence required: <strong>65%</strong></li>
                  <li>Max drawdown: <strong>20%</strong> (auto-stop)</li>
                  <li>SL/TP: <strong>ATR-based</strong> (2x/3x ATR)</li>
                </ul>
              </div>

              <p className="confirm-text">
                You can disable autonomous mode at any time from this dashboard.
              </p>
            </div>
            
            <div className="modal-actions">
              <button 
                className="btn-cancel"
                onClick={() => setShowAutonomousModal(false)}
              >
                Cancel
              </button>
              <button 
                className="btn-confirm"
                onClick={() => confirmAutonomousToggle(true)}
                disabled={togglingAutonomous}
              >
                {togglingAutonomous ? 'Enabling...' : 'Enable Autonomous Mode'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AIAgent;
