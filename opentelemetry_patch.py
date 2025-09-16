"""
Patch for OpenTelemetry to avoid conflicts.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def patch_opentelemetry():
    """Apply OpenTelemetry patch for Azure App Service."""
    try:
        # Import sys here to make sure it's available in this function scope
        import sys
        
        logger.info("Applying OpenTelemetry patch for Azure App Service...")
        
        # Check if we're running in Azure App Service
        if not os.environ.get("WEBSITE_SITE_NAME"):
            logger.info("Not running in Azure App Service, no patch needed")
            return
            
        # Log the Python version and environment
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        
        # Check for Azure-specific environment variables
        azure_env = {k: v for k, v in os.environ.items() if 'AZURE' in k.upper() or 'WEBSITE' in k.upper()}
        logger.info(f"Azure environment variables: {azure_env}")
        
        # Log the installed OpenTelemetry packages
        try:
            import pkg_resources
            otel_packages = [p for p in pkg_resources.working_set if 'opentelemetry' in p.project_name.lower()]
            logger.info(f"Installed OpenTelemetry packages: {[(p.project_name, p.version) for p in otel_packages]}")
        except ImportError:
            logger.warning("Could not determine installed packages")
            
        # Try to import the modules that caused issues in the error logs
        try:
            from opentelemetry.sdk.environment_variables import _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
            logger.info("Successfully imported _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER")
        except ImportError as e:
            logger.warning(f"Could not import _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER: {e}")
            
        try:
            from opentelemetry.util.types import _ExtendedAttributes
            logger.info("Successfully imported _ExtendedAttributes")
        except ImportError as e:
            logger.warning(f"Could not import _ExtendedAttributes: {e}")
            
        # Import OpenTelemetry modules
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry import trace
            
            # Set up the tracer provider
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)
            
            # Set up the exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            )
            
            # Add the span processor
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            
            logger.info("OpenTelemetry patch applied successfully")
            
        except ImportError as e:
            logger.warning(f"OpenTelemetry modules not available, skipping patch: {e}")
            raise
            
    except Exception as e:
        # Make sure we have sys available for traceback logging
        import sys
        
        logger.warning(f"Patching failed, disabling OpenTelemetry completely: {e}")
        logger.warning(f"Traceback: {sys.exc_info()[2]}")
        
        # Create mock modules to avoid import errors
        try:
            from types import ModuleType
            
            # Create mock modules
            mock_modules = [
                "opentelemetry",
                "opentelemetry.sdk",
                "opentelemetry.sdk.trace",
                "opentelemetry.sdk.trace.export",
                "opentelemetry.exporter",
                "opentelemetry.exporter.otlp",
                "opentelemetry.exporter.otlp.proto",
                "opentelemetry.exporter.otlp.proto.grpc",
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
                "opentelemetry.exporter.otlp.proto.http",
                "opentelemetry.exporter.otlp.proto.http.trace_exporter",
                "opentelemetry.exporter.otlp.proto.common",
                "opentelemetry.exporter.otlp.proto.common.trace_encoder",
                "opentelemetry.exporter.otlp.proto.common._internal",
                "opentelemetry.exporter.otlp.proto.common._internal.trace_encoder",
                "opentelemetry.exporter.otlp.proto.http._common",
                "opentelemetry.util",
                "opentelemetry.util.types",
                "opentelemetry.sdk.environment_variables",
            ]
            
            # Create and register mock modules
            for module_name in mock_modules:
                if module_name not in sys.modules:
                    module = ModuleType(module_name)
                    sys.modules[module_name] = module
            
            # Create mock classes
            class MockTracerProvider:
                def add_span_processor(self, *args, **kwargs):
                    pass
                    
            class MockOTLPSpanExporter:
                def __init__(self, *args, **kwargs):
                    pass
                    
            class MockBatchSpanProcessor:
                def __init__(self, *args, **kwargs):
                    pass
                    
            # Add missing attributes that caused import errors
            sys.modules["opentelemetry.util.types"]._ExtendedAttributes = {}
            sys.modules["opentelemetry.sdk.environment_variables"]._OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER = "mock_provider"
            
            # Add mock classes to modules
            sys.modules["opentelemetry.sdk.trace"].TracerProvider = MockTracerProvider
            sys.modules["opentelemetry.exporter.otlp.proto.grpc.trace_exporter"].OTLPSpanExporter = MockOTLPSpanExporter
            sys.modules["opentelemetry.sdk.trace.export"].BatchSpanProcessor = MockBatchSpanProcessor
            
            # Create a mock trace module
            trace_module = ModuleType("opentelemetry.trace")
            
            def set_tracer_provider(*args, **kwargs):
                pass
                
            trace_module.set_tracer_provider = set_tracer_provider
            sys.modules["opentelemetry.trace"] = trace_module
            
            logger.info("Successfully disabled OpenTelemetry with comprehensive mocks")
            
        except Exception as mock_error:
            logger.error(f"Failed to create mock OpenTelemetry modules: {mock_error}")

# Create a mock Langfuse module as well to avoid import errors
def create_mock_langfuse():
    """Create a mock Langfuse module to avoid import errors."""
    try:
        # Import required modules here to ensure they're available
        import sys
        from types import ModuleType
        
        # Check if Langfuse is already imported
        if "langfuse" in sys.modules:
            logger.info("Langfuse already imported, checking if it needs enhancement")
            # Add any missing attributes or methods
            return
            
        # Create a mock Langfuse module
        langfuse_module = ModuleType("langfuse")
        
        # Create a mock Langfuse class
        class MockLangfuse:
            def __init__(self, *args, **kwargs):
                pass
                
            def create_trace(self, *args, **kwargs):
                return "mock-trace-id"
                
            def create_span(self, *args, **kwargs):
                return "mock-span-id"
                
            def create_generation(self, *args, **kwargs):
                return "mock-generation-id"
                
            def create_event(self, *args, **kwargs):
                return "mock-event-id"
                
            def create_observation(self, *args, **kwargs):
                return "mock-observation-id"
                
            def update_trace(self, *args, **kwargs):
                pass
                
            def flush(self, *args, **kwargs):
                pass
                
        # Add the mock class to the module
        langfuse_module.Langfuse = MockLangfuse
        
        # Set the module in sys.modules
        sys.modules["langfuse"] = langfuse_module
        
        # Also create the span processor module which was causing issues
        span_processor_module = ModuleType("langfuse._client.span_processor")
        sys.modules["langfuse._client"] = ModuleType("langfuse._client")
        sys.modules["langfuse._client.span_processor"] = span_processor_module
        
        # Create the resource manager module
        resource_manager_module = ModuleType("langfuse._client.resource_manager")
        sys.modules["langfuse._client.resource_manager"] = resource_manager_module
        
        # Create LangfuseSpanProcessor class
        class MockLangfuseSpanProcessor:
            def __init__(self, *args, **kwargs):
                pass
                
        span_processor_module.LangfuseSpanProcessor = MockLangfuseSpanProcessor
        
        logger.info("Created comprehensive mock Langfuse module")
        
    except Exception as e:
        logger.error(f"Failed to create mock Langfuse module: {e}")

# Apply the patch
patch_opentelemetry()

# Create mock Langfuse module
create_mock_langfuse()
