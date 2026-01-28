import React, { useState, useEffect } from 'react';
import { 
  ThumbsUp, 
  ThumbsDown, 
  X, 
  Sparkles, 
  TrendingUp,
  Loader2
} from 'lucide-react';
import { supabase } from '../services/supabaseClient';
import '../styles/WatchlistRecommendations.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const WatchlistRecommendations = ({ onRecommendationAccepted }) => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [dismissedIds, setDismissedIds] = useState(new Set());

  // Get auth headers
  const getAuthHeaders = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) throw new Error('Not authenticated');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    };
  };

  // Load recommendations
  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const headers = await getAuthHeaders();
      
      const response = await fetch(
        `${API_URL}/api/watchlist/recommendations/pending?limit=50`,
        { headers }
      );

      if (!response.ok) {
        if (response.status === 401) throw new Error('Please log in to see recommendations');
        throw new Error(`Failed to load recommendations: ${response.status}`);
      }

      const data = await response.json();
      setRecommendations(data.recommendations || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading recommendations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
    const interval = setInterval(loadRecommendations, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const handleAccept = async (recommendationId, symbol) => {
    try {
      setProcessing(recommendationId);
      const headers = await getAuthHeaders();

      const response = await fetch(
        `${API_URL}/api/watchlist/recommendations/${recommendationId}/accept`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ add_to_watchlist: true })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to accept recommendation: ${response.status}`);
      }

      // Remove from list
      setRecommendations(recs => recs.filter(r => r.id !== recommendationId));
      
      // Show success feedback
      if (onRecommendationAccepted) {
        onRecommendationAccepted(symbol);
      }
    } catch (err) {
      console.error('Error accepting recommendation:', err);
      alert(`Failed to accept recommendation: ${err.message}`);
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (recommendationId) => {
    try {
      setProcessing(recommendationId);
      const headers = await getAuthHeaders();

      const response = await fetch(
        `${API_URL}/api/watchlist/recommendations/${recommendationId}/reject`,
        {
          method: 'POST',
          headers
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to reject recommendation: ${response.status}`);
      }

      // Remove from list
      setRecommendations(recs => recs.filter(r => r.id !== recommendationId));
    } catch (err) {
      console.error('Error rejecting recommendation:', err);
      alert(`Failed to reject recommendation: ${err.message}`);
    } finally {
      setProcessing(null);
    }
  };

  const handleDismiss = (recommendationId) => {
    const newDismissed = new Set(dismissedIds);
    newDismissed.add(recommendationId);
    setDismissedIds(newDismissed);
  };

  // Filter out dismissed
  const visibleRecommendations = recommendations.filter(
    rec => !dismissedIds.has(rec.id)
  );

  if (loading) {
    return (
      <div className="recommendations-container">
        <div className="loading-spinner">
          <Loader2 className="spinner-icon" />
          <p>Loading recommendations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendations-container">
        <div className="error-message">
          <p>⚠️ {error}</p>
          <button onClick={loadRecommendations} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (visibleRecommendations.length === 0) {
    return (
      <div className="recommendations-container">
        <div className="empty-state">
          <Sparkles size={48} className="empty-icon" />
          <p>No pending recommendations today</p>
          <small>Check back tomorrow for new opportunities</small>
        </div>
      </div>
    );
  }

  return (
    <div className="recommendations-container">
      <div className="recommendations-header">
        <h2>
          <Sparkles size={20} />
          Daily Recommendations
        </h2>
        <span className="badge">{visibleRecommendations.length}</span>
      </div>

      <div className="recommendations-grid">
        {visibleRecommendations.map((rec) => (
          <div 
            key={rec.id} 
            className={`recommendation-card ${rec.action.toLowerCase()} animate-slide-in`}
          >
            <button 
              className="dismiss-btn"
              onClick={() => handleDismiss(rec.id)}
              title="Dismiss"
            >
              <X size={16} />
            </button>

            <div className="card-header">
              <div className="symbol-info">
                <h3 className="symbol">{rec.symbol}</h3>
                <span className={`action-badge ${rec.action.toLowerCase()}`}>
                  {rec.action === 'ADD' ? '⬆️ Add' : '⬇️ Remove'}
                </span>
              </div>
              <div className="score-section">
                <div className="score-value">{rec.score.toFixed(1)}</div>
                <div className="score-bar">
                  <div 
                    className="score-fill"
                    style={{ width: `${rec.score}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="card-body">
              {rec.current_price && (
                <div className="price-row">
                  <span className="label">Current Price:</span>
                  <span className="value">${rec.current_price.toFixed(2)}</span>
                </div>
              )}

              {rec.price_change_7d !== undefined && (
                <div className="price-row">
                  <span className="label">7d Change:</span>
                  <span className={`value ${rec.price_change_7d >= 0 ? 'positive' : 'negative'}`}>
                    {rec.price_change_7d >= 0 ? '📈 ' : '📉 '}
                    {rec.price_change_7d > 0 ? '+' : ''}{rec.price_change_7d.toFixed(1)}%
                  </span>
                </div>
              )}

              <div className="components-row">
                <div className="component">
                  <label>Momentum</label>
                  <div className="mini-bar">
                    <div 
                      className="mini-fill"
                      style={{ width: `${rec.components?.momentum || 0}%` }}
                    />
                  </div>
                  <span>{rec.components?.momentum?.toFixed(0) || 0}</span>
                </div>
                <div className="component">
                  <label>Volume</label>
                  <div className="mini-bar">
                    <div 
                      className="mini-fill"
                      style={{ width: `${rec.components?.volume || 0}%` }}
                    />
                  </div>
                  <span>{rec.components?.volume?.toFixed(0) || 0}</span>
                </div>
                <div className="component">
                  <label>Volatility</label>
                  <div className="mini-bar">
                    <div 
                      className="mini-fill"
                      style={{ width: `${rec.components?.volatility || 0}%` }}
                    />
                  </div>
                  <span>{rec.components?.volatility?.toFixed(0) || 0}</span>
                </div>
                <div className="component">
                  <label>RSI</label>
                  <div className="mini-bar">
                    <div 
                      className="mini-fill"
                      style={{ width: `${rec.components?.rsi || 0}%` }}
                    />
                  </div>
                  <span>{rec.components?.rsi?.toFixed(0) || 0}</span>
                </div>
              </div>

              {rec.reasoning && (
                <div className="reasoning">
                  <strong>💡 Analysis:</strong>
                  <p>{rec.reasoning}</p>
                </div>
              )}
            </div>

            <div className="card-actions">
              <button
                className="action-btn accept-btn"
                onClick={() => handleAccept(rec.id, rec.symbol)}
                disabled={processing === rec.id}
              >
                {processing === rec.id ? (
                  <>
                    <Loader2 size={16} className="spinner" />
                    Processing...
                  </>
                ) : (
                  <>
                    <ThumbsUp size={16} />
                    Add to Watchlist
                  </>
                )}
              </button>
              <button
                className="action-btn reject-btn"
                onClick={() => handleReject(rec.id)}
                disabled={processing === rec.id}
              >
                {processing === rec.id ? (
                  <>
                    <Loader2 size={16} className="spinner" />
                    Processing...
                  </>
                ) : (
                  <>
                    <ThumbsDown size={16} />
                    Reject
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WatchlistRecommendations;
