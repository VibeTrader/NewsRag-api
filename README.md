# NewsRagnarok API

FastAPI service for news article search and summarization using Qdrant vector database and Azure OpenAI.

## 🌟 Features

- **Vector Search**: Find relevant news articles using semantic search
- **AI Summarization**: Generate comprehensive forex market analysis from multiple sources
- **Caching**: High-performance in-memory caching for faster responses
- **Clean Architecture**: Streamlined codebase focused on core functionality

## 📁 Structure

```
/NewsRagnarok-API
├── api.py (FastAPI application)
├── requirements.txt (API dependencies)
├── startup.txt (App Service config)
├── deploy-api.sh (deployment script)
├── clients/
│   ├── qdrant_client.py (Vector database client)
│   └── vector_client.py (Vector operations)
├── utils/
│   └── summarization/ (Summarization utilities)
│       ├── __init__.py
│       ├── news_summarizer.py (Main summarization logic)
│       └── cache_manager.py (In-memory caching)
└── .env (environment variables)
```

## 🔧 API Endpoints

- `GET /health` - Health check for API and Qdrant connection
- `POST /search` - Search for articles by query
- `GET /documents/stats` - Get collection statistics
- `POST /summarize` - Generate forex market analysis summary
- `GET /summarize/stats` - Get cache statistics

## 📊 Summarization Features

The `/summarize` endpoint provides advanced forex market analysis:

- **Executive Summary**: Concise overview of current market conditions
- **Currency Pair Rankings**: Detailed analysis of major forex pairs (EUR/USD, USD/JPY, etc.)
- **Risk Assessment**: Analysis of market risks and potential volatility
- **Trade Management Guidelines**: Actionable recommendations for traders

Example request:
```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "forex news",
    "limit": 5,
    "format": "text"
  }'
```

## 💡 Technology Stack

- **FastAPI**: High-performance API framework
- **Qdrant**: Vector database for semantic search
- **Azure OpenAI**: AI-powered summarization and analysis
- **In-memory Cache**: Efficient caching with TTL and LRU eviction

## 🚀 Deployment

```bash
# Start the API server
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

## 🔗 Dependencies

- Qdrant (vector database)
- Azure OpenAI (AI model access)
- Pydantic (data validation)
- Loguru (logging)

## 📝 Environment Variables

Required environment variables:
- `QDRANT_URL`: Qdrant database URL
- `QDRANT_API_KEY`: Qdrant API key
- `QDRANT_COLLECTION_NAME`: Collection name for news articles
- `OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: Azure OpenAI API version
- `OPENAI_BASE_URL`: Azure OpenAI base URL
- `AZURE_OPENAI_DEPLOYMENT`: Azure OpenAI deployment name

Optional settings:
- `SUMMARY_CACHE_SIZE`: Max number of cached summaries (default: 100)
- `SUMMARY_CACHE_TTL`: Cache time-to-live in seconds (default: 1800)
