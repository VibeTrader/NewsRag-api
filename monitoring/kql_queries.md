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