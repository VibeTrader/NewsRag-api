"""
LangChain-based forex market summarizer for NewsRagnarok API.
"""

import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

# Import LangChain components
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.chains import LLMChain

# Import monitoring
try:
    from utils.monitoring import LangChainMonitoring
    langchain_monitoring = LangChainMonitoring()
except ImportError:
    langchain_monitoring = None

from utils.summarization.cache_manager import CacheManager

# Forex summary prompt template
SYSTEM_TEMPLATE = """You are a financial news analyst specializing in forex markets with expertise in identifying currency pairs and market sentiment from news articles.

## ANALYSIS PROCESS
1. First, carefully identify ALL currency pairs mentioned in EACH article
2. For each currency pair, track:
   - Frequency of mentions across all articles
   - Associated sentiment (bearish, neutral, or bullish)
   - Fundamental factors mentioned (economic data, central bank policies, etc.)
   - Technical factors mentioned (support/resistance levels, trends, etc.)

3. Then rank currency pairs based on:
   - Frequency of mentions (higher frequency = more significant)
   - Strength of sentiment indicators
   - Importance of fundamental factors mentioned
   - Recency of the news (more recent news carries more weight)

## OUTPUT FORMAT
Analyze the provided news articles and create a comprehensive forex market analysis with EXACTLY this structure and format:

1. Start with "**Executive Summary**" followed by 2-3 sentences on current market conditions. Use bold formatting (**text**) for important sentiment indicators like **Neutral to Slightly Bullish** or **Bearish/Negative**, and for currency pair names like **EUR/USD**.

2. Continue with "**Currency Pair Rankings**" and then list AT LEAST 4 major currency pairs with detailed analysis for each:
   - Format each as "**CURRENCY_PAIR** (Rank: X/10)" where X is a number from 1-10, can include decimal points (e.g. 7.5/10)
   - Include "   * Fundamental Outlook: Y%" where Y is 0-100 (three spaces before the asterisk)
   - Include "   * Sentiment Outlook: Z%" where Z is 0-100 (three spaces before the asterisk)
   - Include "   * Rationale: [detailed explanation with specific market factors]" (three spaces before the asterisk)
   - Each new currency pair starts on a new line with no extra line between bullet points
   - Prioritize pairs that appear most frequently in the articles, with strongest sentiment signals

3. Include "**Risk Assessment:**" section with:
   - "   * Primary Risk: [description]" (three spaces before the asterisk)
   - "   * Correlation Risk: [description]" (three spaces before the asterisk)
   - "   * Volatility Potential: [description]" (three spaces before the asterisk)

4. End with "**Trade Management Guidelines:**" followed by a paragraph that includes recommendations. 
   Use bold formatting for currency pair names mentioned in the guidelines.

CRITICAL FORMATTING REQUIREMENTS:
- Follow the exact formatting shown in the example output (pay special attention to spacing, asterisks, and bold formatting)
- Extract specific details from the articles including price levels, economic data points, and technical levels
- Never use generic statements or fill in missing information with placeholder text
- Use only factual information from the provided articles
- DO NOT number any lists or sections in the output
- Ensure every currency pair has its sentiment expressed as a percentage between 0-100%
"""

HUMAN_TEMPLATE = """Search query: {query}

Articles to analyze:

{articles}"""

