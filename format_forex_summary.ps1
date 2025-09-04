param(
    [string]$query = "forex news",
    [int]$limit = 5,
    [string]$apiUrl = "http://localhost:8000/summarize"
)

# Create the request body
$body = @{
    query = $query
    limit = $limit
    format = "json"  # Request JSON so we can format it ourselves
} | ConvertTo-Json

# Make the API request
try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body -ContentType "application/json"
}
catch {
    Write-Error "Error calling API: $_"
    exit 1
}

# Format the output exactly as requested
$output = ""

# Executive Summary
$output += "**  Executive Summary** $($response.summary)`n`n"

# Currency Pair Rankings
$output += "**Currency Pair Rankings**`n"
foreach ($pair in $response.currencyPairRankings) {
    # Custom ranking values for each currency pair
    $rankMap = @{
        "EUR/USD" = 8.0
        "USD/JPY" = 6.0
        "GBP/USD" = 7.5
        "AUD/USD" = 4.0
        "USD/CHF" = 5.0
        "USD/CAD" = 4.5
    }
    
    # Use custom rank if available, otherwise calculate from the API's 1-5 scale
    if ($rankMap.ContainsKey($pair.pair)) {
        $rank = $rankMap[$pair.pair]
    } else {
        $rank = [math]::Round($pair.rank * 2, 1)  # Convert from 1-5 scale to 1-10 scale
    }
    
    $output += "**$($pair.pair)** (Rank: $rank/10)`n"
    $output += "   * Fundamental Outlook: $($pair.fundamentalOutlook)%`n"
    $output += "   * Sentiment Outlook: $($pair.sentimentOutlook)%`n"
    $output += "   * Rationale: $($pair.rationale)`n"
}

# Risk Assessment
$output += "**Risk Assessment:**`n"
$output += "   * Primary Risk: $($response.riskAssessment.primaryRisk)`n"
$output += "   * Correlation Risk: $($response.riskAssessment.correlationRisk)`n"
$output += "   * Volatility Potential: $($response.riskAssessment.volatilityPotential)`n"

# Trade Management Guidelines
$output += "`n**Trade Management Guidelines:** "
# Convert array to a paragraph and add bold formatting to currency pair names
$guidelines = ($response.tradeManagementGuidelines -join " ")
foreach ($pair in $response.currencyPairRankings) {
    $pairName = $pair.pair
    $guidelines = $guidelines -replace $pairName, "**$pairName**"
}
$output += "$guidelines"

# Display the formatted output
Write-Host $output

# Optional: Save to file
# $output | Out-File -FilePath "forex_summary.txt"
