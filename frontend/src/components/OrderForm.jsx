import React, { useState } from 'react';
import { cryptoAPI as api } from '../services/api';
import './OrderForm.css';

const OrderForm = ({ onOrderComplete }) => {
  const [formData, setFormData] = useState({
    symbol: 'BTC',
    side: 'BUY',
    quantity: '',
    price: '',
    strategy: 'Manual'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.createOrder({
        ...formData,
        quantity: parseFloat(formData.quantity),
        price: parseFloat(formData.price)
      });
      
      // Reset form
      setFormData({
        symbol: 'BTC',
        side: 'BUY',
        quantity: '',
        price: '',
        strategy: 'Manual'
      });
      
      if (onOrderComplete) onOrderComplete();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to execute order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="order-form-container">
      <h3>Place Order</h3>
      <form onSubmit={handleSubmit} className="order-form">
        <div className="form-group">
          <label>Symbol</label>
          <select name="symbol" value={formData.symbol} onChange={handleChange}>
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
            <option value="SOL">SOL</option>
            <option value="BNB">BNB</option>
            <option value="XRP">XRP</option>
          </select>
        </div>

        <div className="form-group">
          <label>Side</label>
          <div className="side-selector">
            <button
              type="button"
              className={`side-btn buy ${formData.side === 'BUY' ? 'active' : ''}`}
              onClick={() => setFormData({...formData, side: 'BUY'})}
            >
              Buy
            </button>
            <button
              type="button"
              className={`side-btn sell ${formData.side === 'SELL' ? 'active' : ''}`}
              onClick={() => setFormData({...formData, side: 'SELL'})}
            >
              Sell
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Quantity</label>
          <input
            type="number"
            name="quantity"
            value={formData.quantity}
            onChange={handleChange}
            step="0.0001"
            min="0"
            required
            placeholder="0.00"
          />
        </div>

        <div className="form-group">
          <label>Price ($)</label>
          <input
            type="number"
            name="price"
            value={formData.price}
            onChange={handleChange}
            step="0.01"
            min="0"
            required
            placeholder="0.00"
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? 'Executing...' : `${formData.side} ${formData.symbol}`}
        </button>
      </form>
    </div>
  );
};

export default OrderForm;
