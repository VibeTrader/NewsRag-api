# Create a configuration file for Azure App Service
# This file will be deployed to the server and tells the app how to start

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This is the first file that will be loaded
logger.info("Starting Azure App Service configuration")

# Add our custom path first in the Python path so our patched modules take precedence
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our patch to fix OpenTelemetry issues
logger.info("Applying OpenTelemetry patch")
try:
    import opentelemetry_patch
    logger.info("OpenTelemetry patch applied successfully")
except Exception as e:
    logger.error(f"Error applying OpenTelemetry patch: {e}")

# Start the main application
logger.info("Starting application")
