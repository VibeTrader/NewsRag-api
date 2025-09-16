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
    Patch the OpenTelemetry module to resolve import errors in Azure App Service
    """
    logger.info("Applying OpenTelemetry patch for Azure App Service...")
    
    # Check if we're in Azure App Service
    in_azure = os.environ.get("WEBSITE_SITE_NAME") is not None
    
    if in_azure:
        logger.info("Running in Azure App Service, applying patch...")
        
        # Apply multiple patches
        patched_anything = False
        
        # Patch 1: _ExtendedAttributes in opentelemetry.util.types
        util_types_path = "/agents/python/opentelemetry/util/types.py"
        if os.path.exists(util_types_path):
            logger.info(f"Found pre-installed OpenTelemetry types at {util_types_path}")
            
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
                
                logger.info("Successfully patched opentelemetry.util.types module")
                patched_anything = True
            except Exception as e:
                logger.error(f"Error patching opentelemetry.util.types: {e}")
        
        # Patch 2: _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER in opentelemetry.sdk.environment_variables
        env_vars_path = "/agents/python/opentelemetry/sdk/environment_variables/__init__.py"
        if os.path.exists(env_vars_path):
            logger.info(f"Found pre-installed OpenTelemetry environment variables at {env_vars_path}")
            
            try:
                # Create a new module
                spec = importlib.util.spec_from_file_location("opentelemetry.sdk.environment_variables", env_vars_path)
                env_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(env_module)
                
                # Add the missing variable
                env_module._OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER = "OTEL_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER"
                
                # Replace the module in sys.modules
                sys.modules["opentelemetry.sdk.environment_variables"] = env_module
                
                logger.info("Successfully patched opentelemetry.sdk.environment_variables module")
                patched_anything = True
            except Exception as e:
                logger.error(f"Error patching opentelemetry.sdk.environment_variables: {e}")
        
        # Patch 3: Create a mock exporter to avoid any other potential issues
        try:
            class MockOTLPSpanExporter:
                def __init__(self, *args, **kwargs):
                    pass
                
                def export(self, spans):
                    return None
                
                def shutdown(self):
                    return None
            
            # Create a mock module
            class MockExporterModule:
                OTLPSpanExporter = MockOTLPSpanExporter
            
            # Register the mock module
            sys.modules["opentelemetry.exporter.otlp.proto.http.trace_exporter"] = MockExporterModule()
            logger.info("Created mock OTLPSpanExporter")
            patched_anything = True
        except Exception as e:
            logger.error(f"Error creating mock exporter: {e}")
        
        return patched_anything
    else:
        logger.info("Not running in Azure App Service, no patch needed")
        return False

# Apply the patch
patch_applied = patch_opentelemetry()

# Disable OpenTelemetry completely as a last resort if patching fails
if not patch_applied:
    logger.warning("Patching failed, disabling OpenTelemetry completely")
    try:
        # Create mock modules for key OpenTelemetry components
        class MockModule:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None
        
        # Replace key modules with mocks
        sys.modules["opentelemetry"] = MockModule()
        sys.modules["opentelemetry.sdk"] = MockModule()
        sys.modules["opentelemetry.exporter"] = MockModule()
        sys.modules["opentelemetry.trace"] = MockModule()
        
        logger.info("Successfully disabled OpenTelemetry")
    except Exception as e:
        logger.error(f"Error disabling OpenTelemetry: {e}")

# Now let's also create a mock Langfuse if all else fails
try:
    class MockLangfuse:
        def __init__(self, *args, **kwargs):
            pass
            
        def create_event(self, *args, **kwargs):
            return "mock-id"
            
        def create_trace(self, *args, **kwargs):
            return "mock-trace-id"
            
        def create_generation(self, *args, **kwargs):
            return "mock-generation-id"
            
        def create_observation(self, *args, **kwargs):
            return "mock-observation-id"
            
        def flush(self, *args, **kwargs):
            pass
    
    # Add the mock implementation to sys.modules as a backup
    # This will only be used if the real import fails
    sys.modules["langfuse_mock"] = type("LangfuseMockModule", (), {"Langfuse": MockLangfuse})
    logger.info("Created mock Langfuse module as backup")
except Exception as e:
    logger.error(f"Error creating mock Langfuse: {e}")

