import { useState, useEffect } from 'react'
import { cryptoAPI } from '../services/api'
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react'
import './Portfolio.css'

function Portfolio() {
  const [portfolio, setPortfolio] = useState([])
  const [prices, setPrices] = useState({})
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [newItem, setNewItem] = useState({
    coin_id: '',
    symbol: '',
    name: '',
    amount: '',
    purchase_price: ''
  })

  useEffect(() => {
    loadPortfolio()
  }, [])

  const loadPortfolio = async () => {
    try {
      setLoading(true)
      const [portfolioData, pricesData] = await Promise.all([
        cryptoAPI.getPortfolio(),
        cryptoAPI.getPrices()
      ])

      setPortfolio(portfolioData)

      const priceMap = {}
      pricesData.forEach(crypto => {
        priceMap[crypto.id] = crypto.current_price
      })
      setPrices(priceMap)
    } catch (error) {
      console.error('Error loading portfolio:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (term) => {
    setSearchTerm(term)
    if (term.length > 2) {
      try {
        const results = await cryptoAPI.searchCrypto(term)
        setSearchResults(results.coins?.slice(0, 5) || [])
      } catch (error) {
        console.error('Search error:', error)
      }
    } else {
      setSearchResults([])
    }
  }

  const selectCoin = (coin) => {
    setNewItem({
      ...newItem,
      coin_id: coin.id,
      symbol: coin.symbol,
      name: coin.name
    })
    setSearchResults([])
    setSearchTerm('')
  }

  const handleAddItem = async (e) => {
    e.preventDefault()
    try {
      await cryptoAPI.addToPortfolio({
        ...newItem,
        user_id: 'default'
      })

      setNewItem({
        coin_id: '',
        symbol: '',
        name: '',
        amount: '',
        purchase_price: ''
      })
      setShowAddForm(false)
      loadPortfolio()
    } catch (error) {
      console.error('Error adding to portfolio:', error)
    }
  }

  const handleDeleteItem = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
      try {
        await cryptoAPI.removeFromPortfolio(id)
        loadPortfolio()
      } catch (error) {
        console.error('Error deleting item:', error)
      }
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'USD'
    }).format(value)
  }

  const calculateProfit = (item) => {
    const currentPrice = prices[item.coin_id] || 0
    const currentValue = item.amount * currentPrice
    const purchaseValue = item.amount * item.purchase_price
    const profit = currentValue - purchaseValue
    const profitPercent = ((currentValue - purchaseValue) / purchaseValue) * 100

    return { profit, profitPercent, currentValue }
  }

  if (loading) {
    return <div className="loading">Chargement...</div>
  }

  return (
    <div className="portfolio">
      <div className="portfolio-header">
        <h1 className="page-title">Mon Portfolio</h1>
        <button
          className="btn-primary"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus size={20} />
          Ajouter une crypto
        </button>
      </div>

      {showAddForm && (
        <div className="add-form">
          <h3>Ajouter une cryptomonnaie</h3>
          <form onSubmit={handleAddItem}>
            <div className="form-group">
              <label>Rechercher une crypto</label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Bitcoin, Ethereum..."
                className="form-input"
              />
              {searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.map(coin => (
                    <div
                      key={coin.id}
                      className="search-result-item"
                      onClick={() => selectCoin(coin)}
                    >
                      <img src={coin.thumb} alt={coin.name} />
                      <span>{coin.name}</span>
                      <span className="symbol">{coin.symbol}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {newItem.coin_id && (
              <>
                <div className="selected-coin">
                  Sélectionné: <strong>{newItem.name}</strong> ({newItem.symbol})
                </div>

                <div className="form-group">
                  <label>Quantité</label>
                  <input
                    type="number"
                    step="0.00000001"
                    value={newItem.amount}
                    onChange={(e) => setNewItem({...newItem, amount: e.target.value})}
                    placeholder="0.00"
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Prix d'achat (USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newItem.purchase_price}
                    onChange={(e) => setNewItem({...newItem, purchase_price: e.target.value})}
                    placeholder="0.00"
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn-primary">
                    <Save size={18} />
                    Ajouter
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setShowAddForm(false)
                      setNewItem({coin_id: '', symbol: '', name: '', amount: '', purchase_price: ''})
                    }}
                  >
                    <X size={18} />
                    Annuler
                  </button>
                </div>
              </>
            )}
          </form>
        </div>
      )}

      {portfolio.length === 0 ? (
        <div className="empty-state">
          <p>Votre portfolio est vide</p>
          <p className="empty-subtitle">Ajoutez vos premières cryptomonnaies pour commencer</p>
        </div>
      ) : (
        <div className="portfolio-table">
          <div className="table-header">
            <div>Crypto</div>
            <div>Quantité</div>
            <div>Prix d'achat</div>
            <div>Prix actuel</div>
            <div>Valeur</div>
            <div>Profit/Perte</div>
            <div>Actions</div>
          </div>
          {portfolio.map(item => {
            const { profit, profitPercent, currentValue } = calculateProfit(item)
            const currentPrice = prices[item.coin_id] || 0

            return (
              <div key={item.id} className="table-row">
                <div className="col-crypto">
                  <strong>{item.name}</strong>
                  <span className="symbol">{item.symbol?.toUpperCase()}</span>
                </div>
                <div>{item.amount}</div>
                <div>{formatCurrency(item.purchase_price)}</div>
                <div>{formatCurrency(currentPrice)}</div>
                <div className="value">{formatCurrency(currentValue)}</div>
                <div className={profit >= 0 ? 'profit positive' : 'profit negative'}>
                  {formatCurrency(profit)}
                  <span className="percent">({profitPercent.toFixed(2)}%)</span>
                </div>
                <div className="actions">
                  <button
                    className="btn-icon btn-danger"
                    onClick={() => handleDeleteItem(item.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Portfolio
