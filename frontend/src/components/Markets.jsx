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
      const url = `${API_URL}/api/admin/bootstrap?cryptos=50&days=730&force=true`;

      console.log('🚀 Calling bootstrap:', url);
      console.log('🔐 Headers:', headers);

      const response = await fetch(url, {
        method: 'POST',
        headers
      });

      console.log('📊 Response status:', response.status);
      const data = await response.json();
      console.log('📦 Response data:', data);

      if (!response.ok) {
        throw new Error(`Failed to update recommendations: ${response.status} - ${data.detail || ''}`);
      }

      // After bootstrap, trigger recommendation generation
      console.log('🔄 Triggering recommendation generation after bootstrap...');
      const recGenResponse = await fetch(`${API_URL}/api/admin/generate-recommendations`, {
        method: 'POST',
        headers
      });
      
      console.log('📊 Recommendation generation response:', recGenResponse.status);

      setUpdateStatus({
        type: 'success',
        message: '✅ Recommendations update started'
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } catch (err) {
      console.error('❌ Bootstrap error:', err);
      setUpdateStatus({
        type: 'error',
        message: `❌ Error: ${err.message}`
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
      const url = `${API_URL}/api/admin/bootstrap?cryptos=200&days=730&force=true`;

      console.log('🚀 Calling market data update:', url);
      console.log('🔐 Headers:', headers);

      const response = await fetch(url, {
        method: 'POST',
        headers
      });

      console.log('📊 Response status:', response.status);
      const data = await response.json();
      console.log('📦 Response data:', data);

      if (!response.ok) {
        throw new Error(`Failed to update market data: ${response.status} - ${data.detail || ''}`);
      }

      // After bootstrap, trigger recommendation generation
      console.log('🔄 Triggering recommendation generation after market data update...');
      const recGenResponse = await fetch(`${API_URL}/api/admin/generate-recommendations`, {
        method: 'POST',
        headers
      });
      
      console.log('📊 Recommendation generation response:', recGenResponse.status);

      setUpdateStatus({
        type: 'success',
        message: '✅ Market data update started'
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } catch (err) {
      console.error('❌ Market update error:', err);
      setUpdateStatus({
        type: 'error',
        message: `❌ Error: ${err.message}`
      });
      setTimeout(() => setUpdateStatus(null), 5000);
    } finally {
      setLoadingUpdates(false);
    }
  };

  return (
    <div className="markets-page">
      <div className="markets-container">
        <div style={{ marginBottom: '20px' }}>
          <h2 style={{ color: '#e2e8f0', fontSize: '24px', margin: 0 }}>Markets & Data</h2>
        </div>

        {/* Watchlist Manager with update buttons passed as props */}
        <WatchlistManager 
          updateButtons={
            <div className="market-update-buttons">
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
          }
        />

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
  );
}
