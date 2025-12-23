"""
Sentiment Analysis Service
Analyzes market sentiment from various sources
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Analyzes market sentiment from various sources
    - Twitter/X mentions
    - Reddit discussions
    - News sentiment
    - Social signals
    """
    
    # Sentiment score thresholds
    VERY_BULLISH = 0.7
    BULLISH = 0.4
    NEUTRAL = -0.4
    BEARISH = -0.7
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def get_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive sentiment analysis for a symbol
        
        Args:
            symbol: Cryptocurrency symbol (BTC, ETH, etc.)
            
        Returns:
            Dictionary with sentiment scores and indicators
        """
        sentiment_data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0.0,  # -1 to 1
            "social_score": 0.0,
            "news_score": 0.0,
            "sentiment_label": "neutral",
            "components": {}
        }
        
        try:
            # Get sentiment components
            sentiment_data["components"]["social"] = await self._get_social_sentiment(symbol)
            sentiment_data["components"]["news"] = await self._get_news_sentiment(symbol)
            
            # Calculate overall score
            scores = [
                sentiment_data["components"]["social"].get("score", 0),
                sentiment_data["components"]["news"].get("score", 0)
            ]
            
            sentiment_data["overall_score"] = sum(scores) / len(scores) if scores else 0
            sentiment_data["sentiment_label"] = self._label_sentiment(sentiment_data["overall_score"])
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {str(e)}")
            sentiment_data["error"] = str(e)
        
        return sentiment_data
    
    async def _get_social_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get sentiment from social media (Twitter, Reddit)
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Social sentiment data
        """
        social_data = {
            "score": 0.0,
            "twitter_mentions": 0,
            "reddit_posts": 0,
            "trending": False,
            "sources": []
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Lunarcrush API (example - would need API key)
                # This is a mock implementation
                
                # Simulate getting mention counts
                coin_name = self._get_coin_name(symbol)
                
                social_data["twitter_mentions"] = self._simulate_mention_count(coin_name)
                social_data["reddit_posts"] = self._simulate_reddit_posts(coin_name)
                social_data["trending"] = social_data["twitter_mentions"] > 10000
                
                # Calculate social score based on activity
                if social_data["twitter_mentions"] > 50000:
                    social_data["score"] = 0.6
                elif social_data["twitter_mentions"] > 10000:
                    social_data["score"] = 0.3
                elif social_data["twitter_mentions"] > 1000:
                    social_data["score"] = 0.1
                else:
                    social_data["score"] = -0.2
        
        except Exception as e:
            logger.error(f"Error getting social sentiment: {str(e)}")
            social_data["error"] = str(e)
        
        return social_data
    
    async def _get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get sentiment from news sources
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            News sentiment data
        """
        news_data = {
            "score": 0.0,
            "articles_count": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "trending_news": []
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # NewsAPI or CryptoNews API would go here
                # This is a mock implementation
                
                coin_name = self._get_coin_name(symbol)
                
                # Simulate news sentiment
                news_data["articles_count"] = self._simulate_article_count(coin_name)
                
                # Simulate sentiment distribution
                if news_data["articles_count"] > 0:
                    news_data["positive"] = int(news_data["articles_count"] * 0.5)
                    news_data["negative"] = int(news_data["articles_count"] * 0.2)
                    news_data["neutral"] = int(news_data["articles_count"] * 0.3)
                    
                    # Calculate score
                    if news_data["articles_count"] > 0:
                        sentiment_ratio = (news_data["positive"] - news_data["negative"]) / news_data["articles_count"]
                        news_data["score"] = max(-1, min(1, sentiment_ratio))
        
        except Exception as e:
            logger.error(f"Error getting news sentiment: {str(e)}")
            news_data["error"] = str(e)
        
        return news_data
    
    def _label_sentiment(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= self.VERY_BULLISH:
            return "very_bullish"
        elif score >= self.BULLISH:
            return "bullish"
        elif score >= self.NEUTRAL:
            return "neutral"
        elif score >= self.BEARISH:
            return "bearish"
        else:
            return "very_bearish"
    
    def _get_coin_name(self, symbol: str) -> str:
        """Get full coin name from symbol"""
        coin_names = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "ADA": "Cardano",
            "SOL": "Solana",
            "XRP": "Ripple",
            "DOT": "Polkadot",
            "DOGE": "Dogecoin",
            "MATIC": "Polygon",
            "AVAX": "Avalanche",
            "LINK": "Chainlink",
        }
        return coin_names.get(symbol, symbol)
    
    def _simulate_mention_count(self, coin_name: str) -> int:
        """Simulate Twitter mention count (in real app, would use API)"""
        # This would be replaced with real API calls
        import random
        return random.randint(1000, 100000)
    
    def _simulate_reddit_posts(self, coin_name: str) -> int:
        """Simulate Reddit post count (in real app, would use API)"""
        import random
        return random.randint(50, 5000)
    
    def _simulate_article_count(self, coin_name: str) -> int:
        """Simulate news article count (in real app, would use API)"""
        import random
        return random.randint(5, 50)
    
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get the Crypto Fear & Greed Index
        
        Returns:
            Fear & Greed index data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.alternative.me/fng/?limit=1",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("data"):
                        index = data["data"][0]
                        return {
                            "value": int(index["value"]),
                            "classification": index["value_classification"],
                            "timestamp": index["timestamp"]
                        }
        
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed index: {str(e)}")
        
        return {
            "value": 50,
            "classification": "Neutral",
            "timestamp": str(datetime.now())
        }
    
    async def get_whale_alerts(self, symbol: str) -> Dict[str, Any]:
        """
        Get recent whale transaction alerts
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Recent whale activities
        """
        whale_data = {
            "symbol": symbol,
            "recent_transfers": [],
            "large_transactions": 0,
            "whale_sentiment": "neutral"
        }
        
        try:
            # This would integrate with Whale Alert API
            # For now, returning mock data structure
            
            import random
            whale_data["large_transactions"] = random.randint(0, 5)
            
            if whale_data["large_transactions"] > 3:
                whale_data["whale_sentiment"] = "accumulating"
            elif whale_data["large_transactions"] > 0:
                whale_data["whale_sentiment"] = "distributing"
            else:
                whale_data["whale_sentiment"] = "inactive"
        
        except Exception as e:
            logger.error(f"Error getting whale alerts: {str(e)}")
            whale_data["error"] = str(e)
        
        return whale_data


# Global instance
sentiment_analyzer = SentimentAnalyzer()
