import { useState, useEffect } from 'react';
import { cryptoAPI } from '../services/api';
import { Bot, Play, Pause, AlertTriangle } from 'lucide-react';
import './ActiveBots.css';

function ActiveBots() {
  const [bots, setBots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBots = async () => {
      try {
        const data = await cryptoAPI.getBots();
        setBots(data.bots || []);
      } catch (error) {
        console.error("Error fetching bots:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchBots();
  }, []);

  if (loading) return <div className="bots-loading">Chargement des bots...</div>;

  return (
    <div className="bots-section">
      <div className="section-header">
        <h2>Bots Actifs</h2>
        <Bot size={20} className="header-icon" />
      </div>

      <div className="bots-list">
        {bots.length > 0 ? (
          bots.map((bot) => (
            <div key={bot.id} className={`bot-card ${bot.status === 'RUNNING' ? 'live' : 'stopped'}`}>
              <div className="bot-header">
                <div className="bot-info">
                  <h3>{bot.name}</h3>
                  <span className="strategy-tag">{bot.strategy}</span>
                </div>
                <div className={`status-badge ${bot.status === 'RUNNING' ? 'active' : 'inactive'}`}>
                  {bot.status === 'RUNNING' ? <Play size={12} /> : <Pause size={12} />}
                  {bot.status === 'RUNNING' ? 'RUNNING' : 'STOPPED'}
                </div>
              </div>
              
              <div className="bot-stats">
                <div className="stat">
                  <span className="label">Win Rate</span>
                  <span className="value">{(bot.win_rate || 0).toFixed(1)}%</span>
                </div>
                <div className="stat">
                  <span className="label">Total PnL</span>
                  <span className={`value ${(bot.total_pnl || 0) >= 0 ? 'green' : 'red'}`}>
                    ${(bot.total_pnl || 0).toFixed(2)}
                  </span>
                </div>
                <div className="stat">
                  <span className="label">Trades</span>
                  <span className="value">{bot.total_trades || 0}</span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="no-bots">
            <AlertTriangle size={24} />
            <p>Aucun bot configuré</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActiveBots;
