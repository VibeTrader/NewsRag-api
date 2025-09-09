# NewsRagnarok API Monitoring

This folder contains resources for monitoring the NewsRagnarok API using Azure Application Insights.

## Contents

- **setup_guide.md**: Step-by-step guide for setting up Azure Application Insights for the NewsRagnarok API
- **dashboard_template.json**: Template for creating an Azure Dashboard to visualize key metrics
- **kql_queries.md**: Useful KQL queries for analyzing logs and metrics

## Implementation Details

The NewsRagnarok API has been instrumented with the Application Insights SDK to track:

1. **API Endpoint Metrics**:
   - Request counts and response times
   - Error rates and types
   - Request volumes by endpoint

2. **Search Performance**:
   - Search latency
   - Result counts
   - Query patterns
   - Threshold usage

3. **Summarization Performance**:
   - Summary generation time
   - Article counts used in summaries
   - Sentiment distribution
   - Currency pair analysis

4. **External Dependencies**:
   - Qdrant vector database performance
   - Azure OpenAI service performance
   - Dependency failures

5. **Resource Utilization**:
   - CPU and memory usage
   - Instance counts
   - HTTP queue lengths

## Monitoring Architecture

The monitoring solution uses:

1. **Application Insights SDK**: Direct integration with the FastAPI application
2. **Custom Metrics**: Tracking business-specific metrics such as search quality and summary performance
3. **Dependency Tracking**: Monitoring external service calls to Qdrant and Azure OpenAI
4. **Structured Logging**: Enhanced logging with context for better troubleshooting
5. **Azure Dashboard**: Visual monitoring of key metrics
6. **Alert Rules**: Proactive notification of issues

## Getting Started

1. Review the **setup_guide.md** file for instructions on setting up Azure Application Insights
2. Use the **dashboard_template.json** file to create a monitoring dashboard
3. Refer to **kql_queries.md** for useful queries to analyze performance and troubleshoot issues

## Best Practices

1. **Regular Monitoring**: Check the dashboard daily to establish baseline performance
2. **Alert Tuning**: Adjust alert thresholds based on observed patterns
3. **Log Analysis**: Use KQL queries to investigate issues and identify optimization opportunities
4. **Metric Expansion**: Add additional custom metrics as the application evolves
5. **Long-term Analysis**: Set up continuous export to Azure Storage for historical trend analysis