"""
Langfuse integration for your application.

IMPORTANT: This is a specialized integration for Langfuse 3.3.4 or higher.
"""

import os
import sys
from loguru import logger

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the simplified Langfuse monitor
from simple_langfuse import SimpleLangfuseMonitor

# Create a placeholder for StatefulTraceClient
class StatefulTraceClient:
    """Compatibility class for StatefulTraceClient."""
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get('id', '')
        self.name = kwargs.get('name', '')
        self.span = kwargs.get('span')
        self.langfuse = kwargs.get('langfuse')
        
    def generation(self, *args, **kwargs):
        """Compatibility method for generation."""
        return self
        
    def span(self, *args, **kwargs):
        """Compatibility method for span."""
        return self
        
    def score(self, *args, **kwargs):
        """Compatibility method for score."""
        return self

# Create a singleton instance
langfuse_monitor = SimpleLangfuseMonitor()

# Export with the original class name for backward compatibility
LangfuseMonitor = SimpleLangfuseMonitor

# Export the monitor and compatibility classes
__all__ = ['langfuse_monitor', 'LangfuseMonitor', 'StatefulTraceClient']
