import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { cryptoAPI } from '../services/api'
import { ArrowLeft, TrendingUp, TrendingDown } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import './CryptoDetail.css'

function CryptoDetail() {
  const { coinId } = useParams()
  const navigate = useNavigate()
  const [crypto, setCrypto] = useState(null)
  const [chartData, setChartData] = useState([])
  const [chartPeriod, setChartPeriod] = useState('7')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCryptoDetail()
  }, [coinId, chartPeriod])

  const loadCryptoDetail = async () => {
    try {
      setLoading(true)
      const [detailData, chartDataRaw] = await Promise.all([
        cryptoAPI.getCryptoDetails(coinId),
        cryptoAPI.getChartData(coinId, chartPeriod)
      ])

      setCrypto(detailData)

      const formattedChartData = chartDataRaw.prices.map(([timestamp, price]) => ({
        date: new Date(timestamp).toLocaleDateString('fr-FR'),
        price: price
      }))
      setChartData(formattedChartData)
    } catch (error) {
      console.error('Error loading crypto detail:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 8
    }).format(value)
  }

  const formatNumber = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      notation: 'compact',
      compactDisplay: 'short'
    }).format(value)
  }

  if (loading) {
    return <div className="loading">Chargement...</div>
  }

  if (!crypto) {
    return <div className="error">Cryptomonnaie non trouvée</div>
  }

  const priceChange24h = crypto.market_data?.price_change_percentage_24h || 0
  const isPositive = priceChange24h >= 0

  return (
    <div className="crypto-detail">
      <button className="back-button" onClick={() => navigate(-1)}>
        <ArrowLeft size={20} />
        Retour
      </button>

      <div className="detail-header">
        <div className="crypto-info">
          <img src={crypto.image?.large} alt={crypto.name} className="crypto-image" />
          <div>
            <h1>{crypto.name}</h1>
            <span className="crypto-symbol">{crypto.symbol?.toUpperCase()}</span>
          </div>
        </div>

        <div className="price-section">
          <div className="current-price">
            {formatCurrency(crypto.market_data?.current_price?.usd || 0)}
          </div>
          <div className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
            {isPositive ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            {Math.abs(priceChange24h).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="chart-section">
        <div className="chart-header">
          <h2>Graphique des prix</h2>
          <div className="chart-period-selector">
            {['1', '7', '30', '90', '365'].map(period => (
              <button
                key={period}
                className={chartPeriod === period ? 'active' : ''}
                onClick={() => setChartPeriod(period)}
              >
                {period === '1' ? '24h' : period === '7' ? '7j' : period === '30' ? '1m' : period === '90' ? '3m' : '1a'}
              </button>
            ))}
          </div>
        </div>

        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              stroke="#a0aec0"
              tick={{fontSize: 12}}
            />
            <YAxis
              stroke="#a0aec0"
              tick={{fontSize: 12}}
              tickFormatter={(value) => `$${formatNumber(value)}`}
            />
            <Tooltip
              contentStyle={{
                background: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px'
              }}
              formatter={(value) => [formatCurrency(value), 'Prix']}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#667eea"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="stats-grid">
        <div className="stat-box">
          <div className="stat-label">Market Cap</div>
          <div className="stat-value">
            {formatCurrency(crypto.market_data?.market_cap?.usd || 0)}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Volume 24h</div>
          <div className="stat-value">
            {formatCurrency(crypto.market_data?.total_volume?.usd || 0)}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Plus Haut 24h</div>
          <div className="stat-value">
            {formatCurrency(crypto.market_data?.high_24h?.usd || 0)}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Plus Bas 24h</div>
          <div className="stat-value">
            {formatCurrency(crypto.market_data?.low_24h?.usd || 0)}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Plus Haut Historique</div>
          <div className="stat-value">
            {formatCurrency(crypto.market_data?.ath?.usd || 0)}
          </div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Offre Circulante</div>
          <div className="stat-value">
            {formatNumber(crypto.market_data?.circulating_supply || 0)}
          </div>
        </div>
      </div>

      {crypto.description?.en && (
        <div className="description-section">
          <h2>À propos de {crypto.name}</h2>
          <div
            className="description-content"
            dangerouslySetInnerHTML={{ __html: crypto.description.en }}
          />
        </div>
      )}
    </div>
  )
}

export default CryptoDetail
