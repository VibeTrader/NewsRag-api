# NewsRag API

**High-Performance News Search & Forex Market Analysis API**

A FastAPI service that provides semantic news search and AI-powered forex market analysis using vector databases and LangChain.

---

## What Does This Do?

NewsRag API provides two core capabilities:

1. **Semantic News Search**: Find relevant financial news articles using vector similarity search
2. **AI Market Analysis**: Generate comprehensive forex market summaries with currency pair rankings, risk assessment, and trade recommendations

### Key Features
- **Vector Search**: Qdrant-based semantic search for finding relevant articles
- **AI Summarization**: LangChain + Azure OpenAI for intelligent market analysis
- **Currency Pair Analysis**: Automatic detection and ranking of forex pairs
- **Smart Caching**: In-memory cache with TTL and LRU eviction for fast responses
- **Multi-Region Deployment**: Runs across US, Europe, and India regions
- **Production Monitoring**: Application Insights and Langfuse integration

---

## Quick Start

```bash
# Setup
git clone <repo-url>
cd NewsRag-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run
uvicorn api:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### Health Check
```bash
GET /health
GET /health/simple  # For Traffic Manager (no dependencies)
```

### Search Articles
```bash
POST /search
```

**Request:**
```json
{
  "query": "EUR/USD forex news",
  "limit": 10,
  "score_threshold": 0.3,
  "use_ai_summary": false
}
```

**Response:**
```json
{
  "results": [...],
  "total_count": 10,
  "query": "EUR/USD forex news",
  "used_threshold": 0.3
}
```

### Generate Market Summary
```bash
POST /summarize
```

**Request:**
```json
{
  "query": "forex market analysis",
  "limit": 20,
  "score_threshold": 0.3,
  "use_cache": true,
  "format": "json"  // or "text"
}
```

**Response (JSON format):**
```json
{
  "summary": "Executive market overview...",
  "keyPoints": ["Point 1", "Point 2", ...],
  "sentiment": {
    "overall": "bullish",
    "score": 65
  },
  "impactLevel": "HIGH",
  "currencyPairRankings": [
    {
      "pair": "EUR/USD",
      "rank": 1,
      "fundamentalOutlook": 60,
      "sentimentOutlook": 55,
      "detailedRationale": "Analysis..."
    }
  ],
  "riskAssessment": {
    "primaryRisk": "Risk description...",
    "correlationRisk": "Correlation analysis...",
    "volatilityPotential": "Volatility outlook..."
  },
  "tradeManagementGuidelines": [
    "Guideline 1",
    "Guideline 2"
  ],
  "timestamp": "2024-01-15T10:30:00Z",
  "query": "forex market analysis",
  "articleCount": 20
}
```

### Cache Statistics
```bash
GET /summarize/stats
```

### Document Statistics
```bash
GET /documents/stats
```

---

## Architecture

### System Flow

```
Client Request
     ↓
FastAPI Endpoint
     ↓
┌─────────────────────────┐
│  /search                │  →  Qdrant Vector Search  →  Return Articles
└─────────────────────────┘
     ↓
┌─────────────────────────┐
│  /summarize             │
└─────────────────────────┘
     ↓
Check Cache (30 min TTL)
     ↓ (cache miss)
Qdrant Search (get relevant articles)
     ↓
Format Articles for LLM
     ↓
LangChain + Azure OpenAI
  ├─ Currency Pair Detection
  ├─ Market Analysis
  ├─ Risk Assessment
  └─ Trade Guidelines
     ↓
Parse & Structure Response
     ↓
Cache Result
     ↓
Return JSON or Text
```

### Components

1. **API Layer** (`api.py`)
   - FastAPI application
   - Request/response handling
   - CORS middleware
   - Health checks

2. **Search Layer** (`clients/qdrant_client.py`)
   - Qdrant vector database integration
   - Semantic similarity search
   - Document statistics

3. **Summarization Layer** (`utils/summarization/`)
   - `news_summarizer.py` - Main summarization orchestrator
   - `langchain/enhanced_forex_summarizer.py` - LangChain-based forex analysis
   - `cache_manager.py` - In-memory caching with TTL

4. **Monitoring Layer** (`utils/monitoring/`)
   - `app_insights.py` - Azure Application Insights integration
   - `langfuse/` - Langfuse LLM monitoring
   - `dependency_tracker.py` - Dependency health tracking

---

## Project Structure

```
NewsRag-api/
├── api.py                          # FastAPI application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── startup.sh                      # Startup script
│
├── clients/
│   ├── qdrant_client.py           # Vector database client
│   └── vector_client.py           # Vector operations
│
├── utils/
│   ├── summarization/
│   │   ├── news_summarizer.py     # Main summarizer
│   │   ├── cache_manager.py       # Caching system
│   │   └── langchain/             # LangChain implementation
│   │       └── enhanced_forex_summarizer.py
│   │
│   └── monitoring/
│       ├── app_insights.py        # Application Insights
│       ├── dependency_tracker.py  # Health tracking
│       └── langfuse/              # LLM monitoring
│
├── models/
│   ├── article_model.py           # Pydantic models
│   └── output.py                  # Response models
│
├── test/
│   ├── forex_summarizer_test.py   # Summarizer tests
│   ├── test_api_local.py          # API tests
│   └── test_monitoring.py         # Monitoring tests
│
├── terraform/                     # Infrastructure as Code
│   ├── main.tf                    # Main config
│   ├── variables.tf               # Variables
│   └── modules/                   # Terraform modules
│
└── .github/workflows/             # CI/CD pipelines
    ├── deploy-infrastructure.yml  # Infrastructure deployment
    └── deploy-app-multi-region.yml # App deployment
