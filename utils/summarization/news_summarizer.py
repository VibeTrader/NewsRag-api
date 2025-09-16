import os
from typing import List, Dict, Any
from loguru import logger
from datetime import datetime

# Import custom modules - Use the enhanced forex summarizer
from utils.summarization.langchain.enhanced_forex_summarizer import EnhancedForexSummarizer

class NewsSummarizer:
    """Service for generating comprehensive news summaries across multiple articles."""
    
    def __init__(self):
        """Initialize the summarizer with enhanced forex summarizer."""
        # Configuration for cache
        self.cache_size = int(os.getenv("SUMMARY_CACHE_SIZE", "100"))
        self.cache_ttl = int(os.getenv("SUMMARY_CACHE_TTL", "1800"))  # 30 minutes
        
        # Initialize Enhanced LangChain-based forex summarizer
        self.langchain_summarizer = EnhancedForexSummarizer()
        
        logger.info("NewsSummarizer initialized with Enhanced LangChain forex summarizer")
        logger.info(f"Cache configuration: size={self.cache_size}, ttl={self.cache_ttl}s")
    
    async def generate_summary(
        self, 
        articles: List[Dict[str, Any]],
        query: str = "latest forex news",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate a comprehensive summary from multiple news articles.
        
        Args:
            articles: List of news articles from Qdrant
            query: Original search query
            use_cache: Whether to use cached summaries
            
        Returns:
            Dictionary containing summary and analysis
        """
        if not articles:
            logger.warning("No articles provided for summarization")
            return {
                "summary": "No news articles available to summarize.",
                "keyPoints": [],
                "sentiment": {"overall": "neutral", "score": 50},
                "impactLevel": "LOW",
                "currencyPairRankings": [],
                "riskAssessment": {"primaryRisk": "", "correlationRisk": "", "volatilityPotential": ""},
                "tradeManagementGuidelines": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # Use Enhanced LangChain-based forex summarizer
        try:
            logger.info(f"Using Enhanced LangChain-based forex summarizer for query: {query} with {len(articles)} articles")
            summary_result = await self.langchain_summarizer.generate_summary(
                articles=articles,
                query=query,
                use_cache=use_cache
            )
            return summary_result
        except Exception as e:
            logger.error(f"Error in Enhanced LangChain summarizer: {str(e)}")
            raise
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return self.langchain_summarizer.get_cache_stats()