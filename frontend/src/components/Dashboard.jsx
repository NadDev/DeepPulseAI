import { useState, useEffect } from 'react'
import { cryptoAPI } from '../services/api'
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'
import RecentTrades from './RecentTrades'
import ActiveBots from './ActiveBots'
import EquityChart from './EquityChart'
import RecommendationStatsWidget from './RecommendationStatsWidget'
import './Dashboard.css'
import './DashboardGrid.css'

function Dashboard() {
  const [topCryptos, setTopCryptos] = useState([])
  const [portfolio, setPortfolio] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalValue: 0,
    totalChange: 0,
    totalCoins: 0
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [cryptos, portfolioData] = await Promise.all([
        cryptoAPI.getPrices(),
        cryptoAPI.getPortfolio()
      ])

      setTopCryptos(cryptos.slice(0, 10))
      setPortfolio(portfolioData)

      // Calculate portfolio stats from summary object
      // Backend returns: { portfolio_value, cash_balance, daily_pnl, total_pnl, ... }
      const totalValue = portfolioData.portfolio_value || 0
      const dailyPnl = portfolioData.daily_pnl || 0
      // Calculate approximate daily change %
      const previousValue = totalValue - dailyPnl
      const totalChange = previousValue !== 0 ? (dailyPnl / previousValue) * 100 : 0

      setStats({
        totalValue,
        totalChange,
        totalCoins: 0 // Summary doesn't provide holding count yet
      })
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'USD'
    }).format(value)
  }

  const formatPercent = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">Chargement...</div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <h1 className="page-title">Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon primary">
            <Wallet size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Valeur Totale</p>
            <p className="stat-value">{formatCurrency(stats.totalValue)}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className={`stat-icon ${stats.totalChange >= 0 ? 'success' : 'danger'}`}>
            {stats.totalChange >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
          </div>
          <div className="stat-content">
            <p className="stat-label">Variation Moyenne</p>
            <p className={`stat-value ${stats.totalChange >= 0 ? 'positive' : 'negative'}`}>
              {formatPercent(stats.totalChange)}
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{background: '#ed8936'}}>
            <DollarSign size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Cryptos en Portfolio</p>
            <p className="stat-value">{stats.totalCoins}</p>
          </div>
        </div>
      </div>



      <div className="dashboard-grid">
        <div className="chart-section">
          <EquityChart />
        </div>
        
        <div className="bots-section-wrapper">
          <ActiveBots />
        </div>

        <div className="recommendations-widget-section">
          <RecommendationStatsWidget onViewMore={() => {
            // This would navigate to recommendations in a full app
            console.log('Navigate to recommendations');
          }} />
        </div>
      </div>

      <RecentTrades />

      <div className="section">
        <h2 className="section-title">Top 10 Cryptomonnaies</h2>
        <div className="crypto-table">
          <div className="table-header">
            <div className="col-rank">#</div>
            <div className="col-name">Nom</div>
            <div className="col-price">Prix</div>
            <div className="col-change">24h</div>
            <div className="col-market">Market Cap</div>
          </div>
          {topCryptos.map((crypto, index) => (
            <div key={crypto.id} className="table-row">
              <div className="col-rank">{index + 1}</div>
              <div className="col-name">
                <img src={crypto.image} alt={crypto.name} className="crypto-icon" />
                <span className="crypto-name">{crypto.name}</span>
                <span className="crypto-symbol">{crypto.symbol.toUpperCase()}</span>
              </div>
              <div className="col-price">{formatCurrency(crypto.current_price)}</div>
              <div className={`col-change ${crypto.price_change_percentage_24h >= 0 ? 'positive' : 'negative'}`}>
                {formatPercent(crypto.price_change_percentage_24h)}
              </div>
              <div className="col-market">{formatCurrency(crypto.market_cap)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