```

---

## Configuration

### Required Environment Variables

```bash
# API Configuration
PORT=8000
API_HOST=0.0.0.0

# Azure OpenAI (REQUIRED)
OPENAI_BASE_URL=https://your-endpoint.openai.azure.com
OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
EMBEDDING_DIMENSION=3072

# Qdrant Vector Database (REQUIRED)
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION_NAME=news_articles

# LLM Configuration
MODEL=claude-3-7-sonnet-20250219
MAX_TOKENS=4000
TEMPERATURE=0.7
LLM_TIMEOUT=120

# Performance Settings
MAX_SUMMARY_ARTICLES=15
MAX_ARTICLE_CONTENT_CHARS=1500
SUMMARY_CACHE_SIZE=100
SUMMARY_CACHE_TTL=1800  # 30 minutes

# Monitoring (OPTIONAL)
LANGFUSE_HOST=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
APPINSIGHTS_INSTRUMENTATIONKEY=your-app-insights-key

# Redis (OPTIONAL)
REDIS_HOST=your-redis-host
REDIS_PORT=6380
REDIS_PASSWORD=your-password
REDIS_USE_SSL=true
```

---

## How Summarization Works

### Process Flow

1. **Search Phase**
   - Query Qdrant for relevant articles
   - Filter by score threshold (default: 0.3)
   - Retrieve top N articles (default: 20)

2. **Preparation Phase**
   - Format articles for LLM processing
   - Truncate content to max characters
   - Highlight currency pairs in text
   - Generate cache key

3. **Analysis Phase**
   - Send to Azure OpenAI via LangChain
   - Use structured prompt for forex analysis
   - Request specific output format:
     - Executive summary
     - Currency pair rankings
     - Risk assessment
     - Trade guidelines

4. **Parsing Phase**
   - Extract structured data from LLM response
   - Validate currency pair rankings
   - Format risk assessment
   - Compile trade recommendations

5. **Caching Phase**
   - Store result with TTL (30 minutes)
   - Use LRU eviction when cache full
   - Return formatted response (JSON or text)

### Currency Pair Analysis

The system automatically:
- Detects currency pairs in articles (EUR/USD, GBP/JPY, etc.)
- Ranks pairs by frequency and importance
- Analyzes sentiment per pair
- Provides fundamental and technical outlook
- Generates detailed rationale for each pair

---

## Deployment

### Multi-Region Strategy

The API is deployed across multiple regions:

| Environment | Regions | Branch |
|-------------|---------|--------|
| **Development** | US, Europe | `dev` |
| **Production** | US, Europe, India | `main` |

### Deployment Flow

1. **Push to `dev` branch**
   - Deploys to US and Europe (dev environment)
   - Uses separate Terraform state (`newsraag-dev.tfstate`)
   - App Services: `newsraag-us-dev`, `newsraag-eu-dev`

2. **Merge to `main` branch**
   - Deploys to all regions (production environment)
   - Uses production Terraform state (`newsraag-prod.tfstate`)
   - App Services: `newsraag-us-prod`, `newsraag-eu-prod`, `newsraag-in-prod`

### CI/CD Pipeline

**Infrastructure Deployment** (`.github/workflows/deploy-infrastructure.yml`):
1. Validate Terraform configuration
2. Plan infrastructure changes
3. Apply changes to Azure
4. Create App Services in all regions

**Application Deployment** (`.github/workflows/deploy-app-multi-region.yml`):
1. Build Python application
2. Create deployment artifact
3. Deploy to all regions in parallel
4. Configure environment variables
5. Validate health endpoints

### Manual Deployment

```bash
# Infrastructure
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Application (local testing)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

---

## Testing

### Run Tests

```bash
# All tests
python -m pytest test/

# Specific tests
python test/forex_summarizer_test.py
python test/test_api_local.py
python test/test_monitoring.py

# With coverage
pytest test/ --cov=. --cov-report=html
```

### Test Coverage

- **Article Formatting**: Validates proper article structure
- **Currency Pair Detection**: Tests forex pair identification
- **Response Parsing**: Validates LLM response parsing
- **Cache Management**: Tests TTL and eviction
- **API Endpoints**: Tests all API routes
- **Monitoring**: Validates telemetry collection

---

## Performance

### Metrics

- **Search Speed**: 100-300ms typical (vector search)
- **Summary Generation**: 3-8 seconds (LLM processing)
- **Cache Hit Rate**: 70-80% with 30-min TTL
- **Concurrent Requests**: Handles 100+ concurrent users
- **Memory Usage**: 200-500MB per instance

### Optimization

1. **Caching**: 30-minute TTL reduces LLM API calls
2. **Parallel Deployment**: Multi-region for low latency
3. **Content Truncation**: Limits article size for faster processing
4. **Score Threshold**: Filters irrelevant results early

---

## Troubleshooting

### API Not Responding

**Check:**
```bash
curl http://localhost:8000/health
```

**Fix:** Verify environment variables are set, check Qdrant and Azure OpenAI connectivity

### Slow Summary Generation

**Check:**
```bash
curl http://localhost:8000/summarize/stats
```

**Fix:** 
- Check cache hit rate
- Reduce `MAX_SUMMARY_ARTICLES`
- Decrease `MAX_ARTICLE_CONTENT_CHARS`
- Increase `SUMMARY_CACHE_TTL`

### Qdrant Connection Errors

**Check:**
```bash
python -c "from clients.qdrant_client import QdrantClientWrapper; client = QdrantClientWrapper(); print('OK')"
```

**Fix:** Verify `QDRANT_URL` and `QDRANT_API_KEY` in `.env`

### LLM Timeout Errors

**Check:** Azure OpenAI service status and quota

**Fix:**
- Increase `LLM_TIMEOUT` value
- Reduce `MAX_SUMMARY_ARTICLES`
- Check Azure OpenAI quota and rate limits

### Cache Issues

**Check:**
```bash
curl http://localhost:8000/summarize/stats
```

**Fix:**
- Clear cache by restarting service
- Adjust `SUMMARY_CACHE_SIZE` and `SUMMARY_CACHE_TTL`

---

## Tech Stack

### Core
- **FastAPI** - High-performance API framework
- **Python 3.12** - Runtime environment
- **Uvicorn** - ASGI server

### AI & Search
- **Azure OpenAI** - GPT-4 for summarization
- **LangChain** - LLM orchestration framework
- **Qdrant** - Vector database for semantic search

### Monitoring
- **Azure Application Insights** - Performance monitoring
- **Langfuse** - LLM observability
- **OpenTelemetry** - Distributed tracing
- **Loguru** - Structured logging

### Infrastructure
- **Terraform** - Infrastructure as Code
- **Azure App Service** - Hosting platform
- **GitHub Actions** - CI/CD automation

---

## Development

### Setup
```bash
git clone <repo>
cd NewsRag-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with credentials
```

### Running Locally
```bash
# Standard mode
uvicorn api:app --host 0.0.0.0 --port 8000

# Development mode (auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# With custom port
uvicorn api:app --host 0.0.0.0 --port 9622
```

### Code Style
- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Test new features

---

## Important Notes

### Caching Behavior
- Cache TTL: 30 minutes (configurable)
- Eviction: LRU (Least Recently Used)
- Cache size: 100 summaries (configurable)
- Cache key: Based on query + article IDs

### Score Threshold
- Default: 0.3 (more permissive than 0.7)
- Lower values return more results
- Higher values return only highly relevant results
- Adjustable per request

### Article Limits
- Search: Default 10, max 100
- Summarization: Default 20, max 50
- Content truncation: 1500 chars per article

### Multi-Region Deployment
- Traffic Manager routes to nearest region
- Each region has independent App Service
- Shared Log Analytics and Application Insights
- Separate Terraform states per environment

---

## Support

### Logs
- **Local**: Console output with Loguru
- **Azure**: App Service → Log Stream
- **Application Insights**: Azure Portal → Insights

### Health Monitoring
```bash
# Local
curl http://localhost:8000/health

# Production
curl https://<app-name>.azurewebsites.net/health
```

### Key Files
- `.env` - Environment configuration
- `api.py` - Main application
- `utils/summarization/news_summarizer.py` - Core summarization
- `terraform/main.tf` - Infrastructure definition

---

**Production Status:** Active across US, Europe, and India regions

**Python Version:** 3.12

**API Version:** 1.0.0
