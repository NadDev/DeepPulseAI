import React, { useState } from 'react';
import { TrendingUp, RefreshCw, AlertTriangle, Check, Loader2 } from 'lucide-react';
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
        message: '✅ Mise à jour des recommandations lancée en arrière-plan'
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
        message: '✅ Mise à jour des données de marché lancée en arrière-plan'
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
        {/* Header */}
        <div className="markets-header">
          <div className="header-content">
            <TrendingUp size={32} />
            <div>
              <h1>Markets & Data</h1>
              <p>Gérez votre watchlist et mettez à jour les données de marché</p>
            </div>
          </div>
        </div>

        {/* Update Controls */}
        <div className="update-controls">
          <div className="controls-info">
            <RefreshCw size={20} />
            <div>
              <h3>Mise à jour des données</h3>
              <p>Lancez manuellement les mises à jour des recommandations et des données de marché</p>
            </div>
          </div>
          
          <div className="controls-buttons">
            <button
              className="btn-primary"
              onClick={handleUpdateRecommendations}
              disabled={loadingUpdates}
            >
              {loadingUpdates ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <RefreshCw size={16} />
              )}
              Maj Recommandations
            </button>
            
            <button
              className="btn-primary btn-secondary"
              onClick={handleUpdateMarketData}
              disabled={loadingUpdates}
            >
              {loadingUpdates ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <RefreshCw size={16} />
              )}
              Mise à jour Marché
            </button>
          </div>
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

        {/* Watchlist Manager */}
        <WatchlistManager />
      </div>
    </div>
  );
}
