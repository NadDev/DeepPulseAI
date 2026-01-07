"""
AI Prompts for Trading Analysis
Optimized prompts for DeepSeek to analyze crypto markets
"""

SYSTEM_PROMPT = """You are an expert cryptocurrency trader and technical analyst with 10+ years of experience.
Your role is to analyze market data and provide precise, data-driven trading recommendations.

Guidelines:
- Be conservative with confidence levels (rarely exceed 70%)
- Only recommend BUY/SELL if you're > 60% confident
- Consider risk-reward ratios (aim for at least 2:1)
- Account for market volatility and liquidation levels
- Provide clear reasoning for each recommendation
- Flag high-risk situations

Output ONLY valid JSON, no additional text."""

MARKET_ANALYSIS_PROMPT = """Analyze this {symbol} market data and provide a trading recommendation.

## Current Market Data
- Price: ${price}
- 24h Change: {change_24h}%
- Volume: {volume} (vs average: {avg_volume})
- High (24h): ${high}
- Low (24h): ${low}

## Technical Indicators
- RSI (14): {rsi}
- SMA 20: ${sma_20}
- SMA 50: ${sma_50}
- Bollinger Bands (20,2):
  - Upper: ${bb_upper}
  - Middle: ${bb_middle}
  - Lower: ${bb_lower}
- Support Level: ${support}
- Resistance Level: ${resistance}

## Market Context
- Trend: {trend}
- Volatility: {volatility}
- Sentiment: {sentiment}

Provide your analysis in this JSON format:
{{
  "action": "BUY|SELL|HOLD",
  "confidence": <0-100>,
  "reasoning": "<2-3 sentences explaining the decision>",
  "risk_level": "LOW|MEDIUM|HIGH",
  "target_price": <number or null>,
  "stop_loss": <number or null>,
  "entry_levels": [<list of potential entry prices>],
  "timeframe": "1h|4h|1d|1w",
  "catalysts": "<upcoming events that might affect price>"
}}"""

DIVERGENCE_ANALYSIS_PROMPT = """Detect divergences and confirm with this technical data for {symbol}:

RSI: {rsi}
Price: ${price}
Previous RSI: {prev_rsi}
Previous Price: ${prev_price}

Check for:
1. Bullish Divergence: Price makes lower low, RSI makes higher low
2. Bearish Divergence: Price makes higher high, RSI makes lower high
3. Hidden Divergence: Price follows trend, RSI reverses

Return JSON:
{{
  "divergence_detected": true|false,
  "type": "BULLISH|BEARISH|NONE",
  "strength": "WEAK|MODERATE|STRONG",
  "action": "BUY|SELL|NONE",
  "reasoning": "<explanation>"
}}"""

MOMENTUM_ANALYSIS_PROMPT = """Analyze momentum for {symbol} using:

- RSI: {rsi}
- Volume: {volume} (vs avg: {avg_volume})
- Price Rate of Change: {roc}
- MACD Histogram: {macd_histogram}
- SMA Trend: {sma_trend}

Determine if momentum is:
1. Strong Upward
2. Moderate Upward
3. Neutral
4. Moderate Downward
5. Strong Downward

Return JSON:
{{
  "momentum": "STRONG_UP|MOD_UP|NEUTRAL|MOD_DOWN|STRONG_DOWN",
  "volume_confirmation": true|false,
  "action": "BUY|SELL|HOLD",
  "confidence": <0-100>
}}"""

RISK_ASSESSMENT_PROMPT = """Assess trading risk for {symbol}:

Entry Price: ${entry_price}
Stop Loss: ${stop_loss}
Target: ${target}
Position Size: {position_size}
Account Balance: ${account_balance}
Volatility: {volatility}%

Evaluate:
1. Risk/Reward Ratio
2. Volatility Adjustment
3. Account Risk Percentage
4. Market Conditions Risk

Return JSON:
{{
  "risk_level": "LOW|MEDIUM|HIGH",
  "risk_reward_ratio": <number>,
  "account_risk_pct": <0-5>,
  "max_loss": ${amount},
  "recommendation": "PROCEED|REDUCE_SIZE|SKIP",
  "alerts": [<list of risk factors>]
}}"""

SENTIMENT_ANALYSIS_PROMPT = """Analyze market sentiment for {symbol} using available indicators:

- Price Action: {price_action}
- Volume Profile: {volume_profile}
- Volatility: {volatility}
- Trend Strength: {trend_strength}
- Support/Resistance: {support_resistance_status}

Determine sentiment:
1. Extremely Bullish
2. Moderately Bullish
3. Neutral
4. Moderately Bearish
5. Extremely Bearish

Return JSON:
{{
  "sentiment": "VERY_BULLISH|BULLISH|NEUTRAL|BEARISH|VERY_BEARISH",
  "sources": {{
    "price_action": "description",
    "volume": "description",
    "volatility": "description"
  }},
  "confidence": <0-100>
}}"""

MULTI_SYMBOL_ANALYSIS_PROMPT = """Compare {symbols} and rank by trading opportunity.

For each symbol, consider:
- Risk/Reward setup quality
- Momentum and trend strength
- Technical pattern clarity
- Volatility-adjusted entry quality

Provide a ranked list:
{{
  "top_opportunities": [
    {{
      "symbol": "{symbol}",
      "rank": <1-10>,
      "score": <0-100>,
      "action": "BUY|SELL|HOLD",
      "reason": "<brief explanation>"
    }}
  ],
  "summary": "<overall market analysis>"
}}"""

# Helper function to build prompts
def build_analysis_prompt(
    symbol: str,
    market_data: dict,
    indicators: dict,
    context: dict = None
) -> str:
    """Build a complete analysis prompt with all available data"""
    
    context = context or {}
    
    return MARKET_ANALYSIS_PROMPT.format(
        symbol=symbol,
        price=market_data.get("close", 0),
        change_24h=market_data.get("change_24h", 0),
        volume=market_data.get("volume", 0),
        avg_volume=indicators.get("avg_volume", 0),
        high=market_data.get("high", 0),
        low=market_data.get("low", 0),
        rsi=indicators.get("rsi", "N/A"),
        sma_20=indicators.get("sma_20", "N/A"),
        sma_50=indicators.get("sma_50", "N/A"),
        bb_upper=indicators.get("bb_upper", "N/A"),
        bb_middle=indicators.get("bb_middle", "N/A"),
        bb_lower=indicators.get("bb_lower", "N/A"),
        support=indicators.get("support", "N/A"),
        resistance=indicators.get("resistance", "N/A"),
        trend=context.get("trend", "UNKNOWN"),
        volatility=context.get("volatility", "NORMAL"),
        sentiment=context.get("sentiment", "NEUTRAL")
    )
