from typing import List, Dict, Any
from loguru import logger

class MarketAnalyzer:
    """Advanced financial market analysis utilities."""
    
    @staticmethod
    def analyze_currency_strength(articles: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze currency strength mentions across articles."""
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']
        strength_scores = {curr: 0.0 for curr in currencies}
        mention_counts = {curr: 0 for curr in currencies}
        
        # Simple sentiment words
        positive_words = ['rise', 'gain', 'strengthen', 'increase', 'bullish', 'strong', 'higher']
        negative_words = ['fall', 'drop', 'weaken', 'decrease', 'bearish', 'weak', 'lower']
        
        for article in articles:
            content = article.get('content', '').lower()
            
            for currency in currencies:
                if currency.lower() in content:
                    mention_counts[currency] += 1
                    
                    # Simple sentiment analysis
                    pos_score = sum(content.count(word) for word in positive_words)
                    neg_score = sum(content.count(word) for word in negative_words)
                    
                    if pos_score > neg_score:
                        strength_scores[currency] += 1
                    elif neg_score > pos_score:
                        strength_scores[currency] -= 1
        
        # Normalize scores
        for currency in currencies:
            if mention_counts[currency] > 0:
                strength_scores[currency] = strength_scores[currency] / mention_counts[currency]
                
        return strength_scores
    
    @staticmethod
    def extract_currency_pairs(strength_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate currency pair recommendations based on relative strength."""
        currencies = list(strength_scores.keys())
        pairs = []
        
        # Generate major pairs
        for base in currencies:
            for quote in currencies:
                if base != quote and base != 'USD' and quote == 'USD':
                    # Calculate relative strength
                    relative_strength = strength_scores[base] - strength_scores[quote]
                    
                    if abs(relative_strength) > 0.1:  # Only include significant differences
                        sentiment = "bullish" if relative_strength > 0 else "bearish"
                        confidence = min(100, int(abs(relative_strength * 100) + 50))
                        
                        pairs.append({
                            "pair": f"{base}/{quote}",
                            "outlook": sentiment,
                            "confidence": confidence,
                            "reason": f"Relative strength analysis shows {base} is {'stronger' if relative_strength > 0 else 'weaker'} than {quote} based on recent news."
                        })
        
        # Sort by confidence
        pairs.sort(key=lambda x: x["confidence"], reverse=True)
        return pairs[:5]  # Return top 5 pairs
        
    @staticmethod
    def create_market_conditions_statement(articles: List[Dict[str, Any]], sentiment_score: int) -> str:
        """Generate a market conditions statement based on articles and sentiment."""
        # Identify common themes
        volatility_words = ['volatile', 'uncertainty', 'fluctuate', 'swing', 'erratic']
        risk_words = ['risk', 'concern', 'worry', 'fear', 'caution']
        opportunity_words = ['opportunity', 'potential', 'bullish', 'optimistic', 'positive']
        
        # Count occurrences
        volatility_count = 0
        risk_count = 0
        opportunity_count = 0
        
        for article in articles:
            content = article.get('content', '').lower()
            
            volatility_count += sum(content.count(word) for word in volatility_words)
            risk_count += sum(content.count(word) for word in risk_words)
            opportunity_count += sum(content.count(word) for word in opportunity_words)
        
        # Generate statement based on counts and sentiment
        if sentiment_score >= 70:
            base = "Market conditions show strong bullish sentiment with multiple upside catalysts"
        elif sentiment_score >= 55:
            base = "Market conditions reflect measured optimism with selective opportunities"
        elif sentiment_score <= 30:
            base = "Market conditions indicate significant bearish pressure and defensive positioning"
        elif sentiment_score <= 45:
            base = "Market conditions suggest caution with limited upside potential"
        else:
            base = "Market conditions appear mixed with balanced risk and reward"
            
        # Add modifiers
        modifiers = []
        if volatility_count > 3:
            modifiers.append("amid elevated volatility")
        if risk_count > opportunity_count * 2:
            modifiers.append("with heightened risk awareness")
        elif opportunity_count > risk_count * 2:
            modifiers.append("with emerging opportunities")
        
        # Combine
        if modifiers:
            return f"{base} {' '.join(modifiers)}."
        return f"{base}."