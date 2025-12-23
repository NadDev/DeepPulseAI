
export const calculateElliottWaves = (data, windowSize = 2) => {
  if (!data || data.length < windowSize * 2) {
    return null;
  }

  const prices = data.map(d => d.price);
  const extrema = [];

  // 1. Find local extrema (peaks and troughs) - allow closer to end
  const endOffset = Math.max(1, Math.floor(windowSize / 2)); // Reduce end offset
  for (let i = windowSize; i < prices.length - endOffset; i++) {
    const current = prices[i];
    const windowSlice = prices.slice(i - windowSize, i + windowSize + 1);
    const maxVal = Math.max(...windowSlice);
    const minVal = Math.min(...windowSlice);

    if (current === maxVal) {
      extrema.push({ index: i, price: current, type: 'peak' });
    } else if (current === minVal) {
      extrema.push({ index: i, price: current, type: 'trough' });
    }
  }

  // Add last point if it's significantly different from last extrema
  if (extrema.length > 0) {
    const lastExtrema = extrema[extrema.length - 1];
    const lastPrice = prices[prices.length - 1];
    const priceChange = Math.abs((lastPrice - lastExtrema.price) / lastExtrema.price);
    
    // If price moved more than 1% since last extrema, add it
    if (priceChange > 0.01) {
      const isNewPeak = lastPrice > lastExtrema.price;
      extrema.push({ 
        index: prices.length - 1, 
        price: lastPrice, 
        type: isNewPeak ? 'peak' : 'trough' 
      });
    }
  }

  if (extrema.length < 2) {
    return null;
  }

  // 2. Analyze wave structure
  const waves = [];
  let waveCount = 0;

  for (let i = 1; i < extrema.length; i++) {
    const startNode = extrema[i - 1];
    const endNode = extrema[i];

    waveCount++;
    const waveNum = waveCount % 8;
    
    let waveLabel;
    let waveType;

    // Map 1-5 -> Impulse, 6-8 -> Corrective (A, B, C)
    switch (waveNum) {
      case 1: waveLabel = '1'; waveType = 'impulse'; break;
      case 2: waveLabel = '2'; waveType = 'impulse'; break;
      case 3: waveLabel = '3'; waveType = 'impulse'; break;
      case 4: waveLabel = '4'; waveType = 'impulse'; break;
      case 5: waveLabel = '5'; waveType = 'impulse'; break;
      case 6: waveLabel = 'A'; waveType = 'corrective'; break;
      case 7: waveLabel = 'B'; waveType = 'corrective'; break;
      case 0: waveLabel = 'C'; waveType = 'corrective'; break;
      default: waveLabel = '?'; waveType = 'unknown';
    }

    // Calculate wave amplitude (percentage move)
    const amplitude = Math.abs((endNode.price - startNode.price) / startNode.price) * 100;

    waves.push({
      wave: waveLabel,
      type: waveType,
      startIndex: startNode.index,
      endIndex: endNode.index,
      startPrice: startNode.price,
      endPrice: endNode.price,
      startDate: data[startNode.index].date,
      endDate: data[endNode.index].date,
      amplitude,
      direction: endNode.price > startNode.price ? 'up' : 'down'
    });
  }

  // 3. Calculate confidence score
  const confidence = calculateConfidence(waves, extrema, prices);

  // 4. Current position analysis (from last extrema to now)
  const lastExtrema = extrema[extrema.length - 1];
  const lastPrice = prices[prices.length - 1];
  
  // Determine potential current wave
  const currentWaveNum = (waveCount + 1) % 8;
  let currentWaveLabel;
  switch (currentWaveNum) {
    case 1: currentWaveLabel = '1'; break;
    case 2: currentWaveLabel = '2'; break;
    case 3: currentWaveLabel = '3'; break;
    case 4: currentWaveLabel = '4'; break;
    case 5: currentWaveLabel = '5'; break;
    case 6: currentWaveLabel = 'A'; break;
    case 7: currentWaveLabel = 'B'; break;
    case 0: currentWaveLabel = 'C'; break;
    default: currentWaveLabel = '?';
  }

  return {
    waves,
    currentWave: {
      label: currentWaveLabel,
      startIndex: lastExtrema.index,
      startPrice: lastExtrema.price,
      currentPrice: lastPrice,
      direction: lastPrice > lastExtrema.price ? 'up' : 'down'
    },
    confidence
  };
};

/**
 * Calcule un score de confiance basé sur :
 * 1. Qualité structurelle (nombre de vagues, alternance, amplitude)
 * 2. Précision historique (les prédictions passées étaient-elles correctes ?)
 */
const calculateConfidence = (waves, extrema, prices) => {
  if (waves.length < 3) {
    return { score: 0.3, factors: { structure: 0.3, historical: 0, pattern: 0 } };
  }

  // === FACTEUR 1: Qualité structurelle (30% du score) ===
  let structureScore = 0;
  
  // Plus de vagues = meilleure détection (jusqu'à un certain point)
  const waveCountScore = Math.min(waves.length / 10, 1); // Max à 10 vagues
  structureScore += waveCountScore * 0.4;
  
  // Alternance correcte peak/trough
  let correctAlternation = 0;
  for (let i = 1; i < extrema.length; i++) {
    if (extrema[i].type !== extrema[i-1].type) {
      correctAlternation++;
    }
  }
  const alternationScore = correctAlternation / (extrema.length - 1);
  structureScore += alternationScore * 0.3;
  
  // Amplitudes significatives (pas du bruit)
  const avgAmplitude = waves.reduce((sum, w) => sum + w.amplitude, 0) / waves.length;
  const amplitudeScore = Math.min(avgAmplitude / 5, 1); // 5% = score max
  structureScore += amplitudeScore * 0.3;

  // === FACTEUR 2: Précision historique (40% du score) ===
  // Vérifie si les vagues passées ont correctement prédit la direction suivante
  let historicalScore = 0;
  let correctPredictions = 0;
  let totalPredictions = 0;

  for (let i = 0; i < waves.length - 1; i++) {
    const wave = waves[i];
    const nextWave = waves[i + 1];
    
    // Après une vague impulse montante (1,3,5), on attend une correction
    // Après une vague impulse descendante (2,4), on attend une montée
    let expectedDirection;
    
    if (['1', '3', '5'].includes(wave.wave)) {
      expectedDirection = 'down'; // Correction après impulse haussière
    } else if (['2', '4'].includes(wave.wave)) {
      expectedDirection = 'up'; // Reprise après correction
    } else if (wave.wave === 'A') {
      expectedDirection = 'up'; // Rebond B
    } else if (wave.wave === 'B') {
      expectedDirection = 'down'; // Chute C
    } else if (wave.wave === 'C') {
      expectedDirection = 'up'; // Nouveau cycle
    }

    if (expectedDirection && nextWave.direction === expectedDirection) {
      correctPredictions++;
    }
    totalPredictions++;
  }

  if (totalPredictions > 0) {
    historicalScore = correctPredictions / totalPredictions;
  }

  // === FACTEUR 3: Respect des règles Elliott (30% du score) ===
  let patternScore = 0;
  let rulesChecked = 0;
  let rulesPassed = 0;

  // Trouver les cycles complets (1-5 + ABC)
  const impulseWaves = waves.filter(w => ['1','2','3','4','5'].includes(w.wave));
  
  // Règle 1: Vague 3 ne doit pas être la plus courte des vagues 1,3,5
  const wave1s = waves.filter(w => w.wave === '1');
  const wave3s = waves.filter(w => w.wave === '3');
  const wave5s = waves.filter(w => w.wave === '5');
  
  if (wave1s.length > 0 && wave3s.length > 0 && wave5s.length > 0) {
    rulesChecked++;
    const lastW1 = wave1s[wave1s.length - 1];
    const lastW3 = wave3s[wave3s.length - 1];
    const lastW5 = wave5s[wave5s.length - 1];
    
    if (lastW3.amplitude >= lastW1.amplitude || lastW3.amplitude >= lastW5.amplitude) {
      rulesPassed++;
    }
  }

  // Règle 2: Vague 2 ne retrace pas 100% de vague 1
  if (wave1s.length > 0 && waves.filter(w => w.wave === '2').length > 0) {
    rulesChecked++;
    const wave2s = waves.filter(w => w.wave === '2');
    const lastW1 = wave1s[wave1s.length - 1];
    const lastW2 = wave2s[wave2s.length - 1];
    
    // Si vague 2 ne dépasse pas le début de vague 1
    if (lastW1.direction === 'up' && lastW2.endPrice > lastW1.startPrice) {
      rulesPassed++;
    } else if (lastW1.direction === 'down' && lastW2.endPrice < lastW1.startPrice) {
      rulesPassed++;
    }
  }

  // Règle 3: Vague 4 ne chevauche pas vague 1
  const wave4s = waves.filter(w => w.wave === '4');
  if (wave1s.length > 0 && wave4s.length > 0) {
    rulesChecked++;
    const lastW1 = wave1s[wave1s.length - 1];
    const lastW4 = wave4s[wave4s.length - 1];
    
    // Vague 4 ne doit pas descendre sous le sommet de vague 1
    if (lastW1.direction === 'up' && lastW4.endPrice > lastW1.endPrice) {
      rulesPassed++;
    }
  }

  if (rulesChecked > 0) {
    patternScore = rulesPassed / rulesChecked;
  } else {
    patternScore = 0.5; // Neutre si pas assez de données
  }

  // === Score final pondéré ===
  const finalScore = (structureScore * 0.3) + (historicalScore * 0.4) + (patternScore * 0.3);

  return {
    score: Math.round(finalScore * 100) / 100,
    factors: {
      structure: Math.round(structureScore * 100) / 100,
      historical: Math.round(historicalScore * 100) / 100,
      pattern: Math.round(patternScore * 100) / 100
    },
    details: {
      waveCount: waves.length,
      avgAmplitude: Math.round(avgAmplitude * 100) / 100,
      correctPredictions,
      totalPredictions,
      rulesPassed,
      rulesChecked
    }
  };
};
