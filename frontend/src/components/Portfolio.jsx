import React, { useState, useEffect } from 'react';
import { cryptoAPI as api } from '../services/api';
import PortfolioSummary from './PortfolioSummary';
import ActivePositions from './ActivePositions';
import TradeHistory from './TradeHistory';
import './Portfolio.css';

function Portfolio() {
  const [summary, setSummary] = useState(null);
  const [positions, setPositions] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [summaryData, positionsData] = await Promise.all([
        api.getPortfolioSummary(),
        api.getPositions()
      ]);

      setSummary(summaryData);
      setPositions(positionsData);
      // Trigger TradeHistory refresh
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error('Error loading portfolio data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClosePosition = async (position) => {
    if (window.confirm(`Close position for ${position.symbol}?`)) {
      try {
        await api.createOrder({
          symbol: position.symbol,
          side: position.side === 'BUY' ? 'SELL' : 'BUY',
          quantity: position.quantity,
          price: position.current_price, // Market close
          strategy: 'Manual Close'
        });
        loadData(); // Refresh
      } catch (error) {
        console.error('Error closing position:', error);
        alert('Failed to close position');
      }
    }
  };

  if (loading && !summary) {
    return <div className="portfolio-loading">Loading portfolio data...</div>;
  }

  return (
    <div className="portfolio-dashboard">
      <div className="portfolio-header">
        <h2>Portfolio Management</h2>
        <span className="last-updated">
          Last updated: {new Date().toLocaleTimeString()}
        </span>
      </div>

      <PortfolioSummary data={summary} />

      <div className="portfolio-content-grid">
        <div className="main-column">
          <ActivePositions 
            positions={positions} 
            onClosePosition={handleClosePosition} 
          />
          <TradeHistory refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  );
}

export default Portfolio;