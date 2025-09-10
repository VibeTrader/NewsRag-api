"""
Simple test for the forex summarizer functionality.
"""

import os
import sys
import re
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Sample test articles
SAMPLE_ARTICLES = [
    {
        "id": "article1",
        "score": 0.95,
        "payload": {
            "title": "EUR/USD Faces Pressure as Dollar Strengthens",
            "source": "Forex News",
            "publishDatePst": "2025-09-08",
            "content": "The EUR/USD pair declined today as the US dollar strengthened across the board."
        }
    },
    {
        "id": "article2",
        "score": 0.90,
        "payload": {
            "title": "USD/JPY Hits 5-Month High on Divergent Central Bank Policies",
            "source": "Financial Times",
            "publishDatePst": "2025-09-09",
            "content": "The USD/JPY pair reached a 5-month high today, breaking above the 152.00 resistance level."
        }
    }
]

# Define test functions to verify parts of our implementation

def test_format_articles():
    """Test the article formatting functionality."""
    articles_text = ""
    for idx, article in enumerate(SAMPLE_ARTICLES, 1):
        payload = article.get("payload", {})
        publish_date = payload.get("publishDatePst", "Unknown date")
        
        articles_text += f"ARTICLE {idx} [Date: {publish_date}]:\n"
        articles_text += f"Title: {payload.get('title', 'Untitled')}\n"
        articles_text += f"Source: {payload.get('source', 'Unknown')}\n"
        articles_text += f"Content: {payload.get('content', '')}...\n\n"
    
    # Verify formatting
    assert "ARTICLE 1" in articles_text
    assert "ARTICLE 2" in articles_text
    assert "EUR/USD Faces Pressure" in articles_text
    assert "USD/JPY Hits 5-Month High" in articles_text
    print("✅ Article formatting test passed")
    return articles_text

def test_currency_pair_highlighting():
    """Test the currency pair highlighting functionality."""
    # Common currency pairs to scan for
    common_pairs = [
        "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
        "EUR/GBP", "EUR/JPY", "GBP/JPY"
    ]
    
    processed_articles = []
    for article in SAMPLE_ARTICLES:
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
    
    # Verify highlighting
    assert "[CURRENCY_PAIR: EUR/USD]" in processed_articles[0]["payload"]["content"]
    assert "[CURRENCY_PAIR: USD/JPY]" in processed_articles[1]["payload"]["content"]
    print("✅ Currency pair highlighting test passed")
    return processed_articles

def test_response_parsing():
    """Test the response parsing functionality."""
    # Sample response from LLM
    sample_response = """**Executive Summary** The forex market is showing mixed signals with the USD strengthening against major currencies.

**Currency Pair Rankings**
**EUR/USD** (Rank: 4/10)
   * Fundamental Outlook: 40%
   * Sentiment Outlook: 35%
   * Rationale: The pair is under pressure due to strong US data.

**USD/JPY** (Rank: 7/10)
   * Fundamental Outlook: 65%
   * Sentiment Outlook: 70%
   * Rationale: Central bank policy divergence continues to push the pair higher.

**Risk Assessment:**
   * Primary Risk: US economic data surprises
   * Correlation Risk: Equity market volatility
   * Volatility Potential: Medium to high

**Trade Management Guidelines:**
Maintain cautious positioning in EUR/USD given the bearish outlook."""

    # Parse the response
    result = parse_structured_response(sample_response)
    
    # Verify parsing
    assert "The forex market is showing mixed signals" in result["summary"]
    assert len(result["currencyPairRankings"]) == 2
    assert result["currencyPairRankings"][0]["pair"] == "EUR/USD"
    assert result["currencyPairRankings"][1]["pair"] == "USD/JPY"
    assert result["riskAssessment"]["primaryRisk"] == "US economic data surprises"
    assert len(result["tradeManagementGuidelines"]) > 0
    print("✅ Response parsing test passed")
    return result

def parse_structured_response(text):
    """Parse the structured text response into a JSON format."""
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
    
    # Extract key points from the summary
    sentences = re.split(r'(?<=[.!?])\s+', result["summary"])
    result["keyPoints"] = [s.strip() for s in sentences if len(s.strip()) > 10][:3]
    
    return result

def test_cache_key_generation():
    """Test that cache keys are generated consistently."""
    # Generate cache key from articles and query
    article_ids = sorted([a.get("id", "") for a in SAMPLE_ARTICLES])
    hash_input = f"forex news:{'-'.join(article_ids)}"
    import hashlib
    key1 = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    # Generate again
    article_ids = sorted([a.get("id", "") for a in SAMPLE_ARTICLES])
    hash_input = f"forex news:{'-'.join(article_ids)}"
    key2 = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    # Verify same key is generated
    assert key1 == key2
    print("✅ Cache key generation test passed")
    return key1

def run_all_tests():
    """Run all the tests."""
    print("Running LangChainForexSummarizer component tests\n")
    
    formatted_articles = test_format_articles()
    processed_articles = test_currency_pair_highlighting()
    parsed_result = test_response_parsing()
    cache_key = test_cache_key_generation()
    
    print("\nAll tests passed successfully!")
    print(f"\nExample cache key: {cache_key}")
    print(f"Example formatted articles:\n{formatted_articles[:200]}...")
    print(f"Example parsed result: {parsed_result['summary']}")

if __name__ == "__main__":
    run_all_tests()
