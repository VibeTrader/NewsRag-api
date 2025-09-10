# NewsRag-api Tests

This directory contains tests for the NewsRag-api functionality.

## Running the Forex Summarizer Test

To test the LangChain-based forex summarizer implementation:

```bash
python test/forex_summarizer_test.py
```

This simple test validates the core functionality of the forex summarizer:

1. **Article Formatting**: Tests that articles are properly formatted for processing
2. **Currency Pair Highlighting**: Tests that currency pairs are correctly identified and highlighted
3. **Response Parsing**: Tests that structured information is correctly extracted from LLM responses
4. **Cache Key Generation**: Tests that cache keys are generated consistently

## Test Structure

- `forex_summarizer_test.py`: Simple test for the forex summarizer functionality
- `test_api_local.py`: Test for local API functionality
- `test_monitoring.py`: Test for monitoring functionality
