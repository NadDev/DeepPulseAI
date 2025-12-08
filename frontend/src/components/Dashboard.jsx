import { useState, useEffect } from 'react'
import { cryptoAPI } from '../services/api'
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'
import './Dashboard.css'

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

      // Calculate portfolio stats
      let totalValue = 0
      let totalChange = 0

      portfolioData.forEach(item => {
        const crypto = cryptos.find(c => c.id === item.coin_id)
        if (crypto) {
          const currentValue = item.amount * crypto.current_price
          const purchaseValue = item.amount * item.purchase_price
          totalValue += currentValue
          totalChange += ((currentValue - purchaseValue) / purchaseValue) * 100
        }
      })

      setStats({
        totalValue,
        totalChange: portfolioData.length > 0 ? totalChange / portfolioData.length : 0,
        totalCoins: portfolioData.length
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
          <div className="stat-icon" style={{background: '#667eea'}}>
            <Wallet size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Valeur Totale</p>
            <p className="stat-value">{formatCurrency(stats.totalValue)}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{background: stats.totalChange >= 0 ? '#48bb78' : '#f56565'}}>
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
