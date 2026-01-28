"""
Test script for WatchlistRecommendationEngine
Run: python test_recommendations.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.services.watchlist_recommendation_engine import get_recommendation_engine

async def test_engine():
    print("[TEST] Testing WatchlistRecommendationEngine...")
    
    engine = get_recommendation_engine(SessionLocal)
    
    # Generate recommendations (no user_id needed for testing scoring)
    test_user_id = "00000000-0000-0000-0000-000000000001"  # Fake UUID for test
    
    recommendations = engine.generate_recommendations(
        user_id=test_user_id,
        top_n=5,
        min_score=0
    )
    
    print(f"\n[OK] Generated {len(recommendations)} recommendations:\n")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec.symbol}")
        print(f"   Score: {rec.score:.1f}/100 | Action: {rec.action}")
        print(f"   Momentum: {rec.components.momentum:.0f} | Volume: {rec.components.volume:.0f}")
        print(f"   Volatility: {rec.components.volatility:.0f} | RSI: {rec.components.rsi:.0f}")
        print(f"   Price: ${rec.current_price:,.2f} | 7d: {rec.price_change_7d:+.1f}%")
        print()
    
    # Test DeepSeek reasoning (if API key set)
    if os.getenv("DEEPSEEK_API_KEY"):
        print("[INFO] Testing DeepSeek reasoning...")
        recs_with_reasoning = await engine.generate_reasoning_batch(
            recommendations[:2],  # Just 2 for testing
            max_concurrent=2
        )
        
        for rec in recs_with_reasoning:
            print(f"\n{rec.symbol}: {rec.reasoning}")
    else:
        print("[INFO] DEEPSEEK_API_KEY not set, skipping reasoning test")
    
    print("\n[OK] Test complete!")

if __name__ == "__main__":
    asyncio.run(test_engine())
