# KQL Queries for NewsRagnarok API Monitoring

This file contains useful Kusto Query Language (KQL) queries for analyzing logs and metrics in Azure Application Insights.

## API Performance Queries

### Overall API Request Volume
```kql
requests
| summarize count() by bin(timestamp, 1h), name
| render timechart
```

### API Response Times by Endpoint
```kql
requests
| where timestamp > ago(24h)
| summarize avg(duration), percentile(duration, 95), max(duration) by name
| sort by avg_duration desc
```

### Failed Requests
```kql
requests
| where success == false
| summarize count() by name, resultCode, bin(timestamp, 1h)
| sort by timestamp desc
```

## Search Performance Queries

### Search Latency
```kql
customMetrics
| where name == "search_latency"
| project timestamp, value, customDimensions
| extend query = tostring(customDimensions.query)
| extend threshold = tostring(customDimensions.threshold_used)
| summarize avg(value) by bin(timestamp, 1h), threshold
| render timechart
```

### Search Results Volume
```kql
customMetrics
| where name == "search_results_count"
| project timestamp, value, customDimensions
| extend query = tostring(customDimensions.query)
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

### No Results Searches
```kql
customEvents
| where name == "search_no_results"
| project timestamp, customDimensions
| extend query = tostring(customDimensions.query)
| summarize count() by bin(timestamp, 1h)
| render columnchart
```

## Summary Performance Queries

### Summary Generation Time
```kql
customMetrics
| where name == "summary_generation_time"
| project timestamp, value, customDimensions
| extend query = tostring(customDimensions.query)
| extend article_count = toint(customDimensions.article_count)
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

### Summary Article Count
```kql
customMetrics
| where name == "summary_article_count"
| project timestamp, value, customDimensions
| extend query = tostring(customDimensions.query)
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

### Summary Sentiment Distribution
```kql
customMetrics
| where name == "summary_sentiment_score"
| project timestamp, value, customDimensions
| extend sentiment = tostring(customDimensions.sentiment)
| summarize avg(value) by bin(timestamp, 1d), sentiment
| render columnchart
```

## Dependency Performance Queries

### Qdrant Search Performance
```kql
dependencies
| where name == "search_documents"
| where target == "vector_search"
| summarize avg(duration), percentile(duration, 95), max(duration) by bin(timestamp, 1h)
| render timechart
```

### Azure OpenAI Performance
```kql
dependencies
| where name == "generate_summary"
| where target == "summary_generation"
| summarize avg(duration), percentile(duration, 95), max(duration) by bin(timestamp, 1h)
| render timechart
```

### Dependency Failures
```kql
dependencies
| where success == false
| summarize count() by name, target, bin(timestamp, 1h)
| sort by timestamp desc
```

## Error Analysis Queries

### Exceptions by Operation
```kql
exceptions
| where timestamp > ago(24h)
| summarize count() by operation_Name, bin(timestamp, 1h)
| render barchart
```

### Exception Details
```kql
exceptions
| where timestamp > ago(24h)
| project timestamp, operation_Name, operation_Id, type, method, outerMessage, customDimensions
| sort by timestamp desc
```

### Operation Failures
```kql
requests
| where success == false
| join kind=inner (
    exceptions
    | project timestamp, operation_Id
) on operation_Id
| project timestamp, name, operation_Id, resultCode
| sort by timestamp desc
```

## User Experience Queries

### Top Searches
```kql
customEvents
| where name == "search_completed"
| project timestamp, customDimensions
| extend query = tostring(customDimensions.query)
| summarize count() by query
| top 10 by count_
| sort by count_ desc
```

### Top Currency Pairs
```kql
customEvents
| where name == "currency_pairs_analyzed"
| project timestamp, customDimensions
| extend pairs = tostring(customDimensions.pairs)
| summarize count() by pairs
| top 10 by count_
| sort by count_ desc
```

## Resource Utilization Queries

### Server Response Time vs Instance Count
```kql
requests
| summarize avg(duration) by bin(timestamp, 5m)
| join kind=fullouter (
    performanceCounters
    | where counter == "Process Count"
    | summarize avg(value) by bin(timestamp, 5m)
) on timestamp
| project timestamp, avg_duration, avg_value
| render timechart
```

### Memory Usage
```kql
performanceCounters
| where counter == "Available Bytes"
| summarize avg(value) by bin(timestamp, 5m)
| render timechart
```

## Critical Error Monitoring Queries (NEW)

### Authentication/Configuration Errors - CRITICAL
Use this to detect API key expiry or configuration issues:
```kql
customEvents
| where name in ("critical_api_error", "critical_search_error", "critical_summarize_error")
| where customDimensions.category in ("authentication", "configuration")
| project timestamp, 
    name, 
    service = tostring(customDimensions.service),
    category = tostring(customDimensions.category),
    error = tostring(customDimensions.error)
| sort by timestamp desc
```

### Startup Errors
Detect when application starts with issues:
```kql
customEvents
| where name == "startup_critical_error"
| project timestamp,
    service = tostring(customDimensions.service),
    error = tostring(customDimensions.error)
| sort by timestamp desc
```

### All Critical Events Dashboard
```kql
customEvents
| where name contains "critical" or name contains "startup"
| project timestamp,
    event = name,
    service = tostring(customDimensions.service),
    category = tostring(customDimensions.category),
    error = tostring(customDimensions.error)
| sort by timestamp desc
| take 100
```

### Error Category Distribution
```kql
customEvents
| where name contains "critical"
| extend category = tostring(customDimensions.category)
| summarize count() by category
| render piechart
```

### Embedding Failures by Type
```kql
exceptions
| where customDimensions.service == "azure_openai"
| extend category = tostring(customDimensions.category)
| summarize count() by category, bin(timestamp, 1h)
| render timechart
```

### Service Health Over Time
```kql
customEvents
| where name == "env_validation"
| project timestamp,
    healthy = tostring(customDimensions.overall_healthy),
    error_count = toint(customDimensions.critical_errors_count)
| summarize 
    HealthyCount = countif(healthy == "True"),
    UnhealthyCount = countif(healthy == "False")
    by bin(timestamp, 1h)
| render timechart
```

### Rate Limit Detection
```kql
customEvents
| where customDimensions.category == "rate_limit"
| union (
    requests
    | where resultCode == 429
    | project timestamp, name, customDimensions = pack("category", "rate_limit", "source", "http_response")
)
| summarize count() by bin(timestamp, 15m)
| render timechart
```

### Search/Summarize Failure Rate
```kql
requests
| where name contains "/search" or name contains "/summarize"
| summarize 
    Total = count(),
    Failed = countif(resultCode >= 500),
    FailureRate = round(countif(resultCode >= 500) * 100.0 / count(), 2)
    by bin(timestamp, 1h)
| project timestamp, Total, Failed, FailureRate
| render timechart
```

## Alert Verification Queries

### Verify Alert Events are Being Tracked
```kql
customEvents
| where timestamp > ago(24h)
| where name contains "critical" or name contains "startup" or name contains "error"
| summarize count() by name
| sort by count_ desc
```

### Check Exception Tracking
```kql
exceptions
| where timestamp > ago(24h)
| extend service = tostring(customDimensions.service)
| extend category = tostring(customDimensions.category)
| summarize count() by service, category
| sort by count_ desc
```

### Recent API Key Related Errors
```kql
union exceptions, customEvents
| where timestamp > ago(1h)
| where customDimensions.category == "authentication" 
    or customDimensions contains "api key"
    or customDimensions contains "unauthorized"
    or customDimensions contains "401"
| project timestamp, itemType, name, customDimensions
| sort by timestamp desc
```
