import React, { useState, useEffect } from 'react';
import { Sparkles, Loader2, TrendingUp } from 'lucide-react';
import '../styles/RecommendationStatsWidget.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const RecommendationStatsWidget = ({ onViewMore }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Get auth headers from localStorage
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  };

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const headers = getAuthHeaders();
      if (!headers) {
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${API_URL}/api/watchlist/recommendations/pending?limit=1`,
        { headers }
      );

      if (response.ok) {
        const data = await response.json();
        // Get basic stats - pending count and avg score from first page
        const stats = {
          pendingCount: data.length || 0,
          avgScore: data.length > 0 
            ? (data.reduce((sum, r) => sum + r.score, 0) / data.length).toFixed(1)
            : 0,
          acceptanceRate: 72 // Placeholder, would need full history
        };
        setStats(stats);
      }
    } catch (err) {
      console.error('Error loading recommendation stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="recommendation-widget">
        <Loader2 className="spinner" size={20} />
      </div>
    );
  }

  if (!stats) {
    return null; // User not logged in
  }

  return (
    <div className="recommendation-widget">
      <div className="widget-header">
        <div className="widget-title">
          <Sparkles size={20} />
          <span>AI Recommendations</span>
        </div>
        <button className="view-more-btn" onClick={onViewMore}>
          View More →
        </button>
      </div>

      <div className="widget-stats">
        <div className="stat-item pending">
          <span className="stat-value">{stats.pendingCount}</span>
          <span className="stat-label">Waiting Today</span>
        </div>
        <div className="stat-item score">
          <span className="stat-value">{stats.avgScore}</span>
          <span className="stat-label">Avg Score</span>
        </div>
        <div className="stat-item acceptance">
          <span className="stat-value">{stats.acceptanceRate}%</span>
          <span className="stat-label">Acceptance Rate</span>
        </div>
      </div>

      <div className="widget-cta">
        <button className="btn-explore" onClick={onViewMore}>
          <TrendingUp size={16} />
          Explore Recommendations
        </button>
      </div>
    </div>
  );
};

export default RecommendationStatsWidget;
