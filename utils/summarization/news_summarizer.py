import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from loguru import logger
import hashlib

# Import custom modules
from utils.summarization.cache_manager import CacheManager

class NewsSummarizer:
    """Service for generating comprehensive news summaries across multiple articles."""
    
    def __init__(self):
        """Initialize the summarizer with Azure OpenAI client."""
        # Import here to avoid dependency issues
        from openai import AzureOpenAI
        import httpx
        
        # Create HTTP client without proxies
        http_client = httpx.Client(
            headers={"Accept-Encoding": "gzip, deflate"}
        )
        
        # Initialize OpenAI client
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("OPENAI_BASE_URL"),
            http_client=http_client
        )
        
        # Configuration
        # Use the GPT model for summarization, falling back to embedding model if not set
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT", os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "gpt-4"))
        self.cache_size = int(os.getenv("SUMMARY_CACHE_SIZE", "100"))
        self.cache_ttl = int(os.getenv("SUMMARY_CACHE_TTL", "1800"))  # 30 minutes
        
        # Initialize cache
        self.cache = CacheManager(
            max_size=self.cache_size,
            default_ttl=self.cache_ttl
        )
        
        logger.info(f"NewsSummarizer initialized with model: {self.model}")
        logger.info(f"Cache configuration: size={self.cache_size}, ttl={self.cache_ttl}s")
        
    def _get_cache_key(self, articles: List[Dict[str, Any]], query: str) -> str:
        """Generate a cache key based on article IDs and query."""
        article_ids = sorted([a.get("id", "") for a in articles])
        hash_input = f"{query}:{'-'.join(article_ids)}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
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
                "timestamp": datetime.now().isoformat()
            }
            
        # Check cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(articles, query)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached summary for query: {query}")
                return cached_result
        
        # Process articles in batches for efficiency
        processed_articles = await self._prepare_articles(articles)
        
        # Generate the summary using Azure OpenAI and market analysis
        summary_result = await self._generate_enhanced_summary(processed_articles, query)
        
        # Update cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(articles, query)
            self.cache.set(cache_key, summary_result)
            logger.debug(f"Cached summary for key: {cache_key}")
            
        return summary_result
    
    async def _prepare_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare articles for summarization by extracting key info."""
        processed_articles = []
        max_articles = min(len(articles), 20)  # Limit to top 20 articles
        
        logger.info(f"Processing {max_articles} articles for summarization")
        
        for article in articles[:max_articles]:
            payload = article.get("payload", {})
            processed_articles.append({
                "id": article.get("id", ""),
                "score": article.get("score", 0),
                "title": payload.get("title", "Untitled"),
                "source": payload.get("source", "Unknown"),
                "publishDate": payload.get("publishDatePst", ""),
                "content": payload.get("content", "")[:3000]  # Truncate to first 3000 chars
            })
            
        return processed_articles
        
    async def _generate_enhanced_summary(
        self, 
        articles: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """Generate summary with GPT."""
        # Generate base summary with GPT
        gpt_result = await self._call_gpt_for_summary(articles, query)
        logger.debug(f"Generated summary for query: {query}")
        
        # Create a properly formatted response
        formatted_result = {
            "summary": gpt_result.get("summary", ""),
            "keyPoints": gpt_result.get("keyPoints", []),
            "currencyPairRankings": gpt_result.get("currencyPairRankings", []),
            "riskAssessment": gpt_result.get("riskAssessment", {}),
            "tradeManagementGuidelines": gpt_result.get("tradeManagementGuidelines", []),
            "marketConditions": gpt_result.get("marketConditions", ""),
            "sentiment": gpt_result.get("sentiment", {"overall": "neutral", "score": 50}),
            "impactLevel": gpt_result.get("impactLevel", "MEDIUM"),
            "timestamp": gpt_result.get("timestamp", datetime.now().isoformat())
        }
        
        return formatted_result

    async def _call_gpt_for_summary(
        self, 
        articles: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """Generate base summary using Azure OpenAI."""
        # Create a structured input for GPT
        articles_text = ""
        for idx, article in enumerate(articles, 1):
            articles_text += f"ARTICLE {idx}:\nTitle: {article['title']}\n"
            articles_text += f"Source: {article['source']}\n"
            articles_text += f"Date: {article['publishDate']}\n"
            articles_text += f"Content: {article['content'][:1000]}...\n\n"
        
        # Create prompt for GPT that matches the desired format
        system_prompt = """You are a financial news analyst specializing in forex markets. 
        Analyze the provided news articles and create a comprehensive forex market analysis with EXACTLY this structure and format:

        1. Start with "**  Executive Summary**" followed by 2-3 sentences on current market conditions. Use bold formatting (**text**) for important sentiment indicators like **Neutral to Slightly Bullish** or **Bearish/Negative**, and for currency pair names like **EUR/USD**.
        
        2. Continue with "**Currency Pair Rankings**" and then list 4 major currency pairs with detailed analysis for each:
           - Format each as "**CURRENCY_PAIR** (Rank: X/10)" where X is a number from 1-10, can include decimal points (e.g. 7.5/10)
           - Include "   * Fundamental Outlook: Y%" where Y is 0-100 (three spaces before the asterisk)
           - Include "   * Sentiment Outlook: Z%" where Z is 0-100 (three spaces before the asterisk)
           - Include "   * Rationale: [detailed explanation with specific market factors]" (three spaces before the asterisk)
           - Each new currency pair starts on a new line with no extra line between bullet points
           - MUST include major pairs such as EUR/USD, USD/JPY, GBP/USD, and AUD/USD
        
        3. Include "**Risk Assessment:**" section with:
           - "   * Primary Risk: [description]" (three spaces before the asterisk)
           - "   * Correlation Risk: [description]" (three spaces before the asterisk)
           - "   * Volatility Potential: [description]" (three spaces before the asterisk)
        
        4. End with "**Trade Management Guidelines:**" followed by a paragraph that includes recommendations. 
           Use bold formatting for currency pair names mentioned in the guidelines.

        Focus on extracting specific details and insights from the articles. Use specific economic data points, price levels, and market trends from the articles.

        Your analysis MUST be comprehensive and include ALL sections mentioned above with specific, detailed information extracted from the articles. 
        Never use generic statements or fill in missing information with placeholder text.
        Use only factual information from the provided articles.

        DO NOT number any lists or sections in the output. Use only the exact formatting specified above.
        """
        
        user_prompt = f"Search query: {query}\n\nArticles to analyze:\n\n{articles_text}"
        
        # Call Azure OpenAI without any fallback
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # Get the response text
        response_text = response.choices[0].message.content.strip()
        
        # Parse the response into a structured format
        parsed_result = self._parse_structured_response(response_text)
        
        # Add timestamp
        parsed_result["timestamp"] = datetime.now().isoformat()
        
        # Clean up the formatted text by removing code block markers if present
        formatted_text = response_text
        formatted_text = formatted_text.replace('```', '')
        
        # Add raw text (so we can return it directly for formatting)
        parsed_result["formatted_text"] = formatted_text
        
        return parsed_result
    

    
    def _parse_structured_response(self, text: str) -> Dict[str, Any]:
        """Parse the structured text response into a JSON format."""
        try:
            # Initialize the result structure
            result = {
                "summary": "",
                "keyPoints": [],
                "currencyPairRankings": [],
                "riskAssessment": {
                    "primaryRisk": "",
                    "correlationRisk": "",
                    "volatilityPotential": ""
                },
                "tradeManagementGuidelines": [],
                "sentiment": {"overall": "neutral", "score": 50},
                "impactLevel": "MEDIUM"
            }
            
            # Extract Executive Summary
            exec_summary_match = re.search(r'\*\*Executive Summary\*\*(.*?)(?=\*\*Currency Pair Rankings|\*\*Risk Assessment|$)', text, re.DOTALL)
            if exec_summary_match:
                result["summary"] = exec_summary_match.group(1).strip()
            
            # Extract Currency Pair Rankings
            pairs_section_match = re.search(r'\*\*Currency Pair Rankings\*\*(.*?)(?=\*\*Risk Assessment|$)', text, re.DOTALL)
            if pairs_section_match:
                pairs_section = pairs_section_match.group(1)
                
                # Extract individual pairs
                pair_matches = re.finditer(r'\*\*([\w/]+)\*\* \(Rank: (\d+)/(\d+)\)(.*?)(?=\*\*[\w/]+\*\* \(Rank:|\*\*Risk Assessment|\*\*Trade Management|$)', pairs_section, re.DOTALL)
                
                for match in pair_matches:
                    pair_name = match.group(1)
                    rank = int(match.group(2))
                    max_rank = int(match.group(3))
                    pair_content = match.group(4)
                    
                    # Extract outlook percentages
                    fundamental_match = re.search(r'Fundamental Outlook: (\d+)%', pair_content)
                    sentiment_match = re.search(r'Sentiment Outlook: (\d+)%', pair_content)
                    rationale_match = re.search(r'Rationale: (.*?)(?=\*|\n\n|$)', pair_content, re.DOTALL)
                    
                    fundamental = int(fundamental_match.group(1)) if fundamental_match else 50
                    sentiment = int(sentiment_match.group(1)) if sentiment_match else 50
                    rationale = rationale_match.group(1).strip() if rationale_match else ""
                    
                    # Add to pairs list
                    result["currencyPairRankings"].append({
                        "pair": pair_name,
                        "rank": rank,
                        "maxRank": max_rank,
                        "fundamentalOutlook": fundamental,
                        "sentimentOutlook": sentiment,
                        "rationale": rationale
                    })
            
            # Extract Risk Assessment
            risk_section_match = re.search(r'\*\*Risk Assessment:\*\*(.*?)(?=\*\*Trade Management|$)', text, re.DOTALL)
            if risk_section_match:
                risk_section = risk_section_match.group(1)
                
                # Extract primary risk
                primary_risk_match = re.search(r'Primary Risk: (.*?)(?=\*|Correlation Risk:|$)', risk_section, re.DOTALL)
                if primary_risk_match:
                    result["riskAssessment"]["primaryRisk"] = primary_risk_match.group(1).strip()
                
                # Extract correlation risk
                correlation_risk_match = re.search(r'Correlation Risk: (.*?)(?=\*|Volatility Potential:|$)', risk_section, re.DOTALL)
                if correlation_risk_match:
                    result["riskAssessment"]["correlationRisk"] = correlation_risk_match.group(1).strip()
                
                # Extract volatility potential
                volatility_match = re.search(r'Volatility Potential: (.*?)(?=\*|$)', risk_section, re.DOTALL)
                if volatility_match:
                    result["riskAssessment"]["volatilityPotential"] = volatility_match.group(1).strip()
            
            # Extract Trade Management Guidelines
            guidelines_match = re.search(r'\*\*Trade Management Guidelines:\*\*(.*?)$', text, re.DOTALL)
            if guidelines_match:
                guidelines_text = guidelines_match.group(1).strip()
                
                # Split by line breaks and bullet points
                lines = re.split(r'\n+', guidelines_text)
                for line in lines:
                    line = re.sub(r'^\s*\*\s*', '', line).strip()
                    if line:
                        result["tradeManagementGuidelines"].append(line)
            
            # Determine overall sentiment
            sentiment_score = 50  # Default neutral
            sentiment_category = "neutral"
            
            if result["currencyPairRankings"]:
                # Calculate average sentiment from currency pairs
                total_sentiment = sum(pair["sentimentOutlook"] for pair in result["currencyPairRankings"])
                sentiment_score = total_sentiment // len(result["currencyPairRankings"])
                
                if sentiment_score >= 70:
                    sentiment_category = "bullish"
                elif sentiment_score <= 30:
                    sentiment_category = "bearish"
            
            result["sentiment"] = {
                "overall": sentiment_category,
                "score": sentiment_score
            }
            
            # Determine impact level
            if "high" in result["summary"].lower() or sentiment_score >= 80 or sentiment_score <= 20:
                result["impactLevel"] = "HIGH"
            elif "low" in result["summary"].lower() or (40 <= sentiment_score <= 60):
                result["impactLevel"] = "LOW"
            else:
                result["impactLevel"] = "MEDIUM"
            
            # Extract key points from the summary
            sentences = re.split(r'(?<=[.!?])\s+', result["summary"])
            result["keyPoints"] = [s.strip() for s in sentences if len(s.strip()) > 10][:3]
            
            # If we couldn't extract key points, add a default one
            if not result["keyPoints"]:
                result["keyPoints"] = ["Market analysis based on latest financial news"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing structured response: {e}")
            logger.error(f"Original text: {text}")
            
            # Return a simplified fallback structure
            return {
                "summary": text[:500] if text else "Unable to generate market analysis",
                "keyPoints": ["Error parsing structured response"],
                "currencyPairRankings": [],
                "riskAssessment": {
                    "primaryRisk": "Unknown",
                    "correlationRisk": "Unknown",
                    "volatilityPotential": "Unknown"
                },
                "tradeManagementGuidelines": [],
                "sentiment": {"overall": "neutral", "score": 50},
                "impactLevel": "MEDIUM"
            }
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return self.cache.get_stats()