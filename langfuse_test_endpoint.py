"""
Test endpoint to diagnose Langfuse connectivity issues.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import traceback
from loguru import logger

from utils.monitoring.langfuse import langfuse_monitor
import langfuse_debug

router = APIRouter()

@router.get("/test-langfuse-detailed")
async def test_langfuse_detailed():
    """Detailed test of Langfuse connectivity with diagnostics."""
    try:
        # First check basic connectivity
        connectivity_results = langfuse_debug.test_langfuse_connectivity()
        
        # Then check SDK installation
        sdk_info = langfuse_debug.check_langfuse_sdk()
        
        # Try direct API call to create a trace
        direct_api_result = langfuse_debug.test_direct_trace_creation()
        
        # Now try using our monitor
        monitor_results = {
            "enabled": langfuse_monitor.enabled,
            "host": langfuse_monitor.langfuse_host,
            "project": getattr(langfuse_monitor, 'project_name', 'unknown'),
            "client_initialized": hasattr(langfuse_monitor, 'langfuse') and langfuse_monitor.langfuse is not None
        }
        
        trace_result = None
        event_result = None
        flush_result = None
        
        # Only attempt SDK operations if monitor is enabled
        if langfuse_monitor.enabled and monitor_results["client_initialized"]:
            # Try to create a trace
            try:
                logger.info("Creating test trace with SDK...")
                trace_id = langfuse_monitor.create_trace(
                    name="diagnostic_test",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "source": "test_endpoint"
                    },
                    tags=["test", "diagnostics"]
                )
                trace_result = {
                    "success": bool(trace_id),
                    "trace_id": trace_id
                }
                logger.info(f"Trace created with ID: {trace_id}")
            except Exception as e:
                logger.error(f"Error creating trace: {e}")
                trace_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": str(type(e)),
                    "traceback": traceback.format_exc()
                }
            
            # Try to create an event
            try:
                logger.info("Creating test event with SDK...")
                event_id = langfuse_monitor.log_event(
                    name="diagnostic_event",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "source": "test_endpoint"
                    }
                )
                event_result = {
                    "success": bool(event_id),
                    "event_id": event_id
                }
                logger.info(f"Event created with ID: {event_id}")
            except Exception as e:
                logger.error(f"Error creating event: {e}")
                event_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": str(type(e)),
                    "traceback": traceback.format_exc()
                }
            
            # Try to flush data
            try:
                logger.info("Explicitly flushing Langfuse data...")
                langfuse_monitor.flush()
                flush_result = {
                    "success": True
                }
                logger.info("Flush completed successfully")
            except Exception as e:
                logger.error(f"Error flushing data: {e}")
                flush_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": str(type(e)),
                    "traceback": traceback.format_exc()
                }
        
        # Compile full results
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "connectivity": connectivity_results,
            "sdk_info": sdk_info,
            "direct_api": direct_api_result,
            "monitor": monitor_results,
            "trace_test": trace_result,
            "event_test": event_result,
            "flush_test": flush_result
        }
    except Exception as e:
        logger.error(f"Error in Langfuse test endpoint: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
