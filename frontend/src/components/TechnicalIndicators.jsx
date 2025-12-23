import { useState, useEffect } from 'react';
import { cryptoAPI } from '../services/api';
import { 
  TrendingUp, TrendingDown, Activity, BarChart2, 
  AlertTriangle, Target, Gauge 
} from 'lucide-react';
import './TechnicalIndicators.css';

function TechnicalIndicators({ symbol = 'BTC' }) {
  const [loading, setLoading] = useState(false);
  const [rsi, setRsi] = useState(null);
  const [macd, setMacd] = useState(null);
  const [bollinger, setBollinger] = useState(null);
  const [ema, setEma] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [fearGreed, setFearGreed] = useState(null);

  useEffect(() => {
    fetchIndicators();
    const interval = setInterval(fetchIndicators, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [symbol]);

  const fetchIndicators = async () => {
    setLoading(true);
    try {
      const [rsiRes, macdRes, bollingerRes, emaRes, sentimentRes, fearGreedRes] = await Promise.all([
        cryptoAPI.getRSI(symbol).catch(() => null),
        cryptoAPI.getMACD(symbol).catch(() => null),
        cryptoAPI.getBollingerBands(symbol).catch(() => null),
        cryptoAPI.getEMA(symbol).catch(() => null),
        cryptoAPI.getSentiment(symbol).catch(() => null),
        cryptoAPI.getFearGreedIndex(symbol).catch(() => null)
      ]);

      setRsi(rsiRes);
      setMacd(macdRes);
      setBollinger(bollingerRes);
      setEma(emaRes);
      setSentiment(sentimentRes);
      setFearGreed(fearGreedRes);
    } catch (error) {
      console.error("Error fetching indicators:", error);
    } finally {
      setLoading(false);
    }
  };

  const getRsiColor = (value) => {
    if (!value) return 'neutral';
    if (value >= 70) return 'overbought';
    if (value <= 30) return 'oversold';
    return 'neutral';
  };

  const getMacdSignal = (macd, signal) => {
    if (!macd || !signal) return 'neutral';
    return macd > signal ? 'bullish' : 'bearish';
  };

  const getFearGreedClass = (value) => {
    if (!value) return 'neutral';
    if (value <= 25) return 'extreme-fear';
    if (value <= 45) return 'fear';
    if (value <= 55) return 'neutral';
    if (value <= 75) return 'greed';
    return 'extreme-greed';
  };

  return (
    <div className={`technical-indicators ${loading ? 'loading' : ''}`}>
      <div className="indicators-header">
        <h3><Activity size={18} /> Technical Indicators</h3>
        <span className="symbol-badge">{symbol}</span>
      </div>

      <div className="indicators-grid">
        {/* RSI Card */}
        <div className={`indicator-card rsi ${getRsiColor(rsi?.value)}`}>
          <div className="indicator-header">
            <Gauge size={16} />
            <span>RSI ({rsi?.period || 14})</span>
          </div>
          <div className="indicator-value">
            {rsi?.value?.toFixed(2) || '—'}
          </div>
          <div className="indicator-interpretation">
            {rsi?.interpretation || 'Loading...'}
          </div>
          <div className="rsi-gauge">
            <div 
              className="rsi-needle" 
              style={{ left: `${Math.min(100, Math.max(0, rsi?.value || 50))}%` }}
            />
            <div className="rsi-zones">
              <span className="oversold">30</span>
              <span className="neutral">50</span>
              <span className="overbought">70</span>
            </div>
          </div>
        </div>

        {/* MACD Card */}
        <div className={`indicator-card macd ${getMacdSignal(macd?.macd, macd?.signal)}`}>
          <div className="indicator-header">
            <BarChart2 size={16} />
            <span>MACD</span>
          </div>
          <div className="macd-values">
            <div className="macd-row">
              <span className="label">MACD:</span>
              <span className="value">{macd?.macd?.toFixed(4) || '—'}</span>
            </div>
            <div className="macd-row">
              <span className="label">Signal:</span>
              <span className="value">{macd?.signal?.toFixed(4) || '—'}</span>
            </div>
            <div className="macd-row">
              <span className="label">Histogram:</span>
              <span className={`value ${(macd?.histogram || 0) >= 0 ? 'positive' : 'negative'}`}>
                {macd?.histogram?.toFixed(4) || '—'}
              </span>
            </div>
          </div>
          <div className="indicator-interpretation">
            {macd?.interpretation || 'Loading...'}
          </div>
        </div>

        {/* Bollinger Bands Card */}
        <div className="indicator-card bollinger">
          <div className="indicator-header">
            <Target size={16} />
            <span>Bollinger Bands ({bollinger?.period || 20})</span>
          </div>
          <div className="bollinger-values">
            <div className="band upper">
              <span className="label">Upper:</span>
              <span className="value">${bollinger?.upper_band?.toFixed(2) || '—'}</span>
            </div>
            <div className="band middle">
              <span className="label">Middle:</span>
              <span className="value">${bollinger?.middle_band?.toFixed(2) || '—'}</span>
            </div>
            <div className="band lower">
              <span className="label">Lower:</span>
              <span className="value">${bollinger?.lower_band?.toFixed(2) || '—'}</span>
            </div>
          </div>
          <div className="indicator-interpretation">
            Position: <strong>{bollinger?.position || '—'}</strong>
          </div>
        </div>

        {/* EMA Card */}
        <div className={`indicator-card ema ${ema?.interpretation?.includes('BULLISH') ? 'bullish' : ema?.interpretation?.includes('BEARISH') ? 'bearish' : 'neutral'}`}>
          <div className="indicator-header">
            <TrendingUp size={16} />
            <span>EMA ({ema?.period || 50})</span>
          </div>
          <div className="ema-values">
            <div className="ema-row">
              <span className="label">EMA:</span>
              <span className="value">${ema?.value?.toFixed(2) || '—'}</span>
            </div>
            <div className="ema-row">
              <span className="label">Price:</span>
              <span className="value">${ema?.price?.toFixed(2) || '—'}</span>
            </div>
          </div>
          <div className="indicator-interpretation">
            {ema?.interpretation || 'Loading...'}
          </div>
        </div>

        {/* Sentiment Card */}
        <div className={`indicator-card sentiment ${sentiment?.overall_sentiment?.toLowerCase() || 'neutral'}`}>
          <div className="indicator-header">
            <Activity size={16} />
            <span>Market Sentiment</span>
          </div>
          <div className="sentiment-value">
            {sentiment?.overall_sentiment || 'Neutral'}
          </div>
          <div className="sentiment-score">
            Score: <strong>{sentiment?.sentiment_score?.toFixed(0) || '—'}</strong>/100
          </div>
          <div className="sentiment-sources">
            <span>Social: {sentiment?.social_sentiment || '—'}</span>
            <span>News: {sentiment?.news_sentiment || '—'}</span>
          </div>
        </div>

        {/* Fear & Greed Index */}
        <div className={`indicator-card fear-greed ${getFearGreedClass(fearGreed?.value)}`}>
          <div className="indicator-header">
            <AlertTriangle size={16} />
            <span>Fear & Greed Index</span>
          </div>
          <div className="fear-greed-value">
            {fearGreed?.value || '—'}
          </div>
          <div className="fear-greed-label">
            {fearGreed?.classification || 'Loading...'}
          </div>
          <div className="fear-greed-gauge">
            <div 
              className="fear-greed-needle" 
              style={{ left: `${Math.min(100, Math.max(0, fearGreed?.value || 50))}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default TechnicalIndicators;
