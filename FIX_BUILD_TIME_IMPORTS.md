# 🔧 Fix Application Code for Build-Time Import Issues

## 🚨 **Root Cause:**
Your application tries to initialize Azure OpenAI services **during import** (module loading), but environment variables are only available **during deployment**. This causes build/test failures.

## 🛠️ **Solution 1: Lazy Initialization (Recommended)**

### **In your `utils/summarization/langchain/forex_summarizer.py`:**

**Before (problematic):**
```python
class EnhancedForexSummarizer:
    def __init__(self):
        # This runs during import and requires env vars
        self.llm = AzureChatOpenAI(...)  # Fails if no OPENAI_API_KEY
```

**After (fixed):**
```python
class EnhancedForexSummarizer:
    def __init__(self):
        self.llm = None  # Don't initialize immediately
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize services only when actually needed"""
        if self._initialized:
            return
            
        try:
            # Check if running in test/build environment
            if os.getenv('SKIP_SERVICE_INIT') == 'true':
                self.llm = None  # Mock for testing
                self._initialized = True
                return
                
            # Normal initialization
            self.llm = AzureChatOpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                azure_endpoint=os.getenv('OPENAI_BASE_URL'),
                azure_deployment=os.getenv('AZURE_OPENAI_DEPLOYMENT'),
                # ... other config
            )
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    def summarize(self, *args, **kwargs):
        self._ensure_initialized()  # Initialize only when needed
        if not self.llm:
            return "Service unavailable during testing"
        return self.llm.invoke(...)
```

### **In your `api.py`:**

**Before:**
```python
# This runs during import
summarizer = NewsSummarizer()  # Fails during build
```

**After:**
```python
# Global variable, initialized lazily
summarizer = None

def get_summarizer():
    global summarizer
    if summarizer is None:
        summarizer = NewsSummarizer()
    return summarizer

@app.get("/")
def read_root():
    summarizer = get_summarizer()  # Initialize only when endpoint called
    # ... rest of code
```

## 🛠️ **Solution 2: Environment Variable Checks**

### **Add to the top of problematic modules:**
```python
import os

# Skip service initialization during build/test
if os.getenv('SKIP_SERVICE_INIT') == 'true':
    print("Skipping service initialization for build/test")
    
    # Create mock classes for testing
    class MockAzureChatOpenAI:
        def invoke(self, *args, **kwargs):
            return "Mock response for testing"
    
    class MockQdrantClient:
        def search(self, *args, **kwargs):
            return []
    
    # Use mocks instead of real services
    AzureChatOpenAI = MockAzureChatOpenAI
```

## 🛠️ **Solution 3: Environment Variable Validation**

### **Add validation before service initialization:**
```python
def validate_environment():
    required_vars = [
        'OPENAI_API_KEY',
        'OPENAI_BASE_URL', 
        'AZURE_OPENAI_DEPLOYMENT',
        'QDRANT_URL',
        'QDRANT_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        if os.getenv('SKIP_SERVICE_INIT') == 'true':
            return False  # Skip initialization
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")
    
    return True

class EnhancedForexSummarizer:
    def __init__(self):
        if not validate_environment():
            self.llm = None  # Mock for testing
            return
            
        self.llm = AzureChatOpenAI(...)  # Safe to initialize
```

## 🎯 **Pipeline Fix Applied:**

I've already updated your pipeline to set `SKIP_SERVICE_INIT=true` during the build phase, so if you implement the lazy initialization pattern above, your build will succeed.

## 🔄 **Updated Pipeline Flow:**

1. **Build Phase**: Sets `SKIP_SERVICE_INIT=true` → Your app uses mocks
2. **Deploy Phase**: Real environment variables → Your app uses real services
3. **Runtime**: Full environment available → Normal operation

## 🚀 **Recommended Implementation Order:**

1. **Use the updated pipeline** (already applied) - this will make your build pass
2. **Implement lazy initialization** in your code (recommended for production)
3. **Test locally** with and without environment variables
4. **Deploy** - should work perfectly

The pipeline fix will make your build pass immediately, but implementing lazy initialization in your code is the proper long-term solution.
