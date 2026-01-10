import React from 'react';
import './TradeHistory.css';

const TradeHistory = ({ trades }) => {
  if (!trades || trades.length === 0) {
    return (
      <div className="history-empty">
        <p>No trade history</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="history-container">
      <h3>Trade History</h3>
      <div className="table-responsive">
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Symbol</th>
              <th>Side</th>
              <th>Price</th>
              <th>Size</th>
              <th>Status</th>
              <th>PnL</th>
              <th>Strategy</th>
              <th>Bot Name</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td>{formatDate(trade.entry_time)}</td>
                <td className="symbol-cell">{trade.symbol}</td>
                <td>
                  <span className={`badge ${trade.side.toLowerCase()}`}>
                    {trade.side}
                  </span>
                </td>
                <td>{formatCurrency(trade.status === 'CLOSED' && trade.exit_price ? trade.exit_price : trade.entry_price)}</td>
                <td>{trade.quantity}</td>
                <td>
                  <span className={`status-badge ${trade.status.toLowerCase()}`}>
                    {trade.status}
                  </span>
                </td>
                <td>
                  {trade.pnl ? (
                    <span className={trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>
                      {formatCurrency(trade.pnl)}
                    </span>
                  ) : '-'}
                </td>
                <td>{trade.strategy}</td>
                <td>{trade.bot_name || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradeHistory;
