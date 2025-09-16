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
        logger.info("Applying OpenTelemetry patch for Azure App Service...")
        
        # Check if we're running in Azure App Service
        if not os.environ.get("WEBSITE_SITE_NAME"):
            logger.info("Not running in Azure App Service, no patch needed")
            return
            
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
            
        except ImportError:
            logger.warning("OpenTelemetry modules not available, skipping patch")
            
    except Exception as e:
        logger.warning(f"Patching failed, disabling OpenTelemetry completely: {e}")
        
        # Create mock modules to avoid import errors
        try:
            import sys
            from types import ModuleType
            
            # Create mock modules
            mock_modules = [
                "opentelemetry",
                "opentelemetry.sdk",
                "opentelemetry.sdk.trace",
                "opentelemetry.exporter",
                "opentelemetry.exporter.otlp",
                "opentelemetry.exporter.otlp.proto",
                "opentelemetry.exporter.otlp.proto.grpc",
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
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
                    
            # Add mock classes to modules
            sys.modules["opentelemetry.sdk.trace"].TracerProvider = MockTracerProvider
            sys.modules["opentelemetry.exporter.otlp.proto.grpc.trace_exporter"].OTLPSpanExporter = MockOTLPSpanExporter
            sys.modules["opentelemetry.sdk.trace.export"] = ModuleType("opentelemetry.sdk.trace.export")
            sys.modules["opentelemetry.sdk.trace.export"].BatchSpanProcessor = MockBatchSpanProcessor
            
            # Create a mock trace module
            trace_module = ModuleType("opentelemetry.trace")
            
            def set_tracer_provider(*args, **kwargs):
                pass
                
            trace_module.set_tracer_provider = set_tracer_provider
            sys.modules["opentelemetry.trace"] = trace_module
            
            logger.info("Successfully disabled OpenTelemetry")
            
        except Exception as mock_error:
            logger.error(f"Failed to create mock OpenTelemetry modules: {mock_error}")

# Create a mock Langfuse module as well to avoid import errors
def create_mock_langfuse():
    """Create a mock Langfuse module to avoid import errors."""
    try:
        import sys
        from types import ModuleType
        
        # Check if Langfuse is already imported
        if "langfuse" in sys.modules:
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
                
            def update_trace(self, *args, **kwargs):
                pass
                
            def flush(self, *args, **kwargs):
                pass
                
        # Add the mock class to the module
        langfuse_module.Langfuse = MockLangfuse
        
        logger.info("Created mock Langfuse module as backup")
        
    except Exception as e:
        logger.error(f"Failed to create mock Langfuse module: {e}")

# Apply the patch
patch_opentelemetry()

# Create mock Langfuse module
create_mock_langfuse()
