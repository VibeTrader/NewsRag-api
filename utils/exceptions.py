"""
Custom exceptions for NewsRag API with proper error categorization
"""

from typing import Optional, Dict, Any
from enum import Enum

class ErrorCategory(Enum):
    """Categories of errors for proper tracking and alerting"""
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    INTERNAL = "internal"
    TIMEOUT = "timeout"

class NewsRagException(Exception):
    """Base exception for NewsRag API"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        service: Optional[str] = None,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.service = service
        self.original_error = original_error
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "category": self.category.value,
            "service": self.service,
            "details": self.details
        }

class EmbeddingError(NewsRagException):
    """Error during embedding generation"""
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        # Categorize based on error message
        category = self._categorize_error(str(original_error) if original_error else message)
        
        super().__init__(
            message=message,
            category=category,
            service="azure_openai",
            original_error=original_error,
            details=details
        )
    
    @staticmethod
    def _categorize_error(error_str: str) -> ErrorCategory:
        error_lower = error_str.lower()
        
        if any(x in error_lower for x in ["401", "unauthorized", "invalid key", "api key", "invalid_api_key"]):
            return ErrorCategory.AUTHENTICATION
        elif any(x in error_lower for x in ["404", "not found", "deployment", "resource not found"]):
            return ErrorCategory.CONFIGURATION
        elif any(x in error_lower for x in ["429", "rate limit", "quota", "too many requests"]):
            return ErrorCategory.RATE_LIMIT
        elif any(x in error_lower for x in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT
        elif any(x in error_lower for x in ["connection", "network", "unreachable", "connect"]):
            return ErrorCategory.SERVICE_UNAVAILABLE
        else:
            return ErrorCategory.INTERNAL

class QdrantError(NewsRagException):
    """Error during Qdrant operations"""
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        category = self._categorize_error(str(original_error) if original_error else message)
        
        super().__init__(
            message=message,
            category=category,
            service="qdrant",
            original_error=original_error,
            details=details
        )
    
    @staticmethod
    def _categorize_error(error_str: str) -> ErrorCategory:
        error_lower = error_str.lower()
        
        if any(x in error_lower for x in ["401", "unauthorized", "forbidden", "api key"]):
            return ErrorCategory.AUTHENTICATION
        elif any(x in error_lower for x in ["404", "not found", "collection"]):
            return ErrorCategory.NOT_FOUND
        elif any(x in error_lower for x in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT
        elif any(x in error_lower for x in ["connection", "network", "connect"]):
            return ErrorCategory.SERVICE_UNAVAILABLE
        else:
            return ErrorCategory.INTERNAL

class SearchError(NewsRagException):
    """Error during search operations"""
    pass

class SummaryError(NewsRagException):
    """Error during summary generation"""
    pass

class ConfigurationError(NewsRagException):
    """Error in configuration/environment"""
    
    def __init__(
        self,
        message: str,
        missing_vars: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            service="configuration",
            details={**(details or {}), "missing_vars": missing_vars or []}
        )
