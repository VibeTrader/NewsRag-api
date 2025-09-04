# README: NewsRagnarok Summarization Service

## Overview
This document provides an overview of the new summarization service added to NewsRagnarok API. The service generates comprehensive summaries of financial news articles by analyzing multiple articles together.

## Key Features

- **Multi-article Summarization**: Generates unified summaries across multiple news articles
- **Financial Analysis**: Provides sentiment analysis, impact assessment, and currency-specific implications
- **Market Conditions**: Creates contextualized market condition statements
- **Trading Recommendations**: Offers currency pair trading suggestions based on news content
- **Efficient Caching**: Uses LRU caching with TTL for improved performance

## Architecture

The summarization service follows a modular architecture with these key components:

### 1. NewsSummarizer
Main class responsible for generating summaries from multiple news articles.

- Uses Azure OpenAI for generating base summaries
- Enhances summaries with additional market analysis
- Implements efficient caching for improved performance

### 2. MarketAnalyzer
Performs specialized financial market analysis on news content.

- Analyzes currency strength mentions across articles
- Generates currency pair recommendations
- Creates market conditions statements

### 3. CacheManager
Provides efficient caching capabilities with LRU eviction policy.

- Time-based expiration (TTL)
- Size-based eviction (LRU)
- Performance statistics tracking

## API Endpoints

### POST /summarize
Generates a comprehensive summary of news articles related to a query.

**Request:**
```json
{
  "query": "USD inflation",
  "limit": 20,
  "score_threshold": 0.3,
  "use_cache": true
}
```

**Response:**
```json
{
  "summary": "The current forex market is characterized by significant movements driven by labor market data, central bank policies, and geopolitical factors. Our top-line recommendation is to monitor USD/JPY for potential further Yen depreciation and consider bullish positions in AUD/USD and EUR/USD due to supportive economic data.",
  "keyPoints": [
    "US labor market weakness has increased expectations for a Federal Reserve rate cut",
    "Australian economic data shows stronger than expected GDP growth",
    "Currency pairs are responding to central bank policy expectations"
  ],
  "sentiment": { 
    "overall": "bullish", 
    "score": 65 
  },
  "impactLevel": "HIGH",
  "currencyPairRankings": [
    {
      "pair": "AUD/USD",
      "rank": 8,
      "maxRank": 10,
      "fundamentalOutlook": 80,
      "sentimentOutlook": 75,
      "rationale": "Strong Australian economic data, including a higher-than-expected trade surplus and GDP growth, has eased expectations for a Reserve Bank of Australia rate cut."
    },
    {
      "pair": "EUR/USD",
      "rank": 7,
      "maxRank": 10,
      "fundamentalOutlook": 70,
      "sentimentOutlook": 65,
      "rationale": "EUR/USD has stabilized and regained ground as USD weakness persists amid expectations of a dovish Fed response to soft labor data."
    },
    {
      "pair": "USD/JPY",
      "rank": 5,
      "maxRank": 10,
      "fundamentalOutlook": 50,
      "sentimentOutlook": 45,
      "rationale": "The pair is showing upward momentum with bullish technical signals, but momentum remains capped ahead of key US labor data."
    }
  ],
  "riskAssessment": {
    "primaryRisk": "US labor market data releases and their impact on Fed policy expectations.",
    "correlationRisk": "Global yield risks and BoJ policy ambiguity affecting the Yen.",
    "volatilityPotential": "High, due to upcoming key economic releases and central bank decisions."
  },
  "tradeManagementGuidelines": [
    "Monitor US labor market data releases closely for signs of weakness, which could reinforce USD downside.",
    "Watch for any unexpected commentary or action from the BoJ, which could impact Yen direction.",
    "Consider the potential for rate cuts by the BoC and Fed, which could further weaken CAD."
  ],
  "marketConditions": "Market conditions reflect measured optimism with selective opportunities amid elevated volatility.",
  "query": "USD inflation",
  "articleCount": 15,
  "timestamp": "2025-09-04T12:34:56Z"
}
```

### GET /summarize/stats
Returns cache statistics for monitoring performance.

**Response:**
```json
{
  "size": 25,
  "max_size": 100,
  "hit_rate": "68.5%",
  "hits": 124,
  "misses": 57
}
```

## Configuration

The summarization service can be configured using environment variables:

- `SUMMARY_CACHE_SIZE`: Maximum number of cached summaries (default: 100)
- `SUMMARY_CACHE_TTL`: Time-to-live in seconds for cached entries (default: 1800)
- `AZURE_OPENAI_DEPLOYMENT`: Azure OpenAI deployment to use (default: "gpt-4")

## Integration with VibeTrader

To use the summarization service in VibeTrader:

```typescript
async function getNewsAnalysis() {
  const response = await fetch('https://newsragnarok-api.azurewebsites.net/summarize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: 'latest forex news',
      limit: 20,
      use_cache: true
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to fetch news analysis');
  }

  return await response.json();
}
```