"""
Enhanced forex summarizer with chunking support and improved logging/monitoring.
"""

import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import your existing forex_summarizer
from utils.summarization.langchain.forex_summarizer import LangChainForexSummarizer

# Try to import monitoring
try:
    from utils.monitoring import AppInsightsMonitor
    monitor = AppInsightsMonitor.get_instance()
    has_monitoring = True
except ImportError:
    has_monitoring = False

class EnhancedForexSummarizer(LangChainForexSummarizer):
    """Enhanced forex summarizer with support for processing all articles efficiently."""
    
    async def generate_summary(
        self, 
        articles: List[Dict[str, Any]],
        query: str = "latest forex news",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate a comprehensive forex market summary from multiple news articles.
        
        Adds automatic chunking for large article sets.
        
        Args:
            articles: List of news articles from Qdrant
            query: Original search query
            use_cache: Whether to use cached summaries
            
        Returns:
            Dictionary containing summary and analysis
        """
        if not articles:
            logger.warning("No articles provided for summarization")
            return self._empty_summary_result()
        
        # Generate cache key before checking cache
        cache_key = None
        if use_cache:
            cache_key = self._get_cache_key(articles, query)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached summary for query: {query}")
                return cached_result
        
        # Determine if we need chunking
        max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "50"))  # Maximum articles per chunk
        
        if len(articles) <= max_chunk_size:
            # Process normally if we have fewer articles than the chunk size
            try:
                return await super().generate_summary(articles, query, use_cache=False)
            except Exception as e:
                logger.error(f"Error in regular summary generation: {e}", exc_info=True)
                if has_monitoring:
                    monitor.track_exception({
                        "phase": "regular_summary",
                        "query": query,
                        "error": str(e)
                    })
                return self._empty_summary_result()
        else:
            # Need to chunk - process in batches and merge results
            logger.info(f"Chunking {len(articles)} articles into groups of {max_chunk_size}")
            
            # Sort by score and recency for optimal chunking
            try:
                # Sort primarily by date, secondarily by score
                sorted_articles = sorted(
                    articles,
                    key=lambda x: (
                        x.get("payload", {}).get("publishDatePst", "0"),
                        x.get("score", 0)
                    ),
                    reverse=True  # Most recent and highest score first
                )
            except Exception as e:
                logger.warning(f"Error sorting articles: {e}")
                sorted_articles = articles
            
            # Split into chunks
            chunks = [sorted_articles[i:i+max_chunk_size] for i in range(0, len(sorted_articles), max_chunk_size)]
            
            # Add enhanced logging for chunking
            logger.info(f"Starting chunked processing for {len(articles)} articles with {len(chunks)} chunks")
            
            # Track the chunking operation if monitoring is available
            if has_monitoring:
                monitor.track_event("chunking_started", {
                    "article_count": str(len(articles)),
                    "chunk_count": str(len(chunks)),
                    "chunk_size": str(max_chunk_size),
                    "query": query
                })
            
            # Process each chunk
            chunk_results = []
            chunk_errors = 0
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} with {len(chunk)} articles")
                try:
                    # Process this chunk using the parent class method
                    chunk_result = await super().generate_summary(
                        chunk, 
                        f"{query} (part {i+1}/{len(chunks)})",
                        use_cache=False
                    )
                    
                    # Add chunk metadata
                    chunk_result["chunk_index"] = i
                    chunk_result["chunk_count"] = len(chunks)
                    
                    chunk_results.append(chunk_result)
                    
                    # Add enhanced logging for successful chunk processing
                    logger.info(f"Successfully processed chunk {i+1}/{len(chunks)} with {len(chunk)} articles")
                    
                    # Track successful chunk if monitoring is available
                    if has_monitoring:
                        monitor.track_event("chunk_processed", {
                            "chunk_index": str(i+1),
                            "chunk_count": str(len(chunks)),
                            "article_count": str(len(chunk)),
                            "query": query
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {e}", exc_info=True)
                    chunk_errors += 1
                    
                    # Track chunk error if monitoring is available
                    if has_monitoring:
                        monitor.track_exception({
                            "phase": "chunk_processing",
                            "chunk_index": str(i+1),
                            "chunk_count": str(len(chunks)),
                            "article_count": str(len(chunk)),
                            "query": query,
                            "error": str(e)
                        })
                    # Continue with other chunks even if one fails
            
            # Merge results from all chunks
            if chunk_results:
                try:
                    merged_result = self._merge_chunk_results(chunk_results, query)
                    
                    # Add enhanced logging for merge operation
                    logger.info(f"Successfully merged results from {len(chunk_results)}/{len(chunks)} chunks")
                    
                    # Track merge success if monitoring is available
                    if has_monitoring:
                        monitor.track_event("chunks_merged", {
                            "successful_chunks": str(len(chunk_results)),
                            "total_chunks": str(len(chunks)),
                            "error_chunks": str(chunk_errors),
                            "query": query
                        })
                    
                    # Cache the merged result
                    if use_cache and cache_key:
                        self.cache.set(cache_key, merged_result)
                    
                    return merged_result
                except Exception as e:
                    logger.error(f"Error merging chunk results: {e}", exc_info=True)
                    
                    # Track merge error if monitoring is available
                    if has_monitoring:
                        monitor.track_exception({
                            "phase": "chunk_merging",
                            "chunks_to_merge": str(len(chunk_results)),
                            "total_chunks": str(len(chunks)),
                            "query": query,
                            "error": str(e)
                        })
                    
                    # Return the first chunk's result as fallback
                    logger.warning("Using first chunk result as fallback due to merge error")
                    return chunk_results[0]
            else:
                # All chunks failed
                logger.error("All chunks failed to process")
                
                # Track complete failure if monitoring is available
                if has_monitoring:
                    monitor.track_event("all_chunks_failed", {
                        "chunk_count": str(len(chunks)),
                        "article_count": str(len(articles)),
                        "query": query
                    })
                
                return self._empty_summary_result()
    
    def _merge_chunk_results(self, chunk_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Merge results from multiple chunks."""
        if not chunk_results:
            return self._empty_summary_result()
        
        try:
            # Start with the first chunk's result
            merged = chunk_results[0].copy()
            
            # Combine key points (up to 5)
            all_key_points = []
            for result in chunk_results:
                all_key_points.extend(result.get("keyPoints", []))
            
            # Deduplicate key points
            unique_key_points = []
            for point in all_key_points:
                # Check if this point is similar to any existing point
                if not any(self._text_similarity(point, existing) > 0.7 for existing in unique_key_points):
                    unique_key_points.append(point)
            
            # Collect all currency pairs
            all_pairs = {}
            for result in chunk_results:
                for pair in result.get("currencyPairRankings", []):
                    pair_name = pair.get("pair", "")
                    if not pair_name:
                        continue
                        
                    if pair_name in all_pairs:
                        # Update existing pair data
                        existing = all_pairs[pair_name]
                        existing["rank"] = max(existing["rank"], pair.get("rank", 0))
                        existing["fundamentalOutlook"] = (existing["fundamentalOutlook"] + pair.get("fundamentalOutlook", 50)) / 2
                        existing["sentimentOutlook"] = (existing["sentimentOutlook"] + pair.get("sentimentOutlook", 50)) / 2
                        existing["mentions"] += 1
                        # Combine rationales (limit size)
                        if len(existing["rationale"]) < 500:
                            existing["rationale"] += f" {pair.get('rationale', '')}"
                    else:
                        # Add new pair
                        all_pairs[pair_name] = pair.copy()
                        all_pairs[pair_name]["mentions"] = 1
            
            # Sort pairs by rank and mentions
            sorted_pairs = sorted(
                all_pairs.values(),
                key=lambda x: (x.get("rank", 0), x.get("mentions", 0)),
                reverse=True
            )
            
            # Calculate overall sentiment
            sentiment_scores = [r.get("sentiment", {}).get("score", 50) for r in chunk_results]
            if sentiment_scores:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                sentiment_category = "neutral"
                if avg_sentiment >= 70:
                    sentiment_category = "bullish"
                elif avg_sentiment <= 30:
                    sentiment_category = "bearish"
                    
                merged["sentiment"] = {
                    "overall": sentiment_category,
                    "score": avg_sentiment
                }
            
            # Combine risk assessments
            risk_types = ["primaryRisk", "correlationRisk", "volatilityPotential"]
            combined_risks = {}
            
            for risk_type in risk_types:
                risk_texts = [r.get("riskAssessment", {}).get(risk_type, "") for r in chunk_results]
                valid_risks = [text for text in risk_texts if text]
                
                if valid_risks:
                    # Use the most comprehensive risk assessment (longest text)
                    combined_risks[risk_type] = max(valid_risks, key=len)
            
            # Build combined summary
            summary_parts = [r.get("summary", "") for r in chunk_results]
            valid_summaries = [s for s in summary_parts if s]
            
            combined_summary = ""
            if valid_summaries:
                # Use the most recent chunk's summary as base
                combined_summary = valid_summaries[0]
                
                # Add unique insights from other chunks
                for summary in valid_summaries[1:]:
                    sentences = summary.split(". ")
                    for sentence in sentences:
                        if sentence and not any(self._text_similarity(sentence, s) > 0.5 for s in combined_summary.split(". ")):
                            combined_summary += f" {sentence}."
            
            # Update merged result
            merged["summary"] = combined_summary
            merged["keyPoints"] = unique_key_points[:5]
            merged["currencyPairRankings"] = sorted_pairs[:8]
            merged["riskAssessment"] = combined_risks
            
            # Count total articles processed
            total_articles = sum(r.get("articleCount", 0) for r in chunk_results)
            merged["articleCount"] = total_articles
            
            # Update timestamp and query
            merged["timestamp"] = datetime.now().isoformat()
            merged["query"] = query
            
            # Add chunking info
            merged["processingDetails"] = {
                "chunksProcessed": len(chunk_results),
                "totalChunks": chunk_results[0].get("chunk_count", len(chunk_results)),
                "totalArticles": total_articles,
                "chunkErrorCount": chunk_results[0].get("chunk_count", len(chunk_results)) - len(chunk_results)
            }
            
            return merged
            
        except Exception as e:
            logger.error(f"Error merging chunk results: {e}", exc_info=True)
            
            # Track exception if monitoring is available
            if has_monitoring:
                monitor.track_exception({
                    "phase": "chunk_merging",
                    "operation": "merge_chunk_results",
                    "error": str(e),
                    "query": query
                })
                
            # Return the first chunk's result as fallback
            if chunk_results and len(chunk_results) > 0:
                return chunk_results[0]
            else:
                return self._empty_summary_result()
    
    def _empty_summary_result(self) -> Dict[str, Any]:
        """Create an empty summary result."""
        return {
            "summary": "Unable to generate market analysis due to processing error.",
            "keyPoints": ["Error processing financial news"],
            "currencyPairRankings": [],
            "riskAssessment": {
                "primaryRisk": "Unknown",
                "correlationRisk": "Unknown",
                "volatilityPotential": "Unknown"
            },
            "tradeManagementGuidelines": [],
            "sentiment": {"overall": "neutral", "score": 50},
            "impactLevel": "MEDIUM",
            "timestamp": datetime.now().isoformat()
        }
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity based on shared words."""
        if not text1 or not text2:
            return 0.0
            
        # Convert to lowercase and tokenize
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        # Avoid division by zero
        return intersection / union if union > 0 else 0.0