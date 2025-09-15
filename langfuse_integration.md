# Langfuse Monitoring Integration

This document explains how the Langfuse monitoring integration works in the NewsRag API.

## Overview

The Langfuse integration provides monitoring and observability for LLM operations, API requests, and general application events. It helps track performance, detect issues, and analyze usage patterns.

## Setup

The integration requires the following environment variables:

```
LANGFUSE_HOST=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
PROJECT_NAME=newsragnarok
```

## Features

The Langfuse integration supports:

1. **API Request Tracking**: Logs HTTP requests with path, method, parameters, and performance metrics
2. **LLM Generation Monitoring**: Tracks LLM prompts, completions, and token usage
3. **Trace Creation**: Groups related operations into traces for end-to-end visibility
4. **Span Tracking**: Captures subtasks within traces for detailed process analysis
5. **Custom Event Logging**: Records any custom events with metadata
6. **Error Tracking**: Captures exceptions and errors with context
7. **Token Counting**: Estimates token usage for texts

## Usage Examples

### Tracking API Requests

```python
langfuse_monitor.log_api_request(
    method="GET",
    path="/search",
    query_params={"q": "query", "limit": 10},
    status_code=200,
    duration_ms=125.5
)
```

### Logging LLM Generations

```python
langfuse_monitor.log_llm_generation(
    model="gpt-4",
    prompt="Summarize this article...",
    completion="The article discusses...",
    token_count={
        "prompt_tokens": 15,
        "completion_tokens": 25,
        "total_tokens": 40
    }
)
```

### Creating Traces and Spans

```python
# Create a trace
trace_id = langfuse_monitor.create_trace(
    name="summarize_process",
    metadata={"query": "example query"},
    tags=["summarization"]
)

# Add spans to the trace
langfuse_monitor.track_span(
    trace=trace_id,
    name="data_processing",
    metadata={"duration_ms": 85.3}
)
```

### Logging Events

```python
langfuse_monitor.log_event(
    name="cache_hit",
    metadata={"query": "example query"}
)
```

## Testing

You can test the Langfuse integration using the provided test script:

```bash
python test_langfuse.py
```

## Implementation Details

The integration uses the Langfuse SDK's `create_event` method to send data to Langfuse. It structures the metadata to optimize visibility in the Langfuse UI.

## Troubleshooting

If you encounter issues with the Langfuse integration:

1. Check that environment variables are set correctly
2. Verify that the Langfuse service is accessible
3. Look for error messages in the logs
4. Run the test script to validate the integration

## Performance Considerations

- The integration adds minimal overhead to API operations
- Events are flushed to Langfuse asynchronously
- For high-volume scenarios, consider selective monitoring
