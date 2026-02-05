import React, { useState } from 'react';
import { Sparkles, AlertTriangle, Check, Loader2 } from 'lucide-react';
import WatchlistManager from './WatchlistManager';
import '../styles/Markets.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Markets() {
  const [loadingUpdates, setLoadingUpdates] = useState(false);
  const [updateStatus, setUpdateStatus] = useState(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('Not authenticated');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  };

  // Update recommendations
  const handleUpdateRecommendations = async () => {
    try {
      setLoadingUpdates(true);
      setUpdateStatus(null);
      const headers = getAuthHeaders();

      const response = await fetch(
        `${API_URL}/api/admin/bootstrap?cryptos=50&days=730&force=false`,
        {
          method: 'POST',
          headers
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update recommendations: ${response.status}`);
      }

      const data = await response.json();
      setUpdateStatus({
        type: 'success',
        message: '✅ Recommendations update started'
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } catch (err) {
      setUpdateStatus({
        type: 'error',
        message: `❌ Erreur: ${err.message}`
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } finally {
      setLoadingUpdates(false);
    }
  };

  // Update market data
  const handleUpdateMarketData = async () => {
    try {
      setLoadingUpdates(true);
      setUpdateStatus(null);
      const headers = getAuthHeaders();

      const response = await fetch(
        `${API_URL}/api/admin/bootstrap?cryptos=200&days=730&force=false`,
        {
          method: 'POST',
          headers
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update market data: ${response.status}`);
      }

      const data = await response.json();
      setUpdateStatus({
        type: 'success',
        message: '✅ Market data update started'
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } catch (err) {
      setUpdateStatus({
        type: 'error',
        message: `❌ Erreur: ${err.message}`
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } finally {
      setLoadingUpdates(false);
    }
  };

  return (
    <div className="markets-page">
      <div className="markets-container">
        {/* Watchlist Manager with inline update buttons */}
        <div className="watchlist-wrapper">
          <WatchlistManager />
          
          {/* Update buttons aligned with Sync avec AI style */}
          <div className="market-update-controls">
            <button
              className="btn-sync"
              onClick={handleUpdateRecommendations}
              disabled={loadingUpdates}
              title="Update recommendations data (50 cryptos)"
            >
              {loadingUpdates ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Sparkles size={16} />
              )}
              Update Recommendations
            </button>
            
            <button
              className="btn-sync"
              onClick={handleUpdateMarketData}
              disabled={loadingUpdates}
              title="Refresh market data (200 cryptos)"
            >
              {loadingUpdates ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Sparkles size={16} />
              )}
              Refresh Market Data
            </button>
          </div>

          {/* Status Messages */}
          {updateStatus && (
            <div className={`alert alert-${updateStatus.type}`}>
              {updateStatus.type === 'success' ? (
                <Check size={16} />
              ) : (
                <AlertTriangle size={16} />
              )}
              {updateStatus.message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
