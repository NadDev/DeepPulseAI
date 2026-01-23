import { useState, useEffect } from 'react';
import { cryptoAPI } from '../services/api';
import { watchlistAPI } from '../services/watchlistAPI';
import MLPredictions from './MLPredictions';
import AdvancedAnalysis from './AdvancedAnalysis';
import { calculateElliottWaves } from '../utils/technicalAnalysis';
import React from 'react';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceDot, ReferenceArea, ReferenceLine
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Activity, BarChart2, 
  PieChart as PieIcon, MessageCircle, ThumbsUp, DollarSign, AlertCircle
} from 'lucide-react';
import './Charts.css';

function Charts() {
  const [selectedCoin, setSelectedCoin] = useState('BTC');
  const [period, setPeriod] = useState('7d');
  const [loading, setLoading] = useState(false);
  const [metricsVisible, setMetricsVisible] = useState(true);
  const [showMA20, setShowMA20] = useState(true);
  const [showMA50, setShowMA50] = useState(true);
  const [showMA200, setShowMA200] = useState(true);
  const [showEMA9, setShowEMA9] = useState(false);
  const [showEMA21, setShowEMA21] = useState(false);
  const [showVWAP, setShowVWAP] = useState(false);
  const [hoveredIndicator, setHoveredIndicator] = useState(null);
  
  // Data States
  const [chartData, setChartData] = useState([]);
  const [cryptoData, setCryptoData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [distributionData, setDistributionData] = useState([]);
  const [rsi, setRsi] = useState(null);
  const [macd, setMacd] = useState(null);
  const [bollinger, setBollinger] = useState(null);
  const [ema, setEma] = useState(null);
  const [elliottWave, setElliottWave] = useState(null);
  const [showElliottWaves, setShowElliottWaves] = useState(true);

  const [coins, setCoins] = useState([]);

  const DEFAULT_COINS = [
    { id: 'BTC', name: 'Bitcoin', symbol: 'BTC' },
    { id: 'ETH', name: 'Ethereum', symbol: 'ETH' },
    { id: 'BNB', name: 'Binance Coin', symbol: 'BNB' },
    { id: 'XRP', name: 'Ripple', symbol: 'XRP' },
    { id: 'ADA', name: 'Cardano', symbol: 'ADA' },
    { id: 'SOL', name: 'Solana', symbol: 'SOL' },
    { id: 'DOGE', name: 'Dogecoin', symbol: 'DOGE' }
  ];

  useEffect(() => {
    // Load watchlist on component mount
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    try {
      const watchlistData = await watchlistAPI.getWatchlist();
      console.log('Watchlist data received:', watchlistData);
      
      if (watchlistData && watchlistData.length > 0) {
        // watchlistData is array of watchlists, get first one's items
        const items = watchlistData[0].items || [];
        console.log('Watchlist items:', items);
        
        // Convert BTCUSDT format to BTC for display
        const coinsFromWatchlist = items.map(item => ({
          id: item.symbol.replace('/USDT', '').replace('USDT', ''),
          name: item.symbol,
          symbol: item.symbol.replace('/USDT', '').replace('USDT', '')
        }));
        
        console.log('Converted coins:', coinsFromWatchlist);
        
        if (coinsFromWatchlist.length > 0) {
          setCoins(coinsFromWatchlist);
          // Set first coin as default
          setSelectedCoin(coinsFromWatchlist[0].id);
          console.log('Selected coin:', coinsFromWatchlist[0].id);
        } else {
          // Fallback to default coins if watchlist is empty
          console.warn('Watchlist empty, using defaults');
          setCoins(DEFAULT_COINS);
          setSelectedCoin('BTC');
        }
      } else {
        // Fallback to default coins
        console.warn('No watchlist data, using defaults');
        setCoins(DEFAULT_COINS);
        setSelectedCoin('BTC');
      }
    } catch (error) {
      console.error('Error loading watchlist:', error);
      // Fallback to default coins
      setCoins(DEFAULT_COINS);
      setSelectedCoin('BTC');
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [selectedCoin, period]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [chartRes, dataRes, analysisRes, rsiRes, macdRes, bollingerRes, emaRes] = await Promise.all([
        cryptoAPI.getChartData(selectedCoin, period),
        cryptoAPI.getCryptoData(selectedCoin),
        cryptoAPI.getCryptoAnalysis(selectedCoin),
        cryptoAPI.getRSI(selectedCoin).catch(() => null),
        cryptoAPI.getMACD(selectedCoin).catch(() => null),
        cryptoAPI.getBollingerBands(selectedCoin).catch(() => null),
        cryptoAPI.getEMA(selectedCoin).catch(() => null)
      ]);

      // Process Chart Data
      if (chartRes && chartRes.prices) {
        const pricesRaw = chartRes.prices.map(p => p[1]);
        const volumesRaw = chartRes.total_volumes
          ? chartRes.total_volumes.map(v => v[1])
          : chartRes.prices.map(() => Math.random() * 1000 + 500);

        const formattedData = [];
        let sum20 = 0, sum50 = 0, sum200 = 0;
        let ema9Val = null, ema21Val = null;
        const k9 = 2 / (9 + 1);
        const k21 = 2 / (21 + 1);
        let cumPV = 0, cumV = 0;

        for (let i = 0; i < chartRes.prices.length; i++) {
          const [ts, price] = chartRes.prices[i];
          const dateObj = new Date(ts);
          const volume = volumesRaw[i] || 0;

          // Running sums for SMA
          sum20 += price;
          sum50 += price;
          sum200 += price;
          if (i >= 20) sum20 -= pricesRaw[i - 20];
          if (i >= 50) sum50 -= pricesRaw[i - 50];
          if (i >= 200) sum200 -= pricesRaw[i - 200];

          const ma20 = i >= 19 ? sum20 / 20 : null;
          const ma50 = i >= 49 ? sum50 / 50 : null;
          const ma200 = i >= 199 ? sum200 / 200 : null;

          // EMA
          if (ema9Val === null) {
            ema9Val = price;
            ema21Val = price;
          } else {
            ema9Val = price * k9 + ema9Val * (1 - k9);
            ema21Val = price * k21 + ema21Val * (1 - k21);
          }

          // VWAP
          cumPV += price * volume;
          cumV += volume;
          const vwap = cumV ? cumPV / cumV : price;

          formattedData.push({
            ts,
            date: dateObj.toLocaleDateString(),
            time: dateObj.toLocaleTimeString(),
            price,
            volume,
            ma20,
            ma50,
            ma200,
            ema9: ema9Val,
            ema21: ema21Val,
            vwap
          });
        }

        setChartData(formattedData);

        // Calculate Elliott Waves locally with adaptive window size
        // Shorter periods need smaller windows to detect waves
        let windowSize = 1; // Very sensitive for 1h/24h
        if (formattedData.length > 100) windowSize = 2;
        if (formattedData.length > 300) windowSize = 3;
        if (formattedData.length > 600) windowSize = 4;
        
        const elliottAnalysis = calculateElliottWaves(formattedData, windowSize);
        
        // Mark wave segments in data for highlighting
        if (elliottAnalysis && elliottAnalysis.waves) {
          elliottAnalysis.waves.slice(-5).forEach((wave, waveIdx) => {
            for (let i = wave.startIndex; i <= wave.endIndex && i < formattedData.length; i++) {
              formattedData[i].wavePrice = formattedData[i].price;
              formattedData[i].waveType = wave.type;
              formattedData[i].waveLabel = wave.wave;
            }
          });
        }
        
        setElliottWave(elliottAnalysis);

        // Calculate Distribution
        const prices = formattedData.map(d => d.price);
        const min = Math.min(...prices);
        const max = Math.max(...prices);
        const range = max - min;
        const buckets = [0, 0, 0, 0, 0];
        prices.forEach(p => {
          const bucketIndex = Math.min(Math.floor(((p - min) / range) * 5), 4);
          buckets[bucketIndex]++;
        });
        setDistributionData(buckets.map((count, i) => ({
          name: `${(i * 20)}-${(i + 1) * 20}%`,
          value: count
        })));
      }

      setCryptoData(dataRes);
      setAnalysisData(analysisRes);
      setRsi(rsiRes);
      setMacd(macdRes);
      setBollinger(bollingerRes);
      setEma(emaRes);

    } catch (error) {
      console.error("Error fetching chart page data:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  const formatCompact = (val) => new Intl.NumberFormat('en-US', { notation: "compact", compactDisplay: "short" }).format(val);

  const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#8B5CF6', '#EF4444'];

  const indicatorDescriptions = {
    ma20: "MA 20 : moyenne mobile 20 périodes pour la tendance courte / swing.",
    ma50: "MA 50 : moyenne mobile 50 périodes pour la tendance intermédiaire.",
    ma200: "MA 200 : moyenne mobile 200 périodes pour la tendance de fond long terme.",
    ema9: "EMA 9 : moyenne mobile exponentielle très réactive pour le momentum.",
    ema21: "EMA 21 : EMA pour la tendance court / moyen terme.",
    vwap: "VWAP : prix moyen pondéré par le volume, niveau d'équilibre intraday.",
    elliott: "Elliott Waves : détection automatique des vagues 1-5 (impulsives) et A-B-C (correctives)."
  };

  return (
    <div className="charts-page">
      {/* HEADER & CONTROLS */}
      <div className="charts-header">
        <div className="header-title">
          <div>
            <h1>Charts</h1>
            <p className="header-subtitle">Analyse temps réel des marchés</p>
          </div>
          <span className="live-badge">
            <span className="pulse-dot"></span> LIVE
          </span>
        </div>
        
        <div className="controls">
          <select 
            value={selectedCoin} 
            onChange={(e) => setSelectedCoin(e.target.value)}
            className="coin-select"
          >
            {coins.map(coin => (
              <option key={coin.id} value={coin.id}>
                {coin.name} ({coin.symbol})
              </option>
            ))}
          </select>
          
          <div className="period-selector">
            {['1h', '24h', '7d', '30d', '90d', '1y'].map(p => (
              <button 
                key={p} 
                className={`period-btn ${period === p ? 'active' : ''}`}
                onClick={() => setPeriod(p)}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Top info band */}
      {cryptoData && (
        <div className="info-bar-grid">
          <div className="info-card">
            <p className="label">Current Price</p>
            <h3>{formatCurrency(cryptoData.price)}</h3>
          </div>
          <div className="info-card">
            <p className="label">24h Change</p>
            <h3 className={cryptoData.change_24h >= 0 ? 'text-green' : 'text-red'}>
              {cryptoData.change_24h >= 0 ? '+' : ''}{cryptoData.change_24h?.toFixed(2)}%
            </h3>
          </div>
          <div className="info-card">
            <p className="label">Trend</p>
            <div className={`trend-badge ${analysisData?.trend || 'neutral'}`}>
              {analysisData?.trend?.toUpperCase() || 'NEUTRAL'}
            </div>
          </div>
          <div className="info-card">
            <p className="label">Sentiment</p>
            <h3>{analysisData?.sentiment_score > 0 ? '😊 Positive' : '😐 Neutral'}</h3>
          </div>
          <div className="info-card">
            <p className="label">Market Cap</p>
            <h3>${formatCompact(analysisData?.market_cap || 0)}</h3>
          </div>
        </div>
      )}

      {/* Technical indicators row under top info band */}
      {(rsi || macd || bollinger || ema) && (
        <div className="indicators-row">
          {/* RSI Indicator Card */}
          {rsi && (
            <div className="metric-card">
              <div className="card-header">
                <h3>RSI</h3>
                <AlertCircle size={18} className="text-blue" />
              </div>
              <div className="indicator-value">
                <span className="value">{typeof rsi === 'object' && rsi.value ? rsi.value.toFixed(2) : '-'}</span>
                <span className="status">{typeof rsi === 'object' && rsi.value ? (rsi.value >= 70 ? 'Overbought' : rsi.value <= 30 ? 'Oversold' : 'Neutral') : 'N/A'}</span>
              </div>
            </div>
          )}

          {/* MACD Indicator Card */}
          {macd && (
            <div className="metric-card">
              <div className="card-header">
                <h3>MACD</h3>
                <TrendingUp size={18} className={typeof macd === 'object' && macd.value > macd.signal ? 'text-green' : 'text-red'} />
              </div>
              <div className="indicator-value">
                <span className="value">{typeof macd === 'object' && macd.value ? macd.value.toFixed(4) : '-'}</span>
                <span className="status">{typeof macd === 'object' && macd.value > macd.signal ? 'Bullish' : 'Bearish'}</span>
              </div>
            </div>
          )}

          {/* Bollinger Bands Indicator Card */}
          {bollinger && (
            <div className="metric-card">
              <div className="card-header">
                <h3>Bollinger</h3>
                <BarChart2 size={18} className="text-orange" />
              </div>
              <div className="indicator-value">
                <span className="value">{typeof bollinger === 'object' && bollinger.middle ? bollinger.middle.toFixed(2) : '-'}</span>
                <span className="status">Middle</span>
              </div>
            </div>
          )}

          {/* EMA Indicator Card */}
          {ema && (
            <div className="metric-card">
              <div className="card-header">
                <h3>EMA</h3>
                <Activity size={18} className="text-emerald" />
              </div>
              <div className="indicator-value">
                <span className="value">{typeof ema === 'object' && ema.value ? ema.value.toFixed(2) : '-'}</span>
                <span className="status">Current</span>
              </div>
            </div>
          )}
        </div>
      )}

      <div className={`charts-main-layout ${!metricsVisible ? 'full-width' : ''}`}>
        <div className="charts-main-left">
          {/* Main Price Chart */}
          <div className="chart-box main-chart">
            <div className="box-header">
              <h3><Activity size={18} /> Price Action &amp; MA</h3>
            </div>
            <div className="ma-description-bar">
              {indicatorDescriptions[hoveredIndicator] || 'Survolez un indicateur (MA / EMA / VWAP) pour afficher une description détaillée.'}
            </div>
            <div className="ma-toggle-group">
              <button
                type="button"
                className={`ma-toggle ${showMA20 ? 'active' : ''}`}
                onClick={() => setShowMA20(!showMA20)}
                onMouseEnter={() => setHoveredIndicator('ma20')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                MA 20
              </button>
              <button
                type="button"
                className={`ma-toggle ${showMA50 ? 'active' : ''}`}
                onClick={() => setShowMA50(!showMA50)}
                onMouseEnter={() => setHoveredIndicator('ma50')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                MA 50
              </button>
              <button
                type="button"
                className={`ma-toggle ${showMA200 ? 'active' : ''}`}
                onClick={() => setShowMA200(!showMA200)}
                onMouseEnter={() => setHoveredIndicator('ma200')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                MA 200
              </button>
              <button
                type="button"
                className={`ma-toggle ${showEMA9 ? 'active' : ''}`}
                onClick={() => setShowEMA9(!showEMA9)}
                onMouseEnter={() => setHoveredIndicator('ema9')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                EMA 9
              </button>
              <button
                type="button"
                className={`ma-toggle ${showEMA21 ? 'active' : ''}`}
                onClick={() => setShowEMA21(!showEMA21)}
                onMouseEnter={() => setHoveredIndicator('ema21')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                EMA 21
              </button>
              <button
                type="button"
                className={`ma-toggle ${showVWAP ? 'active' : ''}`}
                onClick={() => setShowVWAP(!showVWAP)}
                onMouseEnter={() => setHoveredIndicator('vwap')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                VWAP
              </button>
              <button
                type="button"
                className={`ma-toggle ${showElliottWaves ? 'active' : ''}`}
                onClick={() => setShowElliottWaves(!showElliottWaves)}
                onMouseEnter={() => setHoveredIndicator('elliott')}
                onMouseLeave={() => setHoveredIndicator(null)}
              >
                Elliott Waves
              </button>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="ts" 
                  stroke="#94a3b8" 
                  tick={{fontSize: 12}}
                  tickFormatter={(value) => {
                    if (!value) return '';
                    const d = new Date(value);
                    return period === '1h' || period === '24h'
                      ? d.toLocaleTimeString()
                      : d.toLocaleDateString();
                  }}
                />
                <YAxis domain={['auto', 'auto']} stroke="#94a3b8" tickFormatter={(val) => `$${val}`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                  formatter={(val) => [formatCurrency(val), 'Price']}
                  labelFormatter={(value) => {
                    if (!value) return '';
                    const d = new Date(value);
                    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
                  }}
                />
                <Legend />
                
                <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} dot={false} name="Price" />
                
                {/* Elliott Wave highlight - colored overlay on price where waves are detected */}
                {showElliottWaves && (
                  <Line 
                    type="monotone" 
                    dataKey="wavePrice" 
                    stroke="#818CF8" 
                    strokeWidth={2.5} 
                    dot={false} 
                    name="Wave" 
                    connectNulls={false}
                  />
                )}
                
                {/* Elliott Wave - Labels above the price line at wave end points */}
                {showElliottWaves && elliottWave && elliottWave.waves && elliottWave.waves.length > 0 && chartData.length > 0 && (
                  <>
                    {elliottWave.waves.slice(-5).map((wave, idx) => {
                      const isImpulse = wave.type === 'impulse';
                      const waveColor = isImpulse ? '#A78BFA' : '#67E8F9';
                      const endPoint = chartData[wave.endIndex];
                      if (!endPoint) return null;

                      return (
                        <ReferenceDot
                          key={`wave-label-${idx}`}
                          x={endPoint.ts}
                          y={endPoint.price}
                          r={0}
                          isFront={true}
                          label={{
                            value: wave.wave,
                            position: 'top',
                            fill: waveColor,
                            fontSize: 12,
                            fontWeight: 'bold',
                            offset: 6
                          }}
                        />
                      );
                    })}
                  </>
                )}
                {showMA20 && (
                  <Line
                    type="monotone"
                    dataKey="ma20"
                    stroke="rgba(245, 158, 11, 0.4)"
                    strokeWidth={1}
                    dot={false}
                    strokeDasharray="5 5"
                    name="MA 20"
                  />
                )}
                {showMA50 && (
                  <Line
                    type="monotone"
                    dataKey="ma50"
                    stroke="rgba(139, 92, 246, 0.4)"
                    strokeWidth={1}
                    dot={false}
                    strokeDasharray="5 5"
                    name="MA 50"
                  />
                )}
                {showMA200 && (
                  <Line
                    type="monotone"
                    dataKey="ma200"
                    stroke="rgba(99, 102, 241, 0.45)"
                    strokeWidth={1.1}
                    dot={false}
                    strokeDasharray="4 4"
                    name="MA 200"
                  />
                )}
                {showEMA9 && (
                  <Line
                    type="monotone"
                    dataKey="ema9"
                    stroke="rgba(34, 197, 94, 0.35)"
                    strokeWidth={1}
                    dot={false}
                    name="EMA 9"
                  />
                )}
                {showEMA21 && (
                  <Line
                    type="monotone"
                    dataKey="ema21"
                    stroke="rgba(14, 165, 233, 0.35)"
                    strokeWidth={1}
                    dot={false}
                    name="EMA 21"
                  />
                )}
                {showVWAP && (
                  <Line
                    type="monotone"
                    dataKey="vwap"
                    stroke="rgba(249, 115, 22, 0.4)"
                    strokeWidth={1.1}
                    dot={false}
                    name="VWAP"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Advanced Technical Analysis under main chart */}
          <AdvancedAnalysis symbol={selectedCoin} localWaves={elliottWave} period={period} />
        </div>

        <button 
          className="metrics-toggle-btn" 
          onClick={() => setMetricsVisible(!metricsVisible)}
          title={metricsVisible ? 'Collapse metrics' : 'Show metrics'}
        >
          {metricsVisible ? '→' : '←'}
        </button>

        <aside className={`charts-main-right ${!metricsVisible ? 'hidden' : ''}`}>
          {/* Metrics stacked on the right */}
          <div className="metrics-column">
            {/* ML Engine on top of metrics */}
            <MLPredictions symbol={selectedCoin} />

            <div className="metric-card">
              <div className="card-header">
                <h3>Reputation Score</h3>
                <ThumbsUp size={18} className="text-emerald" />
              </div>
              <div className="reputation-container">
                <div className="score-row">
                  <span>Overall</span>
                  <span className="score-val">{((analysisData?.reputation_score || 0.5) * 100).toFixed(0)}%</span>
                </div>
                <div className="progress-bg">
                  <div 
                    className="progress-fill" 
                    style={{width: `${(analysisData?.reputation_score || 0.5) * 100}%`}}
                  ></div>
                </div>
                <div className="checklist">
                  <p>✓ Active community</p>
                  <p>✓ Market cap tracked</p>
                  <p>✓ Social mentions tracked</p>
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="card-header">
                <h3>Social Activity</h3>
                <MessageCircle size={18} className="text-blue" />
              </div>
              <div className="social-stats">
                <div className="stat-box">
                  <span className="sub-label">24h Mentions</span>
                  <span className="stat-val text-blue">{analysisData?.social_mentions_count?.toLocaleString() || '-'}</span>
                </div>
                <div className="stat-box">
                  <span className="sub-label">Sentiment</span>
                  <span className="stat-val">{analysisData?.sentiment_score > 0 ? 'Positive' : 'Neutral'}</span>
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="card-header">
                <h3>Market Metrics</h3>
                <DollarSign size={18} className="text-orange" />
              </div>
              <div className="market-list">
                <div className="market-item">
                  <span>24h High</span>
                  <span className="text-green">{formatCurrency(cryptoData?.high_24h || 0)}</span>
                </div>
                <div className="market-item">
                  <span>24h Low</span>
                  <span className="text-red">{formatCurrency(cryptoData?.low_24h || 0)}</span>
                </div>
                <div className="market-item">
                  <span>Volume</span>
                  <span className="text-blue">{formatCompact(cryptoData?.volume_24h || 0)}</span>
                </div>
              </div>
            </div>

              {/* Volume Analysis (compact) */}
              <div className="chart-box volume-compact">
                <div className="box-header">
                  <h3><BarChart2 size={18} /> Volume Analysis</h3>
                </div>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" hide />
                    <YAxis stroke="#94a3b8" tickFormatter={formatCompact} />
                    <Tooltip 
                      cursor={{fill: '#334155', opacity: 0.4}}
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                    />
                    <Bar dataKey="volume" fill="#3B82F6" name="Volume" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
          </div>
        </aside>
      </div>

      {/* Secondary grid: distribution only */}
      <div className="charts-secondary-grid">
        <div className="chart-box">
          <div className="box-header">
            <h3><PieIcon size={18} /> Price Distribution</h3>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={distributionData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {distributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default Charts;
