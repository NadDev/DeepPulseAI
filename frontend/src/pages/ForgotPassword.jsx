import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './ForgotPassword.css';

const ForgotPassword = () => {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const { error } = await resetPassword(email);

    if (error) {
      setError(error.message || 'Failed to send reset email');
      setLoading(false);
    } else {
      setSuccess(true);
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="forgot-container">
        <div className="forgot-card">
          <div className="success-message">
            <div className="success-icon">📧</div>
            <h2>Check Your Email</h2>
            <p>We've sent a password reset link to:</p>
            <p style={{ fontWeight: 600, color: '#667eea' }}>{email}</p>
            <Link to="/login" className="btn-secondary">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="forgot-container">
      <div className="forgot-card">
        <div className="forgot-header">
          <h1>🔒</h1>
          <h2>Forgot Password?</h2>
          <p>Enter your email and we'll send you a reset link</p>
        </div>

        <form onSubmit={handleSubmit} className="forgot-form">
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              autoComplete="email"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>

          <Link to="/login" className="back-link">
            ← Back to Login
          </Link>
        </form>
      </div>
    </div>
  );
};

export default ForgotPassword;
