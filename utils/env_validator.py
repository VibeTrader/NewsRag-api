"""
Environment Variable Validator with Health Checks
Validates environment variables at startup and provides runtime health checks
"""

import os
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum

class EnvStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    MISSING = "missing"
    UNKNOWN = "unknown"

class EnvironmentValidator:
    """Validates environment variables and external service connectivity."""
    
    _instance = None
    _last_check: Optional[datetime] = None
    _check_interval = timedelta(minutes=5)
    _cached_status: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.required_vars = {
            "azure_openai": [
                ("OPENAI_BASE_URL", "Azure OpenAI endpoint"),
                ("AZURE_OPENAI_DEPLOYMENT", "Azure OpenAI deployment name"),
                ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "Embedding deployment name"),
            ],
            "qdrant": [
                ("QDRANT_URL", "Qdrant database URL"),
                ("QDRANT_API_KEY", "Qdrant API key"),
                ("QDRANT_COLLECTION_NAME", "Qdrant collection name"),
            ],
            "monitoring": [
                ("APPINSIGHTS_INSTRUMENTATIONKEY", "App Insights key (optional)"),
            ]
        }
        
        # API key can be either of these
        self.api_key_vars = ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"]
        
    def validate_env_vars(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate all required environment variables."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "missing_required": [],
            "warnings": [],
            "services": {}
        }
        
        # Check API key
        api_key = None
        for var in self.api_key_vars:
            if os.getenv(var):
                api_key = os.getenv(var)
                results["services"]["api_key"] = {
                    "status": EnvStatus.VALID.value,
                    "variable": var,
                    "preview": f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                }
                break
        
        if not api_key:
            results["missing_required"].append("API_KEY (AZURE_OPENAI_API_KEY or OPENAI_API_KEY)")
            results["services"]["api_key"] = {"status": EnvStatus.MISSING.value}
            results["overall_status"] = "unhealthy"
        
        # Check each service group
        for service, vars_list in self.required_vars.items():
            results["services"][service] = {"status": EnvStatus.VALID.value, "variables": {}}
            
            for var_name, description in vars_list:
                value = os.getenv(var_name)
                
                if not value:
                    if "optional" in description.lower():
                        results["warnings"].append(f"{var_name}: Not set ({description})")
                        results["services"][service]["variables"][var_name] = {
                            "status": EnvStatus.MISSING.value,
                            "optional": True
                        }
                    else:
                        results["missing_required"].append(f"{var_name}: {description}")
                        results["services"][service]["variables"][var_name] = {
                            "status": EnvStatus.MISSING.value,
                            "optional": False
                        }
                        results["services"][service]["status"] = EnvStatus.INVALID.value
                        results["overall_status"] = "unhealthy"
                else:
                    # Mask sensitive values
                    is_sensitive = "key" in var_name.lower() or "secret" in var_name.lower()
                    results["services"][service]["variables"][var_name] = {
                        "status": EnvStatus.VALID.value,
                        "value": f"{value[:8]}..." if is_sensitive and len(value) > 8 else value
                    }
        
        return results["overall_status"] == "healthy", results


    async def validate_azure_openai(self) -> Dict[str, Any]:
        """Validate Azure OpenAI connectivity and API key."""
        result = {
            "service": "azure_openai",
            "status": EnvStatus.UNKNOWN.value,
            "timestamp": datetime.now().isoformat(),
            "error": None,
            "details": {}
        }
        
        try:
            from openai import AzureOpenAI
            import httpx
            
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            endpoint = os.getenv("OPENAI_BASE_URL")
            deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-stocks")
            
            if not api_key or not endpoint:
                result["status"] = EnvStatus.MISSING.value
                result["error"] = "Missing API key or endpoint"
                return result
            
            http_client = httpx.Client(headers={"Accept-Encoding": "gzip, deflate"}, timeout=10.0)
            
            client = AzureOpenAI(
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=endpoint,
                http_client=http_client
            )
            
            # Test with a simple embedding request
            response = client.embeddings.create(
                input="test",
                model=deployment
            )
            
            if response.data and len(response.data) > 0:
                result["status"] = EnvStatus.VALID.value
                result["details"] = {
                    "deployment": deployment,
                    "embedding_dimensions": len(response.data[0].embedding)
                }
            else:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = "Empty response from embedding API"
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Categorize the error
            if "401" in error_str or "unauthorized" in error_str or "invalid" in error_str:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = f"Authentication failed - API key may be invalid or expired: {str(e)}"
            elif "404" in error_str or "not found" in error_str:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = f"Deployment not found - check AZURE_OPENAI_DEPLOYMENT: {str(e)}"
            elif "429" in error_str or "rate limit" in error_str:
                result["status"] = EnvStatus.VALID.value
                result["error"] = f"Rate limited - key is valid but hitting limits: {str(e)}"
            elif "timeout" in error_str or "connection" in error_str:
                result["status"] = EnvStatus.UNKNOWN.value
                result["error"] = f"Connection issue - check network/endpoint: {str(e)}"
            else:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = f"Azure OpenAI error: {str(e)}"
                
            logger.error(f"Azure OpenAI validation failed: {result['error']}")
        
        return result


    async def validate_qdrant(self) -> Dict[str, Any]:
        """Validate Qdrant connectivity."""
        result = {
            "service": "qdrant",
            "status": EnvStatus.UNKNOWN.value,
            "timestamp": datetime.now().isoformat(),
            "error": None,
            "details": {}
        }
        
        try:
            from qdrant_client import QdrantClient
            
            url = os.getenv("QDRANT_URL")
            api_key = os.getenv("QDRANT_API_KEY")
            collection = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
            
            if not url or not api_key:
                result["status"] = EnvStatus.MISSING.value
                result["error"] = "Missing Qdrant URL or API key"
                return result
            
            client = QdrantClient(url=url, api_key=api_key, timeout=10.0)
            
            # Test connection
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            result["status"] = EnvStatus.VALID.value
            result["details"] = {
                "collections_count": len(collection_names),
                "target_collection_exists": collection in collection_names
            }
            
            if collection not in collection_names:
                result["error"] = f"Collection '{collection}' not found"
                result["status"] = EnvStatus.INVALID.value
                
            client.close()
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "401" in error_str or "unauthorized" in error_str:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = f"Qdrant authentication failed: {str(e)}"
            elif "connection" in error_str or "timeout" in error_str:
                result["status"] = EnvStatus.UNKNOWN.value
                result["error"] = f"Qdrant connection issue: {str(e)}"
            else:
                result["status"] = EnvStatus.INVALID.value
                result["error"] = f"Qdrant error: {str(e)}"
                
            logger.error(f"Qdrant validation failed: {result['error']}")
        
        return result

    async def run_full_validation(self, force: bool = False) -> Dict[str, Any]:
        """Run full validation of all services."""
        now = datetime.now()
        
        # Use cached results if recent enough
        if not force and self._last_check and (now - self._last_check) < self._check_interval:
            return self._cached_status
        
        # Validate env vars first
        env_valid, env_results = self.validate_env_vars()
        
        # Run service validations in parallel
        azure_result, qdrant_result = await asyncio.gather(
            self.validate_azure_openai(),
            self.validate_qdrant(),
            return_exceptions=True
        )
        
        # Handle exceptions from gather
        if isinstance(azure_result, Exception):
            azure_result = {
                "service": "azure_openai",
                "status": EnvStatus.INVALID.value,
                "error": str(azure_result)
            }
        if isinstance(qdrant_result, Exception):
            qdrant_result = {
                "service": "qdrant",
                "status": EnvStatus.INVALID.value,
                "error": str(qdrant_result)
            }
        
        # Compile results
        self._cached_status = {
            "timestamp": now.isoformat(),
            "environment": env_results,
            "services": {
                "azure_openai": azure_result,
                "qdrant": qdrant_result
            },
            "overall_healthy": (
                env_valid and 
                azure_result.get("status") == EnvStatus.VALID.value and
                qdrant_result.get("status") == EnvStatus.VALID.value
            ),
            "critical_errors": []
        }
        
        # Collect critical errors
        if azure_result.get("status") != EnvStatus.VALID.value:
            self._cached_status["critical_errors"].append({
                "service": "azure_openai",
                "error": azure_result.get("error", "Unknown error")
            })
        if qdrant_result.get("status") != EnvStatus.VALID.value:
            self._cached_status["critical_errors"].append({
                "service": "qdrant", 
                "error": qdrant_result.get("error", "Unknown error")
            })
        
        self._last_check = now
        
        return self._cached_status

# Global validator instance
env_validator = EnvironmentValidator.get_instance()
