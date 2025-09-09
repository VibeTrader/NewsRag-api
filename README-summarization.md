# Forex News Summarization

The NewsRagnarok API includes a powerful forex news summarization feature that leverages Azure OpenAI to generate comprehensive market analysis from multiple news sources.

## 🔍 How It Works

The summarization process follows these steps:

1. **Search**: Find relevant forex news articles using semantic search in Qdrant
2. **Preparation**: Extract and format the key information from each article
3. **Summarization**: Send articles to Azure OpenAI with specific instructions for analysis
4. **Parsing**: Process the AI-generated analysis into a structured format
5. **Caching**: Store the result for future identical queries (30-minute TTL)

## 📊 Summary Structure

Each summary contains:

### Executive Summary

A concise overview of current market conditions with sentiment indicators highlighted. Example:

```
The forex market is experiencing heightened volatility as the US Dollar (USD) oscillates between multi-week lows 
and sharp recoveries, driven by anticipation of key US macroeconomic data and global bond market movements.
```

### Currency Pair Rankings

Detailed analysis of major currency pairs, each with:
- Rank (scale of 1-10)
- Fundamental outlook percentage
- Sentiment outlook percentage
- Detailed rationale based on news

Example:
```
EUR/USD (Rank: 8/10)
   * Fundamental Outlook: 75%
   * Sentiment Outlook: 70%
   * Rationale: EUR/USD has broken above 1.1700, supported by resilient Eurozone PMI readings...
```

### Risk Assessment

Analysis of market risks:
- Primary Risk: The most significant factor that could impact the market
- Correlation Risk: Related risk factors affecting multiple currencies
- Volatility Potential: Assessment of potential price swings

### Trade Management Guidelines

Practical trading recommendations based on the current market conditions.

## 🚀 API Usage

### Request

```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "forex news",
    "limit": 5,
    "format": "text",
    "use_cache": true
  }'
```

Parameters:
- `query`: Search term for finding relevant articles
- `limit`: Maximum number of articles to analyze (5-20 recommended)
- `format`: Output format ("json" or "text")
- `use_cache`: Whether to use cached summaries if available
- `score_threshold`: Minimum relevance score for articles (0.0-1.0)

### Response (Text Format)

A formatted text summary perfect for human reading, following the structure outlined above.

### Response (JSON Format)

A structured JSON object with the following fields:
- `summary`: Executive summary text
- `keyPoints`: Array of key points from the analysis
- `currencyPairRankings`: Array of currency pair analyses
- `riskAssessment`: Object with risk analysis
- `tradeManagementGuidelines`: Array of trading recommendations
- `marketConditions`: Overall market condition statement
- `sentiment`: Object with sentiment analysis (`overall` and `score`)
- `impactLevel`: Impact level assessment ("LOW", "MEDIUM", "HIGH")
- `timestamp`: ISO timestamp of when the summary was generated
- `query`: Original search query
- `articleCount`: Number of articles analyzed



## 📝 Customization

The summarization behavior can be customized through:

1. **Cache Settings**:
   - `SUMMARY_CACHE_SIZE`: Maximum number of cached summaries (default: 100)
   - `SUMMARY_CACHE_TTL`: Cache duration in seconds (default: 1800)

2. **OpenAI Model**:
   - Set via `AZURE_OPENAI_DEPLOYMENT` environment variable
   - Higher capability models provide more sophisticated analysis

