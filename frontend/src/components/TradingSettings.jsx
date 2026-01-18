import React, { useState, useEffect } from 'react';
import { Shield, Target, Flame, Info, Save, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

/**
 * TradingSettings Component
 * Allows users to configure their SL/TP profile (PRUDENT, BALANCED, AGGRESSIVE)
 * Profile determines stop-loss, take-profit, and trailing stop parameters
 */
export default function TradingSettings() {
  const { session } = useAuth();
  const [settings, setSettings] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState('BALANCED');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [profileDetails, setProfileDetails] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Profile icons and colors
  const profileConfig = {
    PRUDENT: {
      icon: <Shield size={24} />,
      color: '#22c55e',
      bgColor: 'rgba(34, 197, 94, 0.1)',
      borderColor: 'rgba(34, 197, 94, 0.3)',
      description: 'Stops serrés, sorties rapides - idéal pour les débutants',
      riskLevel: 'Faible'
    },
    BALANCED: {
      icon: <Target size={24} />,
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.1)',
      borderColor: 'rgba(245, 158, 11, 0.3)',
      description: 'Équilibre entre protection et potentiel de gain',
      riskLevel: 'Moyen'
    },
    AGGRESSIVE: {
      icon: <Flame size={24} />,
      color: '#ef4444',
      bgColor: 'rgba(239, 68, 68, 0.1)',
      borderColor: 'rgba(239, 68, 68, 0.3)',
      description: 'Stops larges, objectifs ambitieux - traders expérimentés',
      riskLevel: 'Élevé'
    }
  };

  // Fetch current settings on mount
  useEffect(() => {
    fetchSettings();
    fetchProfiles();
  }, []);

  // Fetch profile details when selection changes
  useEffect(() => {
    if (selectedProfile) {
      fetchProfileDetails(selectedProfile);
    }
  }, [selectedProfile]);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/trading`, {
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setSelectedProfile(data.sl_tp_profile || 'BALANCED');
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      setMessage({ type: 'error', text: 'Erreur lors du chargement des paramètres' });
    } finally {
      setLoading(false);
    }
  };

  const fetchProfiles = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/trading/profiles`, {
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setProfiles(data.profiles || []);
      }
    } catch (error) {
      console.error('Error fetching profiles:', error);
    }
  };

  const fetchProfileDetails = async (profileName) => {
    try {
      const response = await fetch(`${API_URL}/api/settings/trading/profile/${profileName}`, {
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setProfileDetails(data);
      }
    } catch (error) {
      console.error('Error fetching profile details:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await fetch(`${API_URL}/api/settings/trading`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sl_tp_profile: selectedProfile
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setMessage({ type: 'success', text: 'Profil de trading mis à jour avec succès!' });
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Erreur lors de la sauvegarde' });
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setMessage({ type: 'error', text: 'Erreur de connexion au serveur' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await fetch(`${API_URL}/api/settings/trading/reset`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setSelectedProfile(data.sl_tp_profile || 'BALANCED');
        setMessage({ type: 'success', text: 'Paramètres réinitialisés aux valeurs par défaut' });
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Erreur lors de la réinitialisation' });
      }
    } catch (error) {
      console.error('Error resetting settings:', error);
      setMessage({ type: 'error', text: 'Erreur de connexion au serveur' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page-section">
        <div className="loading-state">
          <RefreshCw className="spin" size={32} />
          <p>Chargement des paramètres de trading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page-section">
      <div className="section-header">
        <h2>📊 Paramètres de Trading</h2>
        <p>Configurez votre profil de gestion des SL/TP intelligent</p>
      </div>

      {/* Message notification */}
      {message.text && (
        <div className={`notification ${message.type}`}>
          {message.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Profile Selection */}
      <div className="trading-profiles">
        <h3>Choisissez votre profil de risque</h3>
        <div className="profile-cards">
          {['PRUDENT', 'BALANCED', 'AGGRESSIVE'].map(profile => {
            const config = profileConfig[profile];
            const isSelected = selectedProfile === profile;
            
            return (
              <div
                key={profile}
                className={`profile-card ${isSelected ? 'selected' : ''}`}
                style={{
                  backgroundColor: isSelected ? config.bgColor : 'var(--card-bg)',
                  borderColor: isSelected ? config.color : config.borderColor,
                  borderWidth: isSelected ? '2px' : '1px'
                }}
                onClick={() => setSelectedProfile(profile)}
              >
                <div className="profile-icon" style={{ color: config.color }}>
                  {config.icon}
                </div>
                <div className="profile-info">
                  <h4 style={{ color: isSelected ? config.color : 'inherit' }}>
                    {profile}
                  </h4>
                  <p className="profile-description">{config.description}</p>
                  <span 
                    className="risk-badge" 
                    style={{ 
                      backgroundColor: config.bgColor,
                      color: config.color,
                      border: `1px solid ${config.borderColor}`
                    }}
                  >
                    Risque: {config.riskLevel}
                  </span>
                </div>
                {isSelected && (
                  <div className="selected-indicator" style={{ backgroundColor: config.color }}>
                    <CheckCircle size={16} color="white" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Profile Details */}
      {profileDetails && (
        <div className="profile-details">
          <h3>
            <Info size={18} />
            Détails du profil {selectedProfile}
          </h3>
          <div className="details-grid">
            <div className="detail-item">
              <span className="label">Stop Loss</span>
              <span className="value negative">-{(profileDetails.sl_pct * 100).toFixed(1)}%</span>
            </div>
            <div className="detail-item">
              <span className="label">ATR Multiplier</span>
              <span className="value">{profileDetails.atr_multiplier}x</span>
            </div>
            <div className="detail-item">
              <span className="label">Take Profit 1 (R:R)</span>
              <span className="value positive">{profileDetails.tp1_rr}:1</span>
            </div>
            <div className="detail-item">
              <span className="label">Take Profit 2 (R:R)</span>
              <span className="value positive">{profileDetails.tp2_rr}:1</span>
            </div>
            <div className="detail-item">
              <span className="label">Trailing Activation</span>
              <span className="value">+{(profileDetails.trailing_activation_pct * 100).toFixed(1)}%</span>
            </div>
            <div className="detail-item">
              <span className="label">Trailing Distance</span>
              <span className="value">{(profileDetails.trailing_distance_pct * 100).toFixed(2)}%</span>
            </div>
            <div className="detail-item">
              <span className="label">TP1 Partiel</span>
              <span className="value">{(profileDetails.partial_tp_pct * 100).toFixed(0)}%</span>
            </div>
          </div>
          
          {/* Visual explanation */}
          <div className="profile-explanation">
            <h4>💡 Comment ça fonctionne ?</h4>
            <ul>
              <li>
                <strong>Stop Loss:</strong> Position fermée automatiquement si le prix baisse de {(profileDetails.sl_pct * 100).toFixed(1)}% 
                (ou {profileDetails.atr_multiplier}x ATR si plus serré)
              </li>
              <li>
                <strong>Take Profit:</strong> {(profileDetails.partial_tp_pct * 100).toFixed(0)}% vendus à TP1 ({profileDetails.tp1_rr}:1 R:R), 
                le reste court vers TP2 ({profileDetails.tp2_rr}:1 R:R)
              </li>
              <li>
                <strong>Trailing Stop:</strong> Activé après +{(profileDetails.trailing_activation_pct * 100).toFixed(1)}%, 
                suit le prix à {(profileDetails.trailing_distance_pct * 100).toFixed(2)}% de distance
              </li>
            </ul>
          </div>
        </div>
      )}

      {/* Current Settings Info */}
      {settings && (
        <div className="current-settings-info">
          <Info size={18} />
          <span>
            Profil actuel: <strong>{settings.sl_tp_profile}</strong> | 
            Dernière mise à jour: {new Date(settings.updated_at).toLocaleString('fr-FR')}
          </span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="trading-settings-actions">
        <button 
          className="btn-secondary"
          onClick={handleReset}
          disabled={saving}
        >
          <RefreshCw size={18} className={saving ? 'spin' : ''} />
          Réinitialiser
        </button>
        <button 
          className="btn-primary"
          onClick={handleSave}
          disabled={saving || selectedProfile === settings?.sl_tp_profile}
        >
          <Save size={18} />
          {saving ? 'Sauvegarde...' : 'Sauvegarder'}
        </button>
      </div>

      {/* Styling */}
      <style>{`
        .trading-profiles {
          margin-top: 1.5rem;
        }
        
        .trading-profiles h3 {
          margin-bottom: 1rem;
          color: var(--text-primary);
        }
        
        .profile-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1rem;
        }
        
        .profile-card {
          position: relative;
          padding: 1.5rem;
          border-radius: 12px;
          border: 1px solid var(--border-color);
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          gap: 1rem;
          align-items: flex-start;
        }
        
        .profile-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .profile-icon {
          flex-shrink: 0;
          padding: 0.5rem;
          border-radius: 8px;
          background: var(--card-bg);
        }
        
        .profile-info h4 {
          margin: 0 0 0.5rem 0;
          font-size: 1.1rem;
          font-weight: 600;
        }
        
        .profile-description {
          font-size: 0.85rem;
          color: var(--text-secondary);
          margin-bottom: 0.75rem;
        }
        
        .risk-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 500;
        }
        
        .selected-indicator {
          position: absolute;
          top: 0.75rem;
          right: 0.75rem;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .profile-details {
          margin-top: 2rem;
          padding: 1.5rem;
          background: var(--card-bg);
          border-radius: 12px;
          border: 1px solid var(--border-color);
        }
        
        .profile-details h3 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 1rem;
          color: var(--text-primary);
        }
        
        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 1rem;
        }
        
        .detail-item {
          padding: 1rem;
          background: var(--bg-secondary);
          border-radius: 8px;
          text-align: center;
        }
        
        .detail-item .label {
          display: block;
          font-size: 0.8rem;
          color: var(--text-secondary);
          margin-bottom: 0.5rem;
        }
        
        .detail-item .value {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--text-primary);
        }
        
        .detail-item .value.positive {
          color: #22c55e;
        }
        
        .detail-item .value.negative {
          color: #ef4444;
        }
        
        .profile-explanation {
          margin-top: 1.5rem;
          padding: 1rem;
          background: rgba(59, 130, 246, 0.1);
          border-radius: 8px;
          border-left: 3px solid #3b82f6;
        }
        
        .profile-explanation h4 {
          margin: 0 0 0.75rem 0;
          color: #3b82f6;
        }
        
        .profile-explanation ul {
          margin: 0;
          padding-left: 1.25rem;
        }
        
        .profile-explanation li {
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
          color: var(--text-secondary);
        }
        
        .profile-explanation li strong {
          color: var(--text-primary);
        }
        
        .current-settings-info {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-top: 1.5rem;
          padding: 1rem;
          background: var(--bg-secondary);
          border-radius: 8px;
          font-size: 0.9rem;
          color: var(--text-secondary);
        }
        
        .trading-settings-actions {
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid var(--border-color);
        }
        
        .notification {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
        }
        
        .notification.success {
          background: rgba(34, 197, 94, 0.1);
          color: #22c55e;
          border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .notification.error {
          background: rgba(239, 68, 68, 0.1);
          color: #ef4444;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          color: var(--text-secondary);
        }
        
        .spin {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .btn-primary, .btn-secondary {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .btn-primary {
          background: var(--primary-color, #3b82f6);
          color: white;
          border: none;
        }
        
        .btn-primary:hover:not(:disabled) {
          background: var(--primary-hover, #2563eb);
        }
        
        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .btn-secondary {
          background: transparent;
          color: var(--text-primary);
          border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover:not(:disabled) {
          background: var(--bg-secondary);
        }
      `}</style>
    </div>
  );
}
