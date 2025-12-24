"""
LangChain-based forex market summarizer for NewsRagnarok API.
"""

import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

# Import LangChain components with fallbacks
try:
    # Try modern imports first (LangChain 1.0+)
    from langchain_openai import AzureChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
    from langchain_classic.chains import LLMChain
    logger.info("Using modern LangChain imports")
except ImportError as e:
    try:
        # Fall back to legacy imports (LangChain 0.x)
        from langchain.chat_models import AzureChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
        from langchain_classic.chains import LLMChain
        logger.info("Using legacy LangChain imports")
    except ImportError:
        logger.error("Failed to import LangChain components - functionality will be limited")
        # Create placeholder classes
        class AzureChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass
        
        class LLMChain:
            def __init__(self, *args, **kwargs):
                pass
            async def ainvoke(self, *args, **kwargs):
                return {"text": "LangChain import error: Unable to generate summary"}
        
        class SystemMessagePromptTemplate:
            @staticmethod
            def from_template(template):
                return template
        
        class HumanMessagePromptTemplate:
            @staticmethod
            def from_template(template):
                return template
        
        class ChatPromptTemplate:
            @staticmethod
            def from_messages(messages):
                return messages


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
        """Initialize the LangChain-based forex summarizer."""
        # Configuration for LLM
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.request_timeout = int(os.getenv("LLM_TIMEOUT", "120"))
        
        # Configuration for cache
        self.cache_size = int(os.getenv("SUMMARY_CACHE_SIZE", "100"))
        self.cache_ttl = int(os.getenv("SUMMARY_CACHE_TTL", "1800"))
        
        # Initialize cache (reuse existing cache manager)
        self.cache = CacheManager(
            max_size=self.cache_size,
            default_ttl=self.cache_ttl
        )
        
        self.llm = None
        self.chain = None
        
        logger.info(f"LangChainForexSummarizer initialized (Lazy Loading). Cache: size={self.cache_size}, ttl={self.cache_ttl}s")
    
    def _ensure_initialized(self):
        """Ensure LLM and Chain are initialized."""
        if self.chain is not None:
            return

        try:
            logger.info("Initializing Azure OpenAI LLM components...")
            # Try both environment variable names for API key
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Missing API key: Set either AZURE_OPENAI_API_KEY or OPENAI_API_KEY")
                
            self.llm = AzureChatOpenAI(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                api_key=api_key,
                azure_endpoint=os.getenv("OPENAI_BASE_URL"),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                request_timeout=self.request_timeout,
            )
            
            # Create chat prompt template
            system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_TEMPLATE)
            human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE)
            chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
            
            # Create the LLM chain
            self.chain = LLMChain(llm=self.llm, prompt=chat_prompt)
            
            # Add Langfuse monitoring if available
            if langchain_monitoring and langchain_monitoring.enabled:
                try:
                    self.chain = langchain_monitoring.wrap_chain(self.chain, "forex_summary_chain")
                    logger.info("Langfuse monitoring enabled for LangChain forex summarizer")
                except Exception as e:
                    logger.warning(f"Failed to set up Langfuse monitoring: {e}")
                    
            logger.info(f"LLM initialized with deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT')}")
            
        except Exception as e:
            logger.error(f"Error initializing Azure OpenAI LLM: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {e}")
    
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
        except Exception as e:
            logger.warning(f"Error sorting articles by date: {e}")
            sorted_articles = articles
        
        # Batch processing: limit the number of articles to improve performance
        # Use max_articles to control batch size
        max_articles = int(os.getenv("MAX_SUMMARY_ARTICLES", "100"))
        if len(sorted_articles) > max_articles:
            logger.info(f"Limiting articles for summary from {len(sorted_articles)} to {max_articles}")
            selected_articles = sorted_articles[:max_articles]
        else:
            selected_articles = sorted_articles
        
        # Limit content size per article to avoid token limits
        max_content_chars = int(os.getenv("MAX_ARTICLE_CONTENT_CHARS", "1500"))
        
        # Calculate optimal content size based on article count
        # If we have many articles, reduce content size further
        dynamic_content_size = max(800, int(max_content_chars * (10 / len(selected_articles))))
        
        logger.info(f"Using dynamic content size of {dynamic_content_size} chars for {len(selected_articles)} articles")
        
        articles_text = ""
        for idx, article in enumerate(selected_articles, 1):
            payload = article.get("payload", {})
            publish_date = payload.get("publishDatePst", "Unknown date")
            
            articles_text += f"ARTICLE {idx} [Date: {publish_date}]:\n"
            articles_text += f"Title: {payload.get('title', 'Untitled')}\n"
            articles_text += f"Source: {payload.get('source', 'Unknown')}\n"
            
            # Use dynamic content size
            content = payload.get('content', '')
            articles_text += f"Content: {content[:dynamic_content_size]}...\n\n"
        
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
        
        # Ensure LLM is initialized
        self._ensure_initialized()
        
        # Create a trace for Langfuse at the beginning
        trace_id = None
        if langchain_monitoring and langchain_monitoring.langfuse_monitor and langchain_monitoring.langfuse_monitor.enabled:
            try:
                trace_id = langchain_monitoring.langfuse_monitor.create_trace(
                    name=f"forex_summary:{query}",
                    metadata={
                        "query": query,
                        "article_count": len(articles),
                        "use_cache": use_cache
                    },
                    tags=["forex", "summary"],
                    input=query  # Explicitly set input
                )
                logger.info(f"Created Langfuse trace for summarization: {trace_id}")
            except Exception as e:
                logger.warning(f"Error creating Langfuse trace: {e}")
        
        # Generate cache key before checking cache
        cache_key = None
        if use_cache:
            cache_key = self._get_cache_key(articles, query)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached summary for query: {query}")
                
                # Log cache hit to Langfuse if trace exists
                if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        langchain_monitoring.langfuse_monitor.track_span(
                            trace=trace_id,
                            name="cache_hit",
                            metadata={
                                "query": query,
                                "cache_key": cache_key
                            },
                            status="success",
                            input=query,
                            output="Retrieved from cache"
                        )
                        
                        # Update trace with output using track_span instead of update_trace
                        langchain_monitoring.langfuse_monitor.track_span(
                            trace=trace_id,
                            name="cache_result",
                            metadata={
                                "from_cache": True,
                                "cache_key": cache_key
                            },
                            status="success",
                            input=query,
                            output=cached_result.get("formatted_text", cached_result.get("summary", ""))
                        )
                    except Exception as e:
                        logger.warning(f"Error logging cache hit to Langfuse: {e}")
                
                return cached_result
        
        # Process articles for better currency pair detection
        processed_articles = self._preprocess_articles_for_currency_pairs(articles)
        
        # Format articles for prompt
        formatted_articles = self._format_articles_for_prompt(processed_articles)
        
        try:
            # Get the current time before generating summary
            start_time = datetime.now()
            
            # Track preprocessing in Langfuse
            if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    langchain_monitoring.langfuse_monitor.track_span(
                        trace=trace_id,
                        name="preprocessing",
                        metadata={
                            "article_count": len(articles),
                            "selected_count": min(len(articles), int(os.getenv("MAX_SUMMARY_ARTICLES", "15"))),
                            "formatted_chars": len(formatted_articles)
                        },
                        status="success",
                        input=query,
                        output=f"Processed {len(articles)} articles for summarization"
                    )
                except Exception as e:
                    logger.warning(f"Error tracking preprocessing in Langfuse: {e}")
            
            # Generate summary using LangChain
            logger.info(f"Generating forex summary with LangChain for {len(articles)} articles")
            
            try:
                # Start LLM call span in Langfuse
                llm_span_id = None
                if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        llm_span_id = langchain_monitoring.langfuse_monitor.track_span(
                            trace=trace_id,
                            name="llm_call",
                            metadata={
                                "model": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                                "temperature": float(os.getenv("TEMPERATURE", "0.7")),
                                "input_chars": len(formatted_articles)
                            },
                            status="running",
                            input=formatted_articles
                        )
                    except Exception as e:
                        logger.warning(f"Error starting LLM call span in Langfuse: {e}")
                
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
                
                logger.info(f"Generated summary: {len(summary_text)} characters in {duration_ms}ms")
                
                # Update LLM call span in Langfuse
                if llm_span_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        langchain_monitoring.langfuse_monitor.track_span(
                            trace=trace_id,
                            name="llm_call_complete",
                            metadata={
                                "duration_ms": duration_ms,
                                "output_chars": len(summary_text),
                                "model": os.getenv("AZURE_OPENAI_DEPLOYMENT")
                            },
                            status="success",
                            input=formatted_articles,
                            output=summary_text
                        )
                    except Exception as e:
                        logger.warning(f"Error updating LLM call span in Langfuse: {e}")
                
                # Estimate token usage
                token_usage = {}
                
                # Try to get token usage from LangChain if available
                if hasattr(result, "llm_output") and isinstance(result.llm_output, dict):
                    token_usage = result.llm_output.get("token_usage", {})
                
                # If not available from LangChain, estimate it
                if not token_usage and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        # Use tiktoken for better estimation if available
                        try:
                            import tiktoken
                            encoding = tiktoken.encoding_for_model("gpt-4")
                            prompt_tokens = len(encoding.encode(formatted_articles))
                            completion_tokens = len(encoding.encode(summary_text))
                        except ImportError:
                            # Fallback to simple estimation
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
                
                # Update Langfuse trace with error
                if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                    try:
                        langchain_monitoring.langfuse_monitor.track_span(
                            trace=trace_id,
                            name="llm_error",
                            metadata={
                                "error": str(e),
                                "error_type": str(type(e))
                            },
                            status="error",
                            input=formatted_articles,
                            output=f"Error: {str(e)}"
                        )
                    except Exception as trace_error:
                        logger.warning(f"Error updating Langfuse trace with error: {trace_error}")
                
                raise Exception(f"Error in LangChain execution: {e}")
            
            # Start parsing span in Langfuse
            parsing_span_id = None
            if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    parsing_span_id = langchain_monitoring.langfuse_monitor.track_span(
                        trace=trace_id,
                        name="parsing_start",
                        metadata={
                            "summary_chars": len(summary_text)
                        },
                        status="running",
                        input=summary_text
                    )
                except Exception as e:
                    logger.warning(f"Error starting parsing span in Langfuse: {e}")
            
            # Parse the response
            parsed_result = self._parse_structured_response(summary_text)
            
            # Update parsing span in Langfuse
            if parsing_span_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    langchain_monitoring.langfuse_monitor.track_span(
                        trace=trace_id,
                        name="parsing_complete",
                        metadata={
                            "parsed_fields": list(parsed_result.keys()),
                            "currency_pairs": len(parsed_result.get("currencyPairRankings", [])),
                            "key_points": len(parsed_result.get("keyPoints", []))
                        },
                        status="success",
                        input=summary_text,
                        output=str(parsed_result)
                    )
                except Exception as e:
                    logger.warning(f"Error updating parsing span in Langfuse: {e}")
            
            # Add timestamp and formatted text
            parsed_result["timestamp"] = datetime.now().isoformat()
            parsed_result["formatted_text"] = summary_text
            parsed_result["articleCount"] = len(articles)
            
            # Ensure all required fields are present and non-empty
            # This ensures no API client will receive empty fields
            
            # Ensure summary is not empty (use formatted_text if needed)
            if not parsed_result.get("summary"):
                logger.warning("Empty summary field after parsing - using formatted text")
                if summary_text:
                    first_paragraph = summary_text.split('\n\n')[0] if '\n\n' in summary_text else summary_text[:500]
                    parsed_result["summary"] = first_paragraph.strip()
                else:
                    parsed_result["summary"] = "Analysis of current forex market conditions."
            
            # Ensure keyPoints is not empty
            if not parsed_result.get("keyPoints"):
                logger.warning("Empty keyPoints field after parsing - adding default")
                parsed_result["keyPoints"] = ["Market analysis based on latest financial news"]
            
            # Ensure currencyPairRankings is not empty
            if not parsed_result.get("currencyPairRankings") or len(parsed_result["currencyPairRankings"]) == 0:
                logger.warning("Empty currencyPairRankings field after parsing - adding default")
                # Try to extract currency pairs from formatted_text
                if summary_text:
                    # Look for common currency pairs in the text
                    common_pairs = ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD"]
                    for pair in common_pairs:
                        if pair in summary_text:
                            parsed_result["currencyPairRankings"] = [{
                                "pair": pair,
                                "rank": 5.0,
                                "maxRank": 10,
                                "fundamentalOutlook": 50,
                                "sentimentOutlook": 50,
                                "rationale": "Mentioned in analysis. See formatted text for details."
                            }]
                            break
                
                # If still empty, add a default entry
                if not parsed_result.get("currencyPairRankings") or len(parsed_result["currencyPairRankings"]) == 0:
                    parsed_result["currencyPairRankings"] = [{
                        "pair": "EUR/USD",
                        "rank": 5.0,
                        "maxRank": 10,
                        "fundamentalOutlook": 50,
                        "sentimentOutlook": 50,
                        "rationale": "Default entry. See formatted text for full analysis."
                    }]
            
            # Ensure riskAssessment fields are not empty
            if not parsed_result.get("riskAssessment"):
                parsed_result["riskAssessment"] = {}
            
            risk_fields = ["primaryRisk", "correlationRisk", "volatilityPotential"]
            for field in risk_fields:
                if field not in parsed_result["riskAssessment"] or not parsed_result["riskAssessment"][field]:
                    parsed_result["riskAssessment"][field] = "See formatted text for details"
            
            # Ensure tradeManagementGuidelines is not empty
            if not parsed_result.get("tradeManagementGuidelines") or len(parsed_result["tradeManagementGuidelines"]) == 0:
                logger.warning("Empty tradeManagementGuidelines field after parsing - adding default")
                parsed_result["tradeManagementGuidelines"] = ["See formatted text for detailed trading guidelines"]
            
            # Extract currency pairs for metrics after ensuring they exist
            currency_pairs = []
            if "currencyPairRankings" in parsed_result:
                currency_pairs = [pair.get("pair", "") for pair in parsed_result["currencyPairRankings"]]
            
            # Update trace in Langfuse with final result
            if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    # Use track_span instead of update_trace (which doesn't exist in some SDK versions)
                    langchain_monitoring.langfuse_monitor.track_span(
                        trace=trace_id,
                        name="summarization_metrics",
                        metadata={
                            "processing_time_ms": duration_ms,
                            "token_usage": token_usage,
                            "currency_pairs": currency_pairs,
                            "sentiment_score": parsed_result.get("sentiment", {}).get("score", 0),
                            "impact_level": parsed_result.get("impactLevel", "UNKNOWN"),
                            "article_count": len(articles)
                        },
                        status="success",
                        input=query,
                        output=summary_text
                    )
                except Exception as e:
                    logger.warning(f"Error updating Langfuse trace: {e}")
            
            # Cache the result if enabled
            if use_cache and cache_key:
                self.cache.set(cache_key, parsed_result)
                logger.debug(f"Cached summary for key: {cache_key}")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error generating summary with LangChain: {e}")
            
            # Update Langfuse trace with error
            if trace_id and langchain_monitoring and langchain_monitoring.langfuse_monitor:
                try:
                    langchain_monitoring.langfuse_monitor.track_span(
                        trace=trace_id,
                        name="summary_error",
                        metadata={
                            "error": str(e),
                            "error_type": str(type(e))
                        },
                        status="error",
                        input=query,
                        output=f"Error: {str(e)}"
                    )
                except Exception as trace_error:
                    logger.warning(f"Error updating Langfuse trace with error: {trace_error}")
            
            raise
    
    def _parse_structured_response(self, text: str) -> Dict[str, Any]:
        """Parse the structured text response into a JSON format.
        
        This improved version uses more flexible regex patterns and ensures no empty fields.
        """
        import re
        
        try:
            # Log the first part of the text for debugging
            logger.debug(f"Parsing text (first 200 chars): {text[:200]}")
            
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
            
            # More flexible regex patterns that work with or without asterisks
            # Extract Executive Summary - match both with and without asterisks
            exec_summary_patterns = [
                r'(?:Executive Summary|Summary)(?:\s*\n|\s*:)(.*?)(?=(?:Currency Pair Rankings|Risk Assessment|\n\n\w))',
                r'\*\*Executive Summary\*\*(.*?)(?=\*\*Currency Pair Rankings|\*\*Risk Assessment|$)',
                r'Executive Summary(.*?)(?=Currency Pair Rankings|Risk Assessment|$)'
            ]
            
            for pattern in exec_summary_patterns:
                exec_summary_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if exec_summary_match:
                    result["summary"] = exec_summary_match.group(1).strip()
                    logger.debug(f"Found summary with pattern: {pattern[:30]}...")
                    break
            
            # If still no summary, use the first paragraph
            if not result["summary"] and text:
                paragraphs = text.split('\n\n')
                if paragraphs:
                    result["summary"] = paragraphs[0].strip()
                    logger.debug("Using first paragraph as summary")
            
            # Extract Currency Pair Rankings with more flexible patterns
            pairs_section_patterns = [
                r'(?:Currency Pair Rankings)(?:\s*\n|\s*:)(.*?)(?=(?:Risk Assessment|\n\n\w))',
                r'\*\*Currency Pair Rankings\*\*(.*?)(?=\*\*Risk Assessment|$)',
                r'Currency Pair Rankings(.*?)(?=Risk Assessment|$)'
            ]
            
            pairs_section = ""
            for pattern in pairs_section_patterns:
                pairs_section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if pairs_section_match:
                    pairs_section = pairs_section_match.group(1)
                    logger.debug(f"Found currency pairs section with pattern: {pattern[:30]}...")
                    break
            
            if pairs_section:
                # More flexible pattern for currency pairs
                pair_patterns = [
                    r'\*\*([\w/]+)\*\*\s*\(Rank:\s*(\d+(?:\.\d+)?)/(\d+)\)(.*?)(?=\*\*[\w/]+\*\*|\*\*Risk|\n\n\*\*|$)',
                    r'(?:\*\*)?([\w/]+)(?:\*\*)?\s*\(Rank:\s*(\d+(?:\.\d+)?)/(\d+)\)(.*?)(?=(?:\*\*)?[\w/]+(?:\*\*)?|Risk Assessment|$)',
                    r'(?:\*\*)?([\w/]+)(?:\*\*)?\s*\(Rank:?\s*(\d+(?:\.\d+)?)[/]?(\d+)?\)(.*?)(?=(?:\*\*)?[\w/]+(?:\*\*)?|Risk|$)'
                ]
                
                for pattern in pair_patterns:
                    pair_matches = list(re.finditer(pattern, pairs_section, re.DOTALL))
                    if pair_matches:
                        logger.debug(f"Found {len(pair_matches)} currency pairs with pattern: {pattern[:30]}...")
                        break
                
                # Process each matched currency pair
                for match in pair_matches:
                    pair_name = match.group(1)
                    rank = float(match.group(2))
                    # Handle case where max_rank is missing
                    max_rank = int(match.group(3)) if match.group(3) else 10
                    pair_content = match.group(4)
                    
                    # More flexible patterns for outlook percentages
                    fundamental_patterns = [
                        r'Fundamental Outlook:\s*(\d+)%',
                        r'Fundamental\s*:\s*(\d+)%',
                        r'Fundamental\s*Outlook\s*is\s*(\d+)'
                    ]
                    
                    sentiment_patterns = [
                        r'Sentiment Outlook:\s*(\d+)%',
                        r'Sentiment\s*:\s*(\d+)%',
                        r'Sentiment\s*is\s*(\d+)'
                    ]
                    
                    rationale_patterns = [
                        r'Rationale:\s*(.*?)(?=\n\n|\*|$)',
                        r'Rationale\s*is\s*(.*?)(?=\n\n|\*|$)',
                        r'(?:Description|Analysis|Explanation):\s*(.*?)(?=\n\n|\*|$)'
                    ]
                    
                    # Extract fundamental outlook
                    fundamental = 50  # Default
                    for pattern in fundamental_patterns:
                        fundamental_match = re.search(pattern, pair_content, re.IGNORECASE)
                        if fundamental_match:
                            fundamental = int(fundamental_match.group(1))
                            break
                    
                    # Extract sentiment outlook
                    sentiment = 50  # Default
                    for pattern in sentiment_patterns:
                        sentiment_match = re.search(pattern, pair_content, re.IGNORECASE)
                        if sentiment_match:
                            sentiment = int(sentiment_match.group(1))
                            break
                    
                    # Extract rationale
                    rationale = ""
                    for pattern in rationale_patterns:
                        rationale_match = re.search(pattern, pair_content, re.DOTALL | re.IGNORECASE)
                        if rationale_match:
                            rationale = rationale_match.group(1).strip()
                            break
                    
                    # If no rationale found but we have content, use a cleaned version of the content
                    if not rationale and pair_content:
                        # Clean up the content by removing outlook lines
                        content_lines = [
                            line.strip() for line in pair_content.split('\n') 
                            if not re.search(r'(Fundamental|Sentiment)\s*Outlook', line, re.IGNORECASE)
                        ]
                        rationale = " ".join(content_lines).strip()
                    
                    # Ensure rationale has a minimum value
                    if not rationale:
                        rationale = f"Analysis for {pair_name}"
                    
                    # Add to pairs list
                    result["currencyPairRankings"].append({
                        "pair": pair_name,
                        "rank": rank,
                        "maxRank": max_rank,
                        "fundamentalOutlook": fundamental,
                        "sentimentOutlook": sentiment,
                        "rationale": rationale
                    })
            
            # If no currency pairs found but there are mentions in the text, extract them
            if not result["currencyPairRankings"]:
                # Look for common currency pair mentions
                common_pairs = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF", "USD/CAD", "NZD/USD"]
                for pair in common_pairs:
                    if pair in text or pair.replace("/", "") in text:
                        # Found a mention, create a basic entry
                        result["currencyPairRankings"].append({
                            "pair": pair,
                            "rank": 5.0,
                            "maxRank": 10,
                            "fundamentalOutlook": 50,
                            "sentimentOutlook": 50,
                            "rationale": f"Mentioned in analysis. See formatted text for details."
                        })
                        logger.debug(f"Added {pair} as fallback from text mentions")
                        # Just add a few to avoid overwhelming with fallbacks
                        if len(result["currencyPairRankings"]) >= 3:
                            break
            
            # Extract Risk Assessment with more flexible patterns
            risk_section_patterns = [
                r'Risk Assessment:?(.*?)(?=Trade Management Guidelines|$)',
                r'\*\*Risk Assessment(?::\*\*|\*\*:|\*\*)(.*?)(?=\*\*Trade Management|$)',
                r'Risk Assessment(.*?)(?=Trade Management|$)'
            ]
            
            risk_section = ""
            for pattern in risk_section_patterns:
                risk_section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if risk_section_match:
                    risk_section = risk_section_match.group(1).strip()
                    logger.debug(f"Found risk section with pattern: {pattern[:30]}...")
                    break
            
            if risk_section:
                # More flexible patterns for risk components
                primary_risk_patterns = [
                    r'Primary Risk:?\s*(.*?)(?=Correlation Risk|Volatility|$)',
                    r'\*\s*Primary Risk:?\s*(.*?)(?=\*|Correlation|Volatility|$)',
                    r'(?:Main|Key|Principal) Risk:?\s*(.*?)(?=Correlation|Volatility|$)'
                ]
                
                correlation_risk_patterns = [
                    r'Correlation Risk:?\s*(.*?)(?=Volatility|$)',
                    r'\*\s*Correlation Risk:?\s*(.*?)(?=\*|Volatility|$)',
                    r'Cross-[Aa]sset Risk:?\s*(.*?)(?=Volatility|$)'
                ]
                
                volatility_patterns = [
                    r'Volatility Potential:?\s*(.*?)(?=$)',
                    r'\*\s*Volatility Potential:?\s*(.*?)(?=\*|$)',
                    r'(?:Expected|Anticipated) Volatility:?\s*(.*?)(?=$)'
                ]
                
                # Extract primary risk
                for pattern in primary_risk_patterns:
                    primary_risk_match = re.search(pattern, risk_section, re.DOTALL | re.IGNORECASE)
                    if primary_risk_match:
                        result["riskAssessment"]["primaryRisk"] = primary_risk_match.group(1).strip()
                        break
                
                # Extract correlation risk
                for pattern in correlation_risk_patterns:
                    correlation_risk_match = re.search(pattern, risk_section, re.DOTALL | re.IGNORECASE)
                    if correlation_risk_match:
                        result["riskAssessment"]["correlationRisk"] = correlation_risk_match.group(1).strip()
                        break
                
                # Extract volatility potential
                for pattern in volatility_patterns:
                    volatility_match = re.search(pattern, risk_section, re.DOTALL | re.IGNORECASE)
                    if volatility_match:
                        result["riskAssessment"]["volatilityPotential"] = volatility_match.group(1).strip()
                        break
            
            # Extract Trade Management Guidelines with more flexible patterns
            guidelines_patterns = [
                r'Trade Management Guidelines:?(.*?)$',
                r'\*\*Trade Management Guidelines(?::\*\*|\*\*:|\*\*)(.*?)$',
                r'Trade Management(.*?)$'
            ]
            
            guidelines_text = ""
            for pattern in guidelines_patterns:
                guidelines_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if guidelines_match:
                    guidelines_text = guidelines_match.group(1).strip()
                    logger.debug(f"Found guidelines with pattern: {pattern[:30]}...")
                    break
            
            if guidelines_text:
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
            else:
                # Look for sentiment words in summary
                if result["summary"]:
                    summary_lower = result["summary"].lower()
                    if any(word in summary_lower for word in ["bullish", "positive", "uptrend", "gains"]):
                        sentiment_category = "bullish"
                        sentiment_score = 75
                    elif any(word in summary_lower for word in ["bearish", "negative", "downtrend", "losses"]):
                        sentiment_category = "bearish"
                        sentiment_score = 25
            
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
            if result["summary"]:
                sentences = re.split(r'(?<=[.!?])\s+', result["summary"])
                result["keyPoints"] = [s.strip() for s in sentences if len(s.strip()) > 10][:3]
            
            # If we couldn't extract key points, add a default one
            if not result["keyPoints"]:
                result["keyPoints"] = ["Market analysis based on latest financial news"]
            
            # Ensure all required fields have values
            self._ensure_complete_result(result, text)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing structured response: {e}")
            logger.error(f"Original text: {text[:200]}...")
            
            # Return a complete fallback structure that uses the text
            return self._create_fallback_result(text)
    
    def _ensure_complete_result(self, result: Dict[str, Any], original_text: str) -> None:
        """Ensure all fields in the result have valid values."""
        # Ensure summary is not empty
        if not result["summary"] and original_text:
            result["summary"] = original_text.split('\n\n')[0] if '\n\n' in original_text else original_text[:500]
        
        # Ensure keyPoints is not empty
        if not result["keyPoints"]:
            result["keyPoints"] = ["Market analysis based on latest financial news"]
        
        # Ensure currencyPairRankings is not empty
        if not result["currencyPairRankings"]:
            # Add at least one default pair
            result["currencyPairRankings"].append({
                "pair": "EUR/USD",
                "rank": 5.0,
                "maxRank": 10,
                "fundamentalOutlook": 50,
                "sentimentOutlook": 50,
                "rationale": "Default entry. See formatted text for full analysis."
            })
        
        # Ensure riskAssessment fields are not empty
        if not result["riskAssessment"]["primaryRisk"]:
            result["riskAssessment"]["primaryRisk"] = "See formatted text for detailed risk assessment"
        if not result["riskAssessment"]["correlationRisk"]:
            result["riskAssessment"]["correlationRisk"] = "See formatted text for correlation risks"
        if not result["riskAssessment"]["volatilityPotential"]:
            result["riskAssessment"]["volatilityPotential"] = "See formatted text for volatility assessment"
        
        # Ensure tradeManagementGuidelines is not empty
        if not result["tradeManagementGuidelines"]:
            result["tradeManagementGuidelines"].append("See formatted text for detailed trading guidelines")
    
    def _create_fallback_result(self, text: str) -> Dict[str, Any]:
        """Create a complete fallback result that uses the original text."""
        # Get first paragraph for summary
        first_paragraph = text.split('\n\n')[0] if '\n\n' in text else text[:500]
        
        # Look for currency pairs in text
        currency_pairs = []
        common_pairs = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF", "USD/CAD", "NZD/USD"]
        for pair in common_pairs:
            if pair in text:
                currency_pairs.append({
                    "pair": pair,
                    "rank": 5.0,
                    "maxRank": 10,
                    "fundamentalOutlook": 50,
                    "sentimentOutlook": 50,
                    "rationale": "See formatted text for detailed analysis"
                })
                # Add up to 3 pairs
                if len(currency_pairs) >= 3:
                    break
        
        # Ensure at least one pair
        if not currency_pairs:
            currency_pairs.append({
                "pair": "EUR/USD",
                "rank": 5.0,
                "maxRank": 10,
                "fundamentalOutlook": 50,
                "sentimentOutlook": 50,
                "rationale": "Default entry. See formatted text for full analysis."
            })
        
        return {
            "summary": first_paragraph,
            "keyPoints": ["Complete analysis available in formatted text", 
                          "See structured output for detailed currency pair information",
                          "Market analysis based on latest financial news"],
            "currencyPairRankings": currency_pairs,
            "riskAssessment": {
                "primaryRisk": "See formatted text for detailed risk assessment",
                "correlationRisk": "See formatted text for correlation risks",
                "volatilityPotential": "See formatted text for volatility assessment"
            },
            "tradeManagementGuidelines": ["See formatted text for detailed trading guidelines"],
            "sentiment": {"overall": "neutral", "score": 50},
            "impactLevel": "MEDIUM"
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return self.cache.get_stats()
