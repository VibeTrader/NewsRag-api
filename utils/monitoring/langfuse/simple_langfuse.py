"""
Simple Langfuse integration with current SDK methods.
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

try:
    # Attempt to import Langfuse with version detection
    from langfuse import Langfuse
    import importlib.metadata
    try:
        langfuse_version = importlib.metadata.version("langfuse")
        logger.info(f"Detected Langfuse version: {langfuse_version}")
        
        # Handle different Langfuse API versions
        if langfuse_version.startswith("3."):
            logger.info("Using Langfuse 3.x API")
            # Import observe for Langfuse 3.x
            try:
                from langfuse import observe
                logger.info("Successfully imported Langfuse observe decorator")
            except ImportError:
                logger.warning("observe decorator not available in this Langfuse version")
    except importlib.metadata.PackageNotFoundError:
        logger.warning("Could not determine Langfuse version")
except ImportError:
    # Import failed, try to use our mock implementation
    try:
        from langfuse_mock import Langfuse
        logger.warning("Using mock Langfuse implementation due to import error")
    except ImportError:
        # Define a simple mock class right here as last resort
        class Langfuse:
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
        logger.warning("Using inline mock Langfuse implementation due to import errors")

class SimpleLangfuseMonitor:
    """Simplified Langfuse monitoring client for tracking LLM operations."""
    
    def __init__(self, app=None):
        """Initialize Langfuse monitoring client.
        
        Args:
            app: Optional FastAPI app instance
        """
        # Load credentials from environment variables
        self.langfuse_host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
        self.langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.project_name = os.getenv("PROJECT_NAME", "newsragnarok")
        
        # Check if credentials are available
        if not self.langfuse_secret_key or not self.langfuse_public_key:
            logger.warning("Langfuse credentials not found. Monitoring will be disabled.")
            self.enabled = False
            self.langfuse = None
        else:
            # Initialize Langfuse client
            try:
                # Add explicit debugging
                logger.info(f"Initializing Langfuse client with host: {self.langfuse_host}")
                logger.info(f"Using project name: {self.project_name}")
                
                # Check SDK version to use appropriate initialization
                try:
                    import importlib.metadata
                    langfuse_version = importlib.metadata.version("langfuse")
                    logger.info(f"Initializing with Langfuse SDK version: {langfuse_version}")
                except Exception as version_error:
                    logger.warning(f"Could not determine Langfuse version: {version_error}")
                    langfuse_version = "unknown"
                
                # Initialize with timeout and project name
                self.langfuse = Langfuse(
                    secret_key=self.langfuse_secret_key,
                    public_key=self.langfuse_public_key,
                    host=self.langfuse_host,
                    project_name=self.project_name,  # Explicitly set project name
                    timeout=30  # Add timeout to prevent hanging
                )
                
                # Test connection with simple API call
                try:
                    # Try to create a simple event to verify connectivity
                    test_id = self.langfuse.create_event(
                        name="initialization_test",
                        metadata={"timestamp": datetime.now().isoformat()}
                    )
                    self.langfuse.flush()  # Force flush to verify connectivity
                    logger.info(f"Langfuse connectivity test successful: {test_id}")
                    self.enabled = True
                except Exception as conn_error:
                    logger.error(f"Langfuse connectivity test failed: {conn_error}")
                    # Continue with client initialized but mark with warning
                    self.enabled = True
                    
                logger.info("Simple Langfuse monitoring initialized")
            except Exception as e:
                logger.error(f"Error initializing Langfuse: {e}")
                self.enabled = False
                self.langfuse = None
                
        # Store the app reference but don't add middleware
        self.app = app
    
    def log_api_request(self, method: str, path: str, query_params: Dict = None, headers: Dict = None, 
                        status_code: int = None, duration_ms: float = None) -> str:
        """Log an API request to Langfuse."""
        if not self.enabled or not self.langfuse:
            return None
            
        try:
            # Create a unique ID for this request
            request_id = str(uuid.uuid4())
            
            # Create a clean event for API requests
            self.langfuse.create_event(
                name=f"api:{method}_{path}",
                metadata={
                    "id": request_id,
                    "method": method,
                    "path": path,
                    "query_params": query_params or {},
                    "headers": {k: v for k, v in (headers or {}).items() 
                               if k.lower() not in ["authorization", "cookie"]},
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.now().isoformat(),
                    "source": "newsrag_api"
                }
            )
            
            self.langfuse.flush()
            logger.info(f"Logged API request to Langfuse: {method} {path}")
            return request_id
        except Exception as e:
            logger.error(f"Error logging API request to Langfuse: {e}")
            return None
    
    def log_llm_generation(self, model: str, prompt: str, completion: str, token_count: Dict = None) -> str:
        """Log an LLM generation to Langfuse."""
        if not self.enabled or not self.langfuse:
            return None
            
        try:
            # Create a unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Clean event structure for generations
            self.langfuse.create_event(
                name="llm_generation",
                metadata={
                    "id": generation_id,
                    "type": "generation",
                    "model": model,
                    "input": prompt,
                    "output": completion,
                    "token_count": token_count or {},
                    "timestamp": datetime.now().isoformat(),
                    "source": "newsrag_api"
                }
            )
            
            self.langfuse.flush()
            logger.info(f"Logged LLM generation to Langfuse: model={model}")
            return generation_id
        except Exception as e:
            logger.error(f"Error logging LLM generation to Langfuse: {e}")
            return None
    
    def create_trace(self, name=None, metadata=None, tags=None, user_id=None, session_id=None, input=None, output=None):
        """Create a trace in Langfuse.
        
        Args:
            name: Name of the trace
            metadata: Optional metadata for the trace
            tags: Optional tags for the trace
            user_id: Optional user ID
            session_id: Optional session ID
            input: Optional input data
            output: Optional output data
            
        Returns:
            The trace ID or a UUID string if Langfuse is disabled
        """
        if not self.enabled or not self.langfuse:
            return str(uuid.uuid4())
            
        try:
            # Create a trace ID
            trace_id = str(uuid.uuid4())
            
            # Build metadata for the trace
            meta = {
                "trace_id": trace_id,
                "trace_name": name or "unnamed_trace",
                "timestamp": datetime.now().isoformat(),
                "source": "newsrag_api"
            }
            
            # Add tags if provided
            if tags:
                meta["tags"] = tags
                
            # Add user ID if provided
            if user_id:
                meta["user_id"] = user_id
                
            # Add session ID if provided
            if session_id:
                meta["session_id"] = session_id
                
            # Add additional metadata if provided
            if metadata:
                meta.update(metadata)
                
            # Check which API method to use based on Langfuse version
            try:
                # First try the newer trace creation method with input/output
                if hasattr(self.langfuse, "trace"):
                    # Langfuse v3.x uses this method
                    trace = self.langfuse.trace(
                        id=trace_id,
                        name=name or "unnamed_trace",
                        metadata=meta,
                        tags=tags or [],
                        user_id=user_id,
                        session_id=session_id,
                        input=input,
                        output=output
                    )
                    logger.info(f"Created trace using trace() method: {trace_id}")
                    return trace_id
                elif hasattr(self.langfuse, "create_trace"):
                    # Try using standard create_trace method
                    self.langfuse.create_trace(
                        id=trace_id,
                        name=name or "unnamed_trace",
                        metadata=meta,
                        tags=tags or [],
                        user_id=user_id,
                        session_id=session_id,
                        input=input,
                        output=output
                    )
                    logger.info(f"Created trace using create_trace() method: {trace_id}")
                    return trace_id
                else:
                    # Fallback to event-based approach
                    logger.info("Trace methods not available, using event-based approach")
                    self.langfuse.create_event(
                        name=f"trace:{name or 'unnamed'}",
                        metadata=meta
                    )
                    logger.info(f"Created trace as event: {trace_id}")
                    return trace_id
            except Exception as e:
                logger.warning(f"Error using primary trace methods: {e}, falling back to create_observation")
                
                # Fallback to create_observation
                event_data = {
                    "id": trace_id,
                    "name": f"trace:{name or 'unnamed'}",
                    "metadata": meta
                }
                
                # Add input and output if provided
                if input is not None:
                    event_data["input"] = input
                if output is not None:
                    event_data["output"] = output
                    
                try:
                    self.langfuse.create_observation(**event_data)
                    logger.info(f"Created trace using create_observation: {trace_id}")
                except Exception as inner_e:
                    logger.error(f"Error using create_observation fallback: {inner_e}")
                    # Final fallback - create event
                    try:
                        self.langfuse.create_event(
                            name=f"trace:{name or 'unnamed'}",
                            metadata=meta
                        )
                        logger.info(f"Created trace as event (final fallback): {trace_id}")
                    except Exception as final_e:
                        logger.error(f"All trace creation methods failed: {final_e}")
            
            logger.info(f"Created trace in Langfuse: {name}")
            return trace_id
        except Exception as e:
            logger.error(f"Error creating trace in Langfuse: {e}")
            return str(uuid.uuid4())
            
    def track_span(self, trace, name, metadata=None, status="success", input=None, output=None):
        """Track a span within a trace.
        
        Args:
            trace: Trace ID or object
            name: Name of the span
            metadata: Optional metadata for the span
            status: Status of the span
            input: Optional explicit input data
            output: Optional explicit output data
        """
        if not self.enabled or not self.langfuse:
            return None
            
        try:
            # Get trace ID
            trace_id = trace if isinstance(trace, str) else getattr(trace, "id", str(uuid.uuid4()))
            span_id = str(uuid.uuid4())
            
            # Check for input/output in metadata if not explicitly provided
            if input is None and metadata and "input" in metadata:
                input = metadata.pop("input")
            if output is None and metadata and "output" in metadata:
                output = metadata.pop("output")
            
            # Prepare common observation data
            observation_data = {
                "id": span_id,
                "name": name,
                "type": "span",
                "metadata": metadata or {},
                "trace_id": trace_id,
                "status": status,
            }
            
            # Add input/output if available
            if input is not None:
                observation_data["input"] = input
            if output is not None:
                observation_data["output"] = output
            
            # Try different methods based on what's available in the SDK version
            try:
                # Try the observation method
                if hasattr(self.langfuse, "observation"):
                    self.langfuse.observation(**observation_data)
                    logger.info(f"Created span using observation method: {name}")
                    return span_id
                    
                # Try the span method directly
                elif hasattr(self.langfuse, "span"):
                    self.langfuse.span(**observation_data)
                    logger.info(f"Created span using span method: {name}")
                    return span_id
                    
                # Try create_observation
                elif hasattr(self.langfuse, "create_observation"):
                    self.langfuse.create_observation(**observation_data)
                    logger.info(f"Created span using create_observation: {name}")
                    return span_id
                    
                # Fallback to create_span
                elif hasattr(self.langfuse, "create_span"):
                    self.langfuse.create_span(**observation_data)
                    logger.info(f"Created span using create_span: {name}")
                    return span_id
                    
                else:
                    # No span-specific methods available, fallback to events
                    logger.warning("No span methods available in Langfuse SDK, falling back to events")
                    raise ValueError("No span methods available")
                    
            except Exception as e:
                logger.warning(f"Error using primary span methods: {e}, falling back to create_event")
                
                # Fallback to create_event with span-like structure
                event_data = {
                    "name": f"span:{name}",
                    "metadata": {
                        "span_id": span_id,
                        "trace_id": trace_id,
                        "span_name": name,
                        "status": status,
                        "timestamp": datetime.now().isoformat(),
                        "source": "newsrag_api"
                    }
                }
                
                # Add additional metadata if provided
                if metadata:
                    event_data["metadata"].update(metadata)
                    
                # Add input/output as metadata since events don't support them directly
                if input is not None:
                    event_data["metadata"]["input"] = str(input)[:500]  # Truncate to avoid oversized events
                if output is not None:
                    event_data["metadata"]["output"] = str(output)[:500]  # Truncate to avoid oversized events
                
                self.langfuse.create_event(**event_data)
                logger.info(f"Created span as event (fallback): {name}")
            
            logger.info(f"Tracked span in Langfuse: {name}")
            return span_id
        except Exception as e:
            logger.error(f"Error tracking span in Langfuse: {e}")
            return None
            
    def log_event(self, name: str, metadata: Dict = None) -> str:
        """Log a custom event to Langfuse."""
        if not self.enabled or not self.langfuse:
            return None
            
        try:
            # Create a unique ID for this event
            event_id = str(uuid.uuid4())
            
            # Build metadata for the event
            meta = {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat(),
                "source": "newsrag_api"
            }
            
            # Add additional metadata if provided
            if metadata:
                meta.update(metadata)
                
            # Create the event
            self.langfuse.create_event(
                name=name,
                metadata=meta
            )
            
            logger.info(f"Logged event to Langfuse: {name}")
            return event_id
        except Exception as e:
            logger.error(f"Error logging event to Langfuse: {e}")
            return None
            
    def count_tokens(self, text):
        """Estimate token count for a text string.
        
        Uses tiktoken for accurate counting if available, falls back to character estimation.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        # Try to use tiktoken for accurate counting
        try:
            import tiktoken
            # Use cl100k_base for Claude-compatible encoding
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)
            token_count = len(tokens)
            logger.debug(f"Counted {token_count} tokens using tiktoken")
            return token_count
        except Exception as e:
            logger.debug(f"Tiktoken unavailable, using character estimation: {e}")
            
            # Very simple estimation based on whitespace
            words = text.split()
            # Token count is typically 30% more than word count for English text
            estimated_tokens = int(len(words) * 1.3)
            logger.debug(f"Estimated {estimated_tokens} tokens from {len(words)} words")
            return max(1, estimated_tokens)
            
    def flush(self):
        """Flush any pending observations to Langfuse."""
        if self.enabled and self.langfuse:
            try:
                # Add more detailed logging
                logger.info("Starting Langfuse data flush operation...")
                
                # Try the standard flush method first
                if hasattr(self.langfuse, "flush"):
                    self.langfuse.flush()
                    logger.info("Flushed data to Langfuse using flush() method")
                # Some versions might use different methods
                elif hasattr(self.langfuse, "_flush"):
                    self.langfuse._flush()
                    logger.info("Flushed data to Langfuse using _flush() method")
                # Try client.flush if available
                elif hasattr(self.langfuse, "client") and hasattr(self.langfuse.client, "flush"):
                    self.langfuse.client.flush()
                    logger.info("Flushed data to Langfuse using client.flush() method")
                else:
                    # No explicit flush method available
                    logger.warning("No flush method available in Langfuse SDK")
                
                # Force network operations to complete by adding a small delay
                import time
                time.sleep(0.5)  # 500ms delay to ensure network operations complete
                
                logger.info("Flushed data to Langfuse")
            except Exception as e:
                import traceback
                logger.error(f"Error flushing data to Langfuse: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error traceback: {traceback.format_exc()}")
                
                # Try to diagnose network issues
                try:
                    import requests
                    response = requests.get(
                        f"{self.langfuse_host}/api/health", 
                        timeout=3,
                        headers={"Accept": "application/json"}
                    )
                    logger.info(f"Langfuse health check during error: Status {response.status_code}")
                except Exception as network_error:
                    logger.error(f"Network connectivity issue with Langfuse: {network_error}")
                
    def test_connection(self):
        """Test the connection to Langfuse."""
        if not self.enabled or not self.langfuse:
            return False
            
        try:
            # Create a test event
            self.langfuse.create_event(
                name="connection_test",
                metadata={
                    "test_time": datetime.now().isoformat(),
                    "source": "newsrag_api"
                }
            )
            
            # Flush the event
            self.langfuse.flush()
            return True
        except Exception as e:
            logger.error(f"Error testing connection to Langfuse: {e}")
            return False
