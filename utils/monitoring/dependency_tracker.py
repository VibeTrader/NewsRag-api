"""
Dependency tracking wrappers for external services.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from loguru import logger

class DependencyTracker:
    """Wrapper to track dependencies for monitoring."""
    
    def __init__(self, monitor):
        """Initialize the dependency tracker.
        
        Args:
            monitor: The monitoring instance (AppInsightsMonitor)
        """
        self.monitor = monitor
    
    async def track_async(self, func, name: str, type_name: str, target: str, properties: Optional[Dict[str, str]] = None):
        """Track an async function call as a dependency.
        
        Args:
            func: Async function to call
            name: Name of the dependency
            type_name: Type of dependency
            target: Target system name
            properties: Optional properties to associate with the dependency
            
        Returns:
            Result of the function call
        """
        start_time = time.time()
        success = True
        
        try:
            result = await func
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = (time.time() - start_time) * 1000
            self.monitor.track_dependency(
                name=name,
                type_name=type_name,
                target=target,
                success=success,
                duration=duration,
                properties=properties
            )
    
    def track_sync(self, func, name: str, type_name: str, target: str, properties: Optional[Dict[str, str]] = None):
        """Track a synchronous function call as a dependency.
        
        Args:
            func: Function to call
            name: Name of the dependency
            type_name: Type of dependency
            target: Target system name
            properties: Optional properties to associate with the dependency
            
        Returns:
            Result of the function call
        """
        start_time = time.time()
        success = True
        
        try:
            result = func()
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = (time.time() - start_time) * 1000
            self.monitor.track_dependency(
                name=name,
                type_name=type_name,
                target=target,
                success=success,
                duration=duration,
                properties=properties
            )