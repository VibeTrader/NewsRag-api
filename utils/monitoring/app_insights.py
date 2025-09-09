"""
Azure Application Insights integration for monitoring and observability.
"""

import os
import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Callable
from fastapi import FastAPI, Request, Response
from loguru import logger
from applicationinsights import TelemetryClient
from applicationinsights.logging import LoggingHandler

class AppInsightsMonitor:
    """Azure Application Insights integration for monitoring."""
    
    def __init__(self, app: FastAPI, instrumentation_key: Optional[str] = None):
        """Initialize the Application Insights monitor.
        
        Args:
            app: FastAPI application instance
            instrumentation_key: Optional instrumentation key. If not provided, 
                                 will try to load from APPINSIGHTS_INSTRUMENTATIONKEY environment variable.
        """
        self.app = app
        
        # Get instrumentation key
        self.instrumentation_key = instrumentation_key or os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')
        if not self.instrumentation_key:
            logger.warning("No Application Insights instrumentation key found. Monitoring will be disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Initialize telemetry client
        self.telemetry_client = TelemetryClient(self.instrumentation_key)
        
        # Configure Python logging to send to Application Insights
        self._configure_logging()
        
        # Add middleware for request tracking
        self._add_middleware()
        
        # Add shutdown event handler to flush telemetry
        app.add_event_handler("shutdown", self.flush)
        
        logger.info("Application Insights monitoring initialized")
        
    def _configure_logging(self):
        """Configure logging integration with Application Insights."""
        if not self.enabled:
            return
            
        # Add handler for standard logging
        ai_handler = LoggingHandler(self.instrumentation_key)
        logging.getLogger().addHandler(ai_handler)
        
        # Configure loguru to send to standard logging
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level if it exists
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # Find caller from where originated the logged message
                frame, depth = logging.currentframe(), 2
                while frame and frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        
        # Add the handler to the standard logging
        logging.getLogger().addHandler(InterceptHandler())
        
    def _add_middleware(self):
        """Add middleware for request tracking."""
        if not self.enabled:
            return
            
        @self.app.middleware("http")
        async def telemetry_middleware(request: Request, call_next):
            """Middleware to track request telemetry."""
            # Generate a unique request ID if not present
            request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
            
            # Start timer
            start_time = time.time()
            
            # Store context for correlation
            self.telemetry_client.context.operation.id = request_id
            self.telemetry_client.context.operation.name = f"{request.method} {request.url.path}"
            
            # Process the request
            try:
                # Add the request ID to the response headers
                response = await call_next(request)
                
                # Calculate duration
                duration = (time.time() - start_time) * 1000
                
                # Extract query parameters safely
                query_params = {}
                for key, value in request.query_params.items():
                    query_params[key] = value
                
                # Track successful request
                self.telemetry_client.track_request(
                    name=f"{request.method} {request.url.path}",
                    url=str(request.url),
                    duration=duration,
                    response_code=response.status_code,
                    success=response.status_code < 400,
                    properties={
                        "request_id": request_id,
                        "endpoint": request.url.path,
                        "query_params": str(query_params)
                    }
                )
                
                # Ensure telemetry is sent
                self.telemetry_client.flush()
                
                return response
                
            except Exception as e:
                # Calculate duration
                duration = (time.time() - start_time) * 1000
                
                # Track failed request
                self.telemetry_client.track_request(
                    name=f"{request.method} {request.url.path}",
                    url=str(request.url),
                    duration=duration,
                    response_code=500,
                    success=False,
                    properties={
                        "request_id": request_id,
                        "endpoint": request.url.path,
                        "error": str(e)
                    }
                )
                
                # Track the exception
                self.telemetry_client.track_exception()
                
                # Ensure telemetry is sent
                self.telemetry_client.flush()
                
                # Re-raise the exception
                raise
    
    def track_metric(self, name: str, value: float, properties: Optional[Dict[str, str]] = None):
        """Track a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            properties: Optional properties to associate with the metric
        """
        if not self.enabled:
            return
            
        self.telemetry_client.track_metric(name, value, properties=properties)
    
    def track_event(self, name: str, properties: Optional[Dict[str, str]] = None):
        """Track a custom event.
        
        Args:
            name: Event name
            properties: Optional properties to associate with the event
        """
        if not self.enabled:
            return
            
        self.telemetry_client.track_event(name, properties=properties)
    
    def track_dependency(self, name: str, type_name: str, target: str, 
                        success: bool, duration: float, 
                        properties: Optional[Dict[str, str]] = None):
        """Track a dependency call.
        
        Args:
            name: Name of the dependency call
            type_name: Type of dependency (e.g., "HTTP", "Qdrant", "Azure OpenAI")
            target: Target system name
            success: Whether the call was successful
            duration: Duration of the call in milliseconds
            properties: Optional properties to associate with the dependency
        """
        if not self.enabled:
            return
            
        self.telemetry_client.track_dependency(
            name=name,
            data=target,
            type=type_name,
            success=success,
            duration=duration,
            properties=properties
        )
    
    def track_exception(self, properties: Optional[Dict[str, str]] = None):
        """Track an exception.
        
        Args:
            properties: Optional properties to associate with the exception
        """
        if not self.enabled:
            return
            
        self.telemetry_client.track_exception(properties=properties)
    
    def set_custom_properties(self, properties: Dict[str, str]):
        """Set custom properties that will be added to all telemetry.
        
        Args:
            properties: Dictionary of custom properties
        """
        if not self.enabled:
            return
            
        for key, value in properties.items():
            self.telemetry_client.context.properties[key] = value
    
    def flush(self):
        """Flush all telemetry immediately."""
        if self.enabled:
            self.telemetry_client.flush()
            logger.debug("Application Insights telemetry flushed")
    
    def wrap_dependency(self, name: str, type_name: str, target: str):
        """Decorator to track a function as a dependency.
        
        Args:
            name: Name of the dependency
            type_name: Type of dependency
            target: Target system name
            
        Returns:
            Decorated function that tracks timing and success
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                start_time = time.time()
                success = True
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    self.track_dependency(
                        name=name,
                        type_name=type_name,
                        target=target,
                        success=success,
                        duration=duration
                    )
            return wrapper
        return decorator