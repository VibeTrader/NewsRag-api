"""
Test script for OpenTelemetry patch
"""
import os
import sys
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Set environment variable to simulate Azure App Service
os.environ["WEBSITE_SITE_NAME"] = "test-site"

# Import the patch
print("Importing OpenTelemetry patch...")
import opentelemetry_patch

# Try to import the patched modules
print("\nTesting imports that would normally fail:")
try:
    from opentelemetry.util.types import _ExtendedAttributes
    print("SUCCESS: Successfully imported _ExtendedAttributes")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")

try:
    from opentelemetry.sdk.environment_variables import _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    print("SUCCESS: Successfully imported _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")

# Try to import Langfuse modules
print("\nTesting Langfuse imports:")
try:
    from langfuse._client.span_processor import LangfuseSpanProcessor
    print("SUCCESS: Successfully imported LangfuseSpanProcessor")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")

try:
    from langfuse import Langfuse
    print("SUCCESS: Successfully imported Langfuse")
    
    # Test creating a Langfuse instance
    lf = Langfuse(secret_key="test", public_key="test")
    trace_id = lf.create_trace(name="test")
    print(f"SUCCESS: Created trace: {trace_id}")
except ImportError as e:
    print(f"FAIL: Import failed: {e}")
except Exception as e:
    print(f"FAIL: Error using Langfuse: {e}")

print("\nPatch test completed.")
