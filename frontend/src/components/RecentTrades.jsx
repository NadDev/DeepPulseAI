import { useState, useEffect } from 'react';
import { cryptoAPI } from '../services/api';
import { ArrowUpRight, ArrowDownRight, Clock } from 'lucide-react';
import './RecentTrades.css';

function RecentTrades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const data = await cryptoAPI.getTrades(10);
        setTrades(data);
      } catch (error) {
        console.error("Error fetching trades:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrades();
    const interval = setInterval(fetchTrades, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price);
  };

  const formatPnL = (pnl, percent) => {
    if (pnl === null || pnl === undefined) return '-';
    const isPositive = pnl >= 0;
    return (
      <span className={isPositive ? 'text-green' : 'text-red'}>
        {isPositive ? '+' : ''}{formatPrice(pnl)} ({isPositive ? '+' : ''}{percent.toFixed(2)}%)
      </span>
    );
  };

  if (loading) return <div className="trades-loading">Chargement des trades...</div>;

  return (
    <div className="trades-section">
      <div className="section-header">
        <h2>Derniers Trades</h2>
        <Clock size={18} className="header-icon" />
      </div>
      
      <div className="trades-table-container">
        <table className="trades-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Paire</th>
              <th>Type</th>
              <th>Prix Entrée</th>
              <th>Prix Sortie</th>
              <th>P&L</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {trades.length > 0 ? (
              trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{formatDate(trade.created_at)}</td>
                  <td className="font-bold">{trade.symbol}</td>
                  <td>
                    <span className={`badge ${trade.side.toLowerCase()}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td>{formatPrice(trade.entry_price)}</td>
                  <td>{trade.exit_price ? formatPrice(trade.exit_price) : '-'}</td>
                  <td>{formatPnL(trade.pnl, trade.pnl_percent)}</td>
                  <td>
                    <span className={`status-dot ${trade.status.toLowerCase()}`}></span>
                    {trade.status}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colspan="7" className="no-trades">Aucun trade récent</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RecentTrades;