class LangChainForexSummarizer:
    """LangChain-based forex market summarizer for comprehensive news analysis."""
    
    def __init__(self):
        """Initialize the LangChain-based forex summarizer with Azure OpenAI client."""
        # Initialize the LLM
        self.llm = AzureChatOpenAI(
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            api_key=os.getenv("OPENAI_API_KEY"),
            azure_endpoint=os.getenv("OPENAI_BASE_URL"),
            temperature=0.7,
        )
        
        # Create chat prompt template
        system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_TEMPLATE)
        human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE)
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        
        # Create the LLM chain
        self.chain = LLMChain(llm=self.llm, prompt=chat_prompt)
        
        # Add Langfuse monitoring if available
        if langchain_monitoring and langchain_monitoring.enabled:
            self.chain = langchain_monitoring.wrap_chain(self.chain, "forex_summary_chain")
            logger.info("Langfuse monitoring enabled for LangChain forex summarizer")
        
        # Configuration
        self.cache_size = int(os.getenv("SUMMARY_CACHE_SIZE", "100"))
        self.cache_ttl = int(os.getenv("SUMMARY_CACHE_TTL", "1800"))  # 30 minutes
        
        # Initialize cache (reuse existing cache manager)
        self.cache = CacheManager(
            max_size=self.cache_size,
            default_ttl=self.cache_ttl
        )
        
        logger.info(f"LangChainForexSummarizer initialized with model: {os.getenv('AZURE_OPENAI_DEPLOYMENT')}")
        logger.info(f"Cache configuration: size={self.cache_size}, ttl={self.cache_ttl}s")
    
    def _get_cache_key(self, articles: List[Dict[str, Any]], query: str) -> str:
        """Generate a cache key based on article IDs and query."""
        article_ids = sorted([a.get("id", "") for a in articles])
        hash_input = f"{query}:{'-'.join(article_ids)}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    def _format_articles_for_prompt(self, articles: List[Dict[str, Any]]) -> str:
        """Format articles in the structure expected by the prompt template."""
        # Sort articles by date (most recent first if available)
        try:
            sorted_articles = sorted(
                articles, 
                key=lambda x: x.get("payload", {}).get("publishDatePst", "0"), 
                reverse=True
            )
        except:
            sorted_articles = articles
        
        articles_text = ""
        for idx, article in enumerate(sorted_articles, 1):
            payload = article.get("payload", {})
            publish_date = payload.get("publishDatePst", "Unknown date")
            
            articles_text += f"ARTICLE {idx} [Date: {publish_date}]:\n"
            articles_text += f"Title: {payload.get('title', 'Untitled')}\n"
            articles_text += f"Source: {payload.get('source', 'Unknown')}\n"
            articles_text += f"Content: {payload.get('content', '')[:2000]}...\n\n"
        
        return articles_text
    
    def _preprocess_articles_for_currency_pairs(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pre-process articles to highlight currency pair mentions for better detection."""
        # Common currency pairs to scan for
        common_pairs = [
            "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
            "EUR/GBP", "EUR/JPY", "GBP/JPY", "EUR/CHF", "EUR/AUD", "EUR/CAD", "AUD/JPY",
            "EUR/NZD", "USD/INR", "USD/CNY", "USD/HKD", "USD/SGD", "USD/TRY", "USD/ZAR"
        ]
        
        processed_articles = []
        for article in articles:
            # Create a copy of the article
            processed_article = dict(article)
            payload = dict(processed_article.get("payload", {}))
            content = payload.get("content", "")
            
            # Scan for currency pairs and highlight them in the content
            for pair in common_pairs:
                if pair in content:
                    # Highlight the currency pair for better LLM detection
                    content = content.replace(pair, f"[CURRENCY_PAIR: {pair}]")
            
            payload["content"] = content
            processed_article["payload"] = payload
            processed_articles.append(processed_article)
        
        return processed_articles
    
    async def generate_summary(
        self, 
        articles: List[Dict[str, Any]],
        query: str = "latest forex news",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate a comprehensive forex market summary from multiple news articles.
        
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
        
        # Generate cache key before checking cache
        cache_key = None
        if use_cache:
            cache_key = self._get_cache_key(articles, query)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached summary for query: {query}")
                return cached_result
        
        # Process articles for better currency pair detection
        processed_articles = self._preprocess_articles_for_currency_pairs(articles)
        
        # Format articles for prompt
        formatted_articles = self._format_articles_for_prompt(processed_articles)
        
        try:
            # Get the current time before generating summary
            start_time = datetime.now()
            
            # Generate summary using LangChain
            logger.info(f"Generating forex summary with LangChain for {len(articles)} articles")
            
            try:
                # Run the chain with the newer async invoke method
                result = await self.chain.ainvoke({
                    "query": query,
                    "articles": formatted_articles
                })
                
                # Calculate duration
                end_time = datetime.now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Extract the text from the result
                if isinstance(result, dict) and "text" in result:
                    summary_text = result["text"]
                else:
                    summary_text = str(result)
                
                logger.info(f"Generated summary: {len(summary_text)} characters")
                
                # Estimate token usage
                token_usage = {}
                
                # Try to get token usage from LangChain if available
                if hasattr(result, "llm_output") and isinstance(result.llm_output, dict):
                    token_usage = result.llm_output.get("token_usage", {})
                
                # If not available from LangChain, estimate it
                if not token_usage and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        prompt_tokens = langchain_monitoring.langfuse_monitor.count_tokens(formatted_articles)
                        completion_tokens = langchain_monitoring.langfuse_monitor.count_tokens(summary_text)
                        token_usage = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens
                        }
                    except Exception as e:
                        logger.warning(f"Error estimating token usage: {e}")
                        token_usage = {}
            except Exception as e:
                logger.error(f"Error in chain execution: {e}")
                logger.error(f"Error type: {type(e)}")
                raise Exception(f"Error in LangChain execution: {e}")
            
            # Parse the response
            parsed_result = self._parse_structured_response(summary_text)
            
            # Add timestamp and formatted text
            parsed_result["timestamp"] = datetime.now().isoformat()
            parsed_result["formatted_text"] = summary_text
            parsed_result["articleCount"] = len(articles)
            
            # Track metrics in Langfuse if available
            if langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    # Define cache_key to avoid reference errors
                    cache_key = self._get_cache_key(articles, query) if use_cache else None
                    
                    # Get active trace from Langfuse if available
                    trace = None
                    if hasattr(langchain_monitoring.langfuse_monitor.langfuse, "get_current_trace"):
                        try:
                            trace_id = langchain_monitoring.langfuse_monitor.langfuse.get_current_trace()
                            if trace_id:
                                # Create a wrapper trace for the existing trace
                                trace = StatefulTraceClient(
                                    id=trace_id, 
                                    langfuse=langchain_monitoring.langfuse_monitor.langfuse
                                )
                        except Exception:
                            pass
                    
                    # Extract currency pairs for metrics
                    currency_pairs = []
                    if "currencyPairRankings" in parsed_result:
                        currency_pairs = [pair.get("pair", "") for pair in parsed_result["currencyPairRankings"]]
                    
                    # Track summarization metrics
                    if trace:
                        langchain_monitoring.langfuse_monitor.track_summarization_metrics(
                            trace=trace,
                            forex_summary=parsed_result,
                            processing_time_ms=duration_ms,
                            token_usage=token_usage,
                            cache_hit=cached_result is not None,
                            currency_pairs=currency_pairs
                        )
                except Exception as e:
                    logger.warning(f"Error tracking Langfuse metrics: {e}")
            
            # Cache the result if enabled
            if use_cache:
                self.cache.set(cache_key, parsed_result)
                logger.debug(f"Cached summary for key: {cache_key}")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error generating summary with LangChain: {e}")
            raise
    
    def _parse_structured_response(self, text: str) -> Dict[str, Any]:
        """Parse the structured text response into a JSON format."""
        import re
        
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
                pair_matches = re.finditer(r'\*\*([\w/]+)\*\* \(Rank: (\d+(?:\.\d+)?)/(\d+)\)(.*?)(?=\*\*[\w/]+\*\* \(Rank:|\*\*Risk Assessment|\*\*Trade Management|$)', pairs_section, re.DOTALL)
                
                for match in pair_matches:
                    pair_name = match.group(1)
                    rank = float(match.group(2))
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
