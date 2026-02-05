import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Calendar, Target, Brain, Save, RefreshCw, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './LongTermSettings.css';

/**
 * LongTermSettings Component
 * Configure long-term DCA accumulation strategy (OPT-IN)
 * 
 * Features:
 * - Enable/Disable LT strategy (OPT-IN, disabled by default)
 * - Allocation slider (0-20% max)
 * - Asset selection and weighting
 * - DCA frequency and scheduling
 * - Confidence thresholds (score, ML, Fear index)
 */
export default function LongTermSettings() {
  const { session } = useAuth();
  const [allocation, setAllocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchAllocation();
  }, []);

  const getAuthToken = () => localStorage.getItem('access_token');

  const fetchAllocation = async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        setMessage({ type: 'error', text: 'Non authentifié - veuillez vous reconnecter' });
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/long-term/allocation`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setAllocation(data);
      } else if (response.status === 401) {
        setMessage({ type: 'error', text: 'Session expirée' });
      }
    } catch (error) {
      console.error('Error fetching LT allocation:', error);
      setMessage({ type: 'error', text: 'Erreur lors du chargement' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const token = getAuthToken();
      if (!token) {
        setMessage({ type: 'error', text: 'Non authentifié' });
        setSaving(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/long-term/allocation`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(allocation)
      });

      if (response.ok) {
        setMessage({ type: 'success', text: '✅ Configuration sauvegardée' });
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Erreur de sauvegarde' });
      }
    } catch (error) {
      console.error('Error saving LT allocation:', error);
      setMessage({ type: 'error', text: 'Erreur réseau' });
    } finally {
      setSaving(false);
    }
  };

  const handleAllocationChange = (value) => {
    const ltPct = parseFloat(value);
    setAllocation({
      ...allocation,
      long_term_pct: ltPct,
      day_trading_pct: 100 - ltPct
    });
  };

  if (loading) {
    return (
      <div className="long-term-settings loading">
        <RefreshCw className="spin" /> Chargement...
      </div>
    );
  }

  return (
    <div className="long-term-settings">
      <div className="header">
        <TrendingUp size={32} style={{color: '#10b981'}} />
        <h2>Stratégie Long Terme</h2>
        <p className="subtitle">Accumulation DCA ultra-sélective (OPT-IN only)</p>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* OPT-IN Toggle */}
      <div className="section">
        <div className="section-header">
          <h3>⚡ Activation (OPT-IN)</h3>
          <label className="toggle">
            <input
              type="checkbox"
              checked={allocation?.lt_enabled || false}
              onChange={(e) => setAllocation({...allocation, lt_enabled: e.target.checked})}
            />
            <span className="slider"></span>
            <span className="label">{allocation?.lt_enabled ? 'ACTIVÉ' : 'DÉSACTIVÉ'}</span>
          </label>
        </div>
        <div className="info-box">
          <Info size={16} />
          <p>La stratégie long-terme est désactivée par défaut. Activez-la uniquement si vous comprenez la stratégie (DCA sur 6-12 mois, sélection ultra-stricte score 80/100).</p>
        </div>
      </div>

      {/* Allocation Slider */}
      <div className="section">
        <div className="section-header">
          <h3><DollarSign size={20} /> Allocation Capital</h3>
          <span className="value">{allocation?.long_term_pct || 0}%</span>
        </div>
        <div className="slider-container">
          <input
            type="range"
            min="0"
            max="20"
            step="1"
            value={allocation?.long_term_pct || 0}
            onChange={(e) => handleAllocationChange(e.target.value)}
            disabled={!allocation?.lt_enabled}
          />
          <div className="slider-labels">
            <span>0% (aucun)</span>
            <span className="recommended">10% (recommandé)</span>
            <span>20% (max)</span>
          </div>
        </div>
        <div className="breakdown">
          <div className="pocket">
            <span>Day Trading</span>
            <strong>{allocation?.day_trading_pct || 100}%</strong>
          </div>
          <div className="pocket lt">
            <span>Long Terme</span>
            <strong>{allocation?.long_term_pct || 0}%</strong>
          </div>
        </div>
      </div>

      {/* DCA Frequency */}
      <div className="section">
        <h3><Calendar size={20} /> Fréquence DCA</h3>
        <div className="frequency-options">
          {['daily', 'weekly', 'monthly'].map(freq => (
            <label key={freq} className={`frequency-card ${allocation?.lt_dca_frequency === freq ? 'selected' : ''}`}>
              <input
                type="radio"
                name="frequency"
                value={freq}
                checked={allocation?.lt_dca_frequency === freq}
                onChange={(e) => setAllocation({...allocation, lt_dca_frequency: e.target.value})}
                disabled={!allocation?.lt_enabled}
              />
              <span>{freq === 'daily' ? 'Quotidien' : freq === 'weekly' ? 'Hebdomadaire' : 'Mensuel'}</span>
            </label>
          ))}
        </div>
        {allocation?.lt_dca_frequency === 'weekly' && (
          <div className="day-selector">
            <label>Jour de la semaine:</label>
            <select 
              value={allocation?.lt_dca_day || 1}
              onChange={(e) => setAllocation({...allocation, lt_dca_day: parseInt(e.target.value)})}
              disabled={!allocation?.lt_enabled}
            >
              <option value={1}>Lundi</option>
              <option value={2}>Mardi</option>
              <option value={3}>Mercredi</option>
              <option value={4}>Jeudi</option>
              <option value={5}>Vendredi</option>
              <option value={6}>Samedi</option>
              <option value={0}>Dimanche</option>
            </select>
          </div>
        )}
      </div>

      {/* Confidence Thresholds */}
      <div className="section">
        <h3><Target size={20} /> Seuils de Confiance</h3>
        <div className="threshold-grid">
          <div className="threshold-item">
            <label>Score minimum (0-100)</label>
            <input
              type="number"
              min="60"
              max="100"
              value={allocation?.lt_min_confidence_score || 80}
              onChange={(e) => setAllocation({...allocation, lt_min_confidence_score: parseInt(e.target.value)})}
              disabled={!allocation?.lt_enabled}
            />
            <span className="hint">Défaut: 80 (ultra-sélectif)</span>
          </div>
          <div className="threshold-item">
            <label><Brain size={16} /> ML 7d minimum (%)</label>
            <input
              type="number"
              min="50"
              max="100"
              value={allocation?.lt_require_ml_7d_confidence || 70}
              onChange={(e) => setAllocation({...allocation, lt_require_ml_7d_confidence: parseInt(e.target.value)})}
              disabled={!allocation?.lt_enabled}
            />
            <span className="hint">Défaut: 70% BULLISH requis</span>
          </div>
          <div className="threshold-item">
            <label>Fear Index max (0-100)</label>
            <input
              type="number"
              min="0"
              max="50"
              value={allocation?.lt_max_fear_greed_index || 30}
              onChange={(e) => setAllocation({...allocation, lt_max_fear_greed_index: parseInt(e.target.value)})}
              disabled={!allocation?.lt_enabled}
            />
            <span className="hint">Défaut: 30 (acheter la peur)</span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="actions">
        <button 
          className="btn-primary" 
          onClick={handleSave}
          disabled={saving || !allocation}
        >
          {saving ? (
            <>
              <RefreshCw size={18} className="spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save size={18} />
              Sauvegarder
            </>
          )}
        </button>
      </div>
    </div>
  );
}
