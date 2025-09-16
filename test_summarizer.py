"""
Test script for news_summarizer.py import
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# First import the patch
print("Importing OpenTelemetry patch...")
import opentelemetry_patch

# Then try to import from news_summarizer
print("\nTesting news_summarizer import:")
try:
    from utils.summarization.news_summarizer import NewsSummarizer
    print("SUCCESS: Successfully imported NewsSummarizer")
    
    # Create an instance to make sure it initializes
    summarizer = NewsSummarizer()
    print("SUCCESS: Successfully created NewsSummarizer instance")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")
except Exception as e:
    print(f"FAIL: Error initializing NewsSummarizer: {e}")

print("\nTest completed.")
