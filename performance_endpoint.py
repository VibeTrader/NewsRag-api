@app.get("/performance")
async def performance_metrics():
    """Get performance metrics for the API."""
    try:
        # Get cache stats
        cache_stats = summarizer.get_cache_stats()
        
        # Get Langfuse status
        langfuse_status = {
            "enabled": langfuse_monitor.enabled,
            "host": langfuse_monitor.langfuse_host if hasattr(langfuse_monitor, "langfuse_host") else None,
            "has_client": hasattr(langfuse_monitor, "langfuse") and langfuse_monitor.langfuse is not None,
            "project": langfuse_monitor.project_name if hasattr(langfuse_monitor, "project_name") else None
        }
        
        # Get current configuration
        api_config = {
            "max_summary_articles": int(os.getenv("MAX_SUMMARY_ARTICLES", "15")),
            "max_article_content_chars": int(os.getenv("MAX_ARTICLE_CONTENT_CHARS", "1500")),
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "120")),
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("MAX_TOKENS", "4000")),
            "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Unknown")
        }
        
        # Return combined metrics
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache": cache_stats,
            "langfuse": langfuse_status,
            "config": api_config,
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
