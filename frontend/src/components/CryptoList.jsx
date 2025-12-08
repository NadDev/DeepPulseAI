import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { cryptoAPI } from '../services/api'
import { Search, TrendingUp, TrendingDown } from 'lucide-react'
import './CryptoList.css'

function CryptoList() {
  const [cryptos, setCryptos] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadCryptos()
  }, [])

  const loadCryptos = async () => {
    try {
      setLoading(true)
      const data = await cryptoAPI.getPrices()
      setCryptos(data)
    } catch (error) {
      console.error('Error loading cryptos:', error)
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

  const formatNumber = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      notation: 'compact',
      compactDisplay: 'short'
    }).format(value)
  }

  const filteredCryptos = cryptos.filter(crypto =>
    crypto.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    crypto.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return <div className="loading">Chargement...</div>
  }

  return (
    <div className="crypto-list">
      <h1 className="page-title">Marchés des Cryptomonnaies</h1>

      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="Rechercher une cryptomonnaie..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="markets-table">
        <div className="table-header">
          <div className="col-rank">#</div>
          <div className="col-name">Nom</div>
          <div className="col-price">Prix</div>
          <div className="col-change-1h">1h %</div>
          <div className="col-change-24h">24h %</div>
          <div className="col-change-7d">7j %</div>
          <div className="col-volume">Volume 24h</div>
          <div className="col-market-cap">Market Cap</div>
        </div>

        {filteredCryptos.map((crypto) => (
          <Link
            key={crypto.id}
            to={`/crypto/${crypto.id}`}
            className="table-row"
          >
            <div className="col-rank">{crypto.market_cap_rank}</div>
            <div className="col-name">
              <img src={crypto.image} alt={crypto.name} />
              <span className="name">{crypto.name}</span>
              <span className="symbol">{crypto.symbol.toUpperCase()}</span>
            </div>
            <div className="col-price">{formatCurrency(crypto.current_price)}</div>
            <div className={`col-change-1h ${crypto.price_change_percentage_1h_in_currency >= 0 ? 'positive' : 'negative'}`}>
              {crypto.price_change_percentage_1h_in_currency >= 0 ? (
                <TrendingUp size={14} />
              ) : (
                <TrendingDown size={14} />
              )}
              {Math.abs(crypto.price_change_percentage_1h_in_currency || 0).toFixed(2)}%
            </div>
            <div className={`col-change-24h ${crypto.price_change_percentage_24h >= 0 ? 'positive' : 'negative'}`}>
              {crypto.price_change_percentage_24h >= 0 ? (
                <TrendingUp size={14} />
              ) : (
                <TrendingDown size={14} />
              )}
              {Math.abs(crypto.price_change_percentage_24h).toFixed(2)}%
            </div>
            <div className={`col-change-7d ${crypto.price_change_percentage_7d_in_currency >= 0 ? 'positive' : 'negative'}`}>
              {crypto.price_change_percentage_7d_in_currency >= 0 ? (
                <TrendingUp size={14} />
              ) : (
                <TrendingDown size={14} />
              )}
              {Math.abs(crypto.price_change_percentage_7d_in_currency || 0).toFixed(2)}%
            </div>
            <div className="col-volume">{formatNumber(crypto.total_volume)}</div>
            <div className="col-market-cap">{formatNumber(crypto.market_cap)}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default CryptoList
