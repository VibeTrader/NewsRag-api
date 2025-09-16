"""
Langfuse integration for LangChain components in NewsRagnarok API.
"""

import os
from typing import Dict, Any, Optional
from loguru import logger

# Try to import Langfuse components with appropriate error handling
try:
    from langfuse import Langfuse
    # For Langfuse 3.x compatibility
    try:
        from langfuse import observe
    except ImportError:
        # Create a compatible observe decorator for older versions
        def observe(*args, **kwargs):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return wrapper
            return decorator
except ImportError:
    logger.warning("Langfuse import failed. Monitoring will be limited.")
    # Create placeholder classes if needed

# Create placeholder for LangfuseCallbackHandler
class LangfuseCallbackHandler:
    """Placeholder for LangfuseCallbackHandler which is not available."""
    def __init__(self, *args, **kwargs):
        # Add attributes that LangChain expects
        self.ignore_chain = False
        self.ignore_agent = False
        self.ignore_llm = False
        self.ignore_retriever = False
        self.ignore_chat_model = False
        
    # Add required methods
    def run_inline(self, *args, **kwargs):
        return None
        
    def raise_error(self, error):
        """Handle errors"""
        pass
        
    def on_text(self, *args, **kwargs):
        """Handle text events"""
        pass
        
    def on_llm_start(self, *args, **kwargs):
        pass
        
    def on_llm_end(self, *args, **kwargs):
        pass
        
    def on_llm_error(self, *args, **kwargs):
        pass
        
    def on_chain_start(self, *args, **kwargs):
        pass
        
    def on_chain_end(self, *args, **kwargs):
        pass
        
    def on_chain_error(self, *args, **kwargs):
        pass

from utils.monitoring.langfuse import langfuse_monitor

class LangChainMonitoring:
    """Langfuse monitoring for LangChain components."""
    
    def __init__(self, langfuse_monitor_instance=None):
        """Initialize the LangChain monitoring.
        
        Args:
            langfuse_monitor_instance: Optional LangfuseMonitor instance
        """
        self.langfuse_monitor = langfuse_monitor_instance or langfuse_monitor
        
        self.enabled = self.langfuse_monitor.enabled
        self.project_name = self.langfuse_monitor.project_name if hasattr(self.langfuse_monitor, 'project_name') else "newsragnarok"
        
        if self.enabled:
            logger.info("LangChain monitoring with Langfuse initialized")
    
    def get_callback_handler(self, trace_id: Optional[str] = None, tags: Optional[list] = None) -> Optional[LangfuseCallbackHandler]:
        """Get a Langfuse callback handler for LangChain.
        
        Args:
            trace_id: Optional trace ID to associate with LangChain operations
            tags: Optional tags to add to the trace
            
        Returns:
            LangfuseCallbackHandler or None if disabled
        """
        if not self.enabled:
            return None
        
        # Create a dummy callback handler
        try:
            logger.info("Creating placeholder Langfuse callback handler")
            callback = LangfuseCallbackHandler()
            return callback
        except Exception as e:
            logger.error(f"Failed to create Langfuse callback handler: {e}")
            return None
    
    def wrap_llm(self, llm: Any, trace_name: str = "llm_call") -> Any:
        """Wrap an LLM with Langfuse monitoring.
        
        Args:
            llm: LLM to wrap
            trace_name: Name for the trace
            
        Returns:
            Wrapped LLM or original LLM if monitoring is disabled
        """
        if not self.enabled:
            return llm
        
        try:
            # Get a callback handler
            callback = self.get_callback_handler(trace_name)
            
            # Add the callback to the LLM
            if hasattr(llm, "callbacks") and callback:
                if llm.callbacks is None:
                    llm.callbacks = [callback]
                else:
                    llm.callbacks.append(callback)
            
            return llm
        except Exception as e:
            logger.error(f"Failed to wrap LLM with Langfuse: {e}")
            return llm
    
    def wrap_chain(self, chain: Any, trace_name: str = "chain_execution") -> Any:
        """Wrap a LangChain chain with Langfuse monitoring.
        
        Args:
            chain: Chain to wrap
            trace_name: Name for the trace
            
        Returns:
            Wrapped chain or original chain if monitoring is disabled
        """
        if not self.enabled:
            return chain
        
        try:
            # Get a callback handler
            callback = self.get_callback_handler(trace_name)
            
            # Add the callback to the chain
            if hasattr(chain, "callbacks") and callback:
                if chain.callbacks is None:
                    chain.callbacks = [callback]
                else:
                    chain.callbacks.append(callback)
            
            return chain
        except Exception as e:
            logger.error(f"Failed to wrap chain with Langfuse: {e}")
            return chain
