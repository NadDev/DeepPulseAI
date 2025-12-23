import React from 'react';
import { TrendingUp, TrendingDown, XCircle } from 'lucide-react';
import './ActivePositions.css';

const ActivePositions = ({ positions, onClosePosition }) => {
  if (!positions || positions.length === 0) {
    return (
      <div className="positions-empty">
        <p>No active positions</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };

  return (
    <div className="positions-container">
      <h3>Active Positions</h3>
      <div className="table-responsive">
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Size</th>
              <th>Entry Price</th>
              <th>Current Price</th>
              <th>Value</th>
              <th>Unrealized PnL</th>
              <th>Strategy</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => (
              <tr key={pos.id}>
                <td className="symbol-cell">
                  <span className="symbol-name">{pos.symbol}</span>
                </td>
                <td>
                  <span className={`badge ${pos.side.toLowerCase()}`}>
                    {pos.side}
                  </span>
                </td>
                <td>{pos.quantity}</td>
                <td>{formatCurrency(pos.entry_price)}</td>
                <td>{formatCurrency(pos.current_price)}</td>
                <td>{formatCurrency(pos.value)}</td>
                <td>
                  <div className={`pnl-cell ${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                    {pos.unrealized_pnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    <span>{formatCurrency(pos.unrealized_pnl)}</span>
                    <span className="pnl-percent">({pos.unrealized_pnl_percent.toFixed(2)}%)</span>
                  </div>
                </td>
                <td>{pos.strategy}</td>
                <td>
                  <button 
                    className="close-btn"
                    onClick={() => onClosePosition(pos)}
                    title="Close Position"
                  >
                    <XCircle size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ActivePositions;
