#!/usr/bin/env python3
"""
Debug script to analyze DeepSeek responses and why multiple bots are created
Run this to see the FULL response from DeepSeek before parsing
"""

import asyncio
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def analyze_deepseek_flow():
    """Trace the full flow from DeepSeek → Parsing → Bot Creation"""
    
    print("\n" + "="*80)
    print("🔍 DEEPSEEK RESPONSE ANALYSIS")
    print("="*80 + "\n")
    
    print("To debug why 4 bots are created for WALUSDT:\n")
    
    print("STEP 1: Enable full logging in ai_agent.py")
    print("-" * 60)
    print("""
    Add this to _call_deepseek() method (line ~1293):
    
    # Log FULL response from DeepSeek
    logger.info(f"🤖 [DEEPSEEK-FULL-RESPONSE]:")
    logger.info(f"Raw response (first 1000 chars):")
    logger.info(response[:1000])
    logger.info(f"Response contains 'suggested_strategy': {'suggested_strategy' in response}")
    logger.info(f"Response contains 'risk_level': {'risk_level' in response}")
    logger.info(f"Response contains 'signals_summary': {'signals_summary' in response}")
    """)
    
    print("\nSTEP 2: Check what _parse_analysis_response() returns")
    print("-" * 60)
    print("""
    Modify _parse_analysis_response() (line ~1390):
    
    # After: analysis = json.loads(json_str)
    logger.info(f"📊 [PARSED-ANALYSIS] Keys in response: {analysis.keys()}")
    logger.info(f"📊 Has suggested_strategy: {'suggested_strategy' in analysis}")
    logger.info(f"📊 Has risk_level: {'risk_level' in analysis}")
    logger.info(f"Full analysis: {json.dumps(analysis, indent=2)}")
    
    return analysis
    """)
    
    print("\nSTEP 3: Track bot creation decisions")
    print("-" * 60)
    print("""
    Add logging to _select_strategy() (line ~625):
    
    def _select_strategy(self, recommendation: Dict[str, Any]) -> str:
        logger.info(f"🤖 [STRATEGY-SELECT] Recommendation keys: {recommendation.keys()}")
        logger.info(f"   - Has suggested_strategy: {'suggested_strategy' in recommendation}")
        logger.info(f"   - Value: {recommendation.get('suggested_strategy', 'MISSING')}")
        
        if "suggested_strategy" in recommendation and recommendation["suggested_strategy"]:
            # ...existing code
        else:
            logger.warning(f"⚠️ [STRATEGY-SELECT] NO suggested_strategy! Using fallback heuristic")
            # ...fallback code
    """)
    
    print("\nSTEP 4: Verify duplicate check")
    print("-" * 60)
    print("""
    Add logging to _create_ai_bot() before duplicate check (line ~375):
    
    logger.info(f"🤖 [BOT-CREATE] Checking duplicates for {symbol}")
    logger.info(f"   - Strategy: {strategy}")
    logger.info(f"   - Query: user_id={user_id}, status=RUNNING, symbol={symbol}, strategy={strategy}")
    
    duplicate_bot = db.query(Bot).filter(...)
    
    if duplicate_bot:
        logger.warning(f"🚫 [BOT-CREATE] BLOCKED! Found existing: {duplicate_bot.name} ({duplicate_bot.strategy})")
    else:
        logger.info(f"✅ [BOT-CREATE] No duplicate found, creating new bot with {strategy}")
    """)
    
    print("\n" + "="*80)
    print("KEY QUESTIONS TO ANSWER:")
    print("="*80)
    print("""
    1. Does DeepSeek response CONTAIN 'suggested_strategy' field?
       → Check logs for: "Response contains 'suggested_strategy': True/False"
    
    2. Does _parse_analysis_response() INCLUDE 'suggested_strategy' in return?
       → Check logs for: "Has suggested_strategy: True/False"
    
    3. Does _select_strategy() receive 'suggested_strategy'?
       → Check logs for: "Has suggested_strategy: True/False" in recommendation
    
    4. Is each bot created with DIFFERENT strategy?
       → Check logs for different [STRATEGY-SELECT] values each cycle
       
    5. Why doesn't duplicate check block them?
       → Check if Bot.strategy != bot2.strategy (so bypass works)
    """)
    
    print("\n" + "="*80)
    print("EXPECTED BEHAVIOR:")
    print("="*80)
    print("""
    SCENARIO A: DeepSeek suggests same strategy each time
    ────────────────────────────────────────────────────
    T=0min:  suggested_strategy: "mean_reversion" → Creates bot1 (mean_reversion)
    T=5min:  suggested_strategy: "mean_reversion" → Blocks (duplicate)
    T=10min: suggested_strategy: "mean_reversion" → Blocks (duplicate)
    
    Result: 1 bot ✅
    
    SCENARIO B: DeepSeek suggests DIFFERENT strategy each time
    ────────────────────────────────────────────────────────
    T=0min:  suggested_strategy: "mean_reversion" → Creates bot1
    T=5min:  suggested_strategy: "momentum"       → Creates bot2 (different!)
    T=10min: suggested_strategy: "trend_following" → Creates bot3 (different!)
    
    Result: 3 bots (but for valid reasons!)
    
    SCENARIO C: suggested_strategy MISSING from response
    ──────────────────────────────────────────────────
    T=0min:  NO suggested_strategy → Fallback selects "mean_reversion" → Creates bot1
    T=5min:  NO suggested_strategy → Fallback selects "momentum" → Creates bot2
    T=10min: NO suggested_strategy → Fallback selects "trend_following" → Creates bot3
    
    Result: 3 bots for BAD reasons! (random fallback)
    """)
    
    print("\n" + "="*80)
    print("RUN THESE LOGS FOR 20 MINUTES THEN ANALYZE:")
    print("="*80)
    print("""
    docker logs -f crbot-backend 2>&1 | grep -E "\\[DEEPSEEK-FULL|\\[PARSED-ANALYSIS|\\[STRATEGY-SELECT|\\[BOT-CREATE"
    
    Then look for patterns:
    - Are suggested_strategies all SAME or all DIFFERENT?
    - Is duplicate check working? (Are later ones BLOCKED?)
    - What triggers new bot creation?
    """)

if __name__ == "__main__":
    asyncio.run(analyze_deepseek_flow())
