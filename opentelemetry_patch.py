"""
Patch for Azure App Service OpenTelemetry conflict.
This file must be imported before any other imports in api.py.
"""

import os
import sys
import importlib.util
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opentelemetry_patch")

def patch_opentelemetry():
    """
    Patch the OpenTelemetry module to resolve the _ExtendedAttributes import error
    """
    logger.info("Applying OpenTelemetry patch for Azure App Service...")
    
    # Check if we're in Azure App Service
    in_azure = os.environ.get("WEBSITE_SITE_NAME") is not None
    
    if in_azure:
        logger.info("Running in Azure App Service, applying patch...")
        
        # Path to the problematic file
        util_types_path = "/agents/python/opentelemetry/util/types.py"
        
        if os.path.exists(util_types_path):
            logger.info(f"Found pre-installed OpenTelemetry at {util_types_path}")
            
            # Add the _ExtendedAttributes class to the module
            try:
                # Create a new module
                spec = importlib.util.spec_from_file_location("opentelemetry.util.types", util_types_path)
                types_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(types_module)
                
                # Add the missing class
                class _ExtendedAttributes:
                    def __init__(self):
                        pass
                
                # Add the class to the module
                types_module._ExtendedAttributes = _ExtendedAttributes
                
                # Replace the module in sys.modules
                sys.modules["opentelemetry.util.types"] = types_module
                
                logger.info("Successfully patched OpenTelemetry types module")
                return True
            except Exception as e:
                logger.error(f"Error patching OpenTelemetry: {e}")
                return False
        else:
            logger.info("Pre-installed OpenTelemetry not found, no patch needed")
            return False
    else:
        logger.info("Not running in Azure App Service, no patch needed")
        return False

# Apply the patch
patch_applied = patch_opentelemetry()
