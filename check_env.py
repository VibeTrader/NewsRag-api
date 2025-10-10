#!/usr/bin/env python3
"""
Environment Variable Checker for NewsRag API
Run this to verify all required environment variables are set correctly
"""
import os
import sys
from typing import List, Dict, Tuple

def check_required_env_vars() -> Tuple[bool, List[str]]:
    """Check if all required environment variables are set."""
    
    # Required environment variables
    required_vars = [
        # Azure OpenAI Configuration
        ("AZURE_OPENAI_DEPLOYMENT", "Azure OpenAI deployment name"),
        ("OPENAI_BASE_URL", "Azure OpenAI endpoint URL"),
        
        # Qdrant Configuration  
        ("QDRANT_URL", "Qdrant database URL"),
        ("QDRANT_API_KEY", "Qdrant API key"),
        ("QDRANT_COLLECTION_NAME", "Qdrant collection name"),
        
        # Basic App Configuration
        ("WEBSITES_PORT", "App port (should be 8000)"),
        ("ENVIRONMENT", "Environment (production/development)"),
    ]
    
    # Optional but recommended
    optional_vars = [
        ("AZURE_OPENAI_API_VERSION", "Azure OpenAI API version"),
        ("DEPLOYMENT_REGION", "Deployment region identifier"),
        ("MAX_TOKENS", "Maximum tokens for LLM"),
        ("TEMPERATURE", "LLM temperature setting"),
    ]
    
    # API Key - check both possible names
    api_key_vars = ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"]
    
    missing_vars = []
    present_vars = []
    
    print("=== NewsRag API Environment Variable Check ===\n")
    
    # Check API key (special case - need at least one)
    api_key_found = False
    for var in api_key_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 20)} (found)")
            api_key_found = True
            present_vars.append(var)
        else:
            print(f"❌ {var}: Not set")
    
    if not api_key_found:
        missing_vars.append("API_KEY (need either AZURE_OPENAI_API_KEY or OPENAI_API_KEY)")
    
    print()
    
    # Check required variables
    print("Required Variables:")
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value if var not in ["QDRANT_API_KEY"] else "*" * min(len(value), 20)
            print(f"✅ {var}: {display_value}")
            present_vars.append(var)
        else:
            print(f"❌ {var}: Not set ({description})")
            missing_vars.append(var)
    
    print("\nOptional Variables:")
    for var, description in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
            present_vars.append(var)
        else:
            print(f"⚠️  {var}: Not set ({description}) - using default")
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"✅ Variables set: {len(present_vars)}")
    print(f"❌ Missing required: {len(missing_vars)}")
    
    if missing_vars:
        print(f"\n🚨 Missing required variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\nYour app will fail to start until these are set.")
        return False, missing_vars
    else:
        print(f"\n🎉 All required environment variables are set!")
        return True, []

def check_azure_app_service_vars():
    """Check Azure App Service specific variables."""
    print(f"\n=== Azure App Service Configuration ===")
    
    azure_vars = [
        ("WEBSITES_PORT", "8000"),
        ("SCM_DO_BUILD_DURING_DEPLOYMENT", "true"),
        ("ENABLE_ORYX_BUILD", "true"), 
        ("WEBSITES_ENABLE_APP_SERVICE_STORAGE", "false"),
    ]
    
    for var, expected in azure_vars:
        value = os.getenv(var, "").lower()
        expected_lower = expected.lower()
        
        if value == expected_lower:
            print(f"✅ {var}: {value} (correct)")
        else:
            print(f"❌ {var}: {value or 'Not set'} (should be {expected})")

if __name__ == "__main__":
    print("Checking environment variables for NewsRag API...\n")
    
    # Load environment variables from .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📁 Loaded variables from .env file\n")
    except ImportError:
        print("💡 python-dotenv not available, checking system env vars only\n")
    except Exception as e:
        print(f"⚠️ Error loading .env: {e}\n")
    
    # Check required variables
    success, missing = check_required_env_vars()
    
    # Check Azure-specific variables
    check_azure_app_service_vars()
    
    # Exit with appropriate code
    if not success:
        print(f"\n❌ Environment check failed. Fix the missing variables and try again.")
        sys.exit(1)
    else:
        print(f"\n✅ Environment check passed. Your app should start successfully.")
        sys.exit(0)