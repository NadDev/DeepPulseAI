import React from 'react';
import { Wallet, TrendingUp, TrendingDown, DollarSign, Activity, Percent, Target, Award, BarChart3, Zap, LineChart } from 'lucide-react';
import './PortfolioSummary.css';

const PortfolioSummary = ({ data }) => {
  if (!data) return null;

  const { 
    portfolio_value, 
    cash_balance, 
    daily_pnl, 
    total_pnl, 
    win_rate, 
    max_drawdown,
    sharpe_ratio = 0,
    profit_factor = 0,
    average_win = 0,
    average_loss = 0,
    win_loss_ratio = 0,
    expectancy = 0
  } = data;

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(val);
  };

  const formatPercent = (val) => {
    return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
  };

  return (
    <div className="portfolio-summary-grid">
      {/* Total Value */}
      <div className="summary-card total-value">
        <div className="card-icon">
          <Wallet size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Total Portfolio Value</span>
          <span className="card-value">{formatCurrency(portfolio_value)}</span>
        </div>
      </div>

      {/* Cash Balance */}
      <div className="summary-card">
        <div className="card-icon">
          <DollarSign size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Cash Balance</span>
          <span className="card-value">{formatCurrency(cash_balance)}</span>
        </div>
      </div>

      {/* Daily PnL */}
      <div className="summary-card">
        <div className={`card-icon ${daily_pnl >= 0 ? 'positive' : 'negative'}`}>
          {daily_pnl >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
        </div>
        <div className="card-content">
          <span className="card-label">Daily PnL</span>
          <span className={`card-value ${daily_pnl >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(daily_pnl)}
          </span>
        </div>
      </div>

      {/* Total PnL */}
      <div className="summary-card">
        <div className={`card-icon ${total_pnl >= 0 ? 'positive' : 'negative'}`}>
          <Activity size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Total PnL</span>
          <span className={`card-value ${total_pnl >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(total_pnl)}
          </span>
        </div>
      </div>

      {/* Win Rate */}
      <div className="summary-card">
        <div className="card-icon">
          <Percent size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Win Rate</span>
          <span className="card-value">{win_rate.toFixed(1)}%</span>
        </div>
      </div>

      {/* Sharpe Ratio */}
      <div className="summary-card">
        <div className={`card-icon ${sharpe_ratio >= 1 ? 'positive' : sharpe_ratio >= 0 ? '' : 'negative'}`}>
          <LineChart size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Sharpe Ratio</span>
          <span className={`card-value ${sharpe_ratio >= 2 ? 'positive' : sharpe_ratio >= 1 ? '' : 'negative'}`}>
            {sharpe_ratio.toFixed(2)}
          </span>
          <span className="card-subtitle">{sharpe_ratio >= 2 ? 'Excellent' : sharpe_ratio >= 1 ? 'Good' : sharpe_ratio >= 0 ? 'Neutral' : 'Poor'}</span>
        </div>
      </div>

      {/* Max Drawdown */}
      <div className="summary-card">
        <div className="card-icon negative">
          <TrendingDown size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Max Drawdown</span>
          <span className="card-value negative">{max_drawdown.toFixed(2)}%</span>
        </div>
      </div>

      {/* Profit Factor */}
      <div className="summary-card">
        <div className="card-icon positive">
          <Target size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Profit Factor</span>
          <span className={`card-value ${profit_factor >= 2 ? 'positive' : profit_factor >= 1 ? '' : 'negative'}`}>
            {profit_factor.toFixed(2)}
          </span>
          <span className="card-subtitle">{profit_factor >= 2 ? 'Excellent' : profit_factor >= 1 ? 'Profitable' : 'Needs Improvement'}</span>
        </div>
      </div>

      {/* Average Win */}
      <div className="summary-card">
        <div className="card-icon positive">
          <Award size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Average Win</span>
          <span className="card-value positive">{formatCurrency(average_win)}</span>
        </div>
      </div>

      {/* Average Loss */}
      <div className="summary-card">
        <div className="card-icon negative">
          <TrendingDown size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Average Loss</span>
          <span className="card-value negative">{formatCurrency(average_loss)}</span>
        </div>
      </div>

      {/* Win/Loss Ratio */}
      <div className="summary-card">
        <div className="card-icon">
          <BarChart3 size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Win/Loss Ratio</span>
          <span className={`card-value ${win_loss_ratio >= 1.5 ? 'positive' : win_loss_ratio >= 1 ? '' : 'negative'}`}>
            {win_loss_ratio > 0 ? `${win_loss_ratio.toFixed(2)}:1` : 'N/A'}
          </span>
          <span className="card-subtitle">{win_loss_ratio >= 1.5 ? 'Great' : win_loss_ratio >= 1 ? 'Good' : average_loss === 0 ? 'Perfect' : 'Poor'}</span>
        </div>
      </div>

      {/* Expectancy */}
      <div className="summary-card">
        <div className={`card-icon ${expectancy >= 0 ? 'positive' : 'negative'}`}>
          <Zap size={24} />
        </div>
        <div className="card-content">
          <span className="card-label">Expectancy</span>
          <span className={`card-value ${expectancy >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(expectancy)}
          </span>
          <span className="card-subtitle">Per Trade</span>
        </div>
      </div>
    </div>
  );
};

export default PortfolioSummary;
