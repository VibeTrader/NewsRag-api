# NewsRagnarok API

## Overview

The NewsRagnarok API is a high-performance FastAPI service designed for news article search and comprehensive forex market summarization. It leverages a clean, hexagonal architecture and an advanced technology stack to provide fast, accurate, and actionable financial insights.

-----

## 🌟 Features

  * **Vector Search**: Utilizes Qdrant vector database for high-accuracy semantic search, enabling users to find relevant news articles based on the meaning of a query, not just keywords.
  * **AI Summarization**: Integrates with Azure OpenAI to generate detailed and nuanced forex market analysis from multiple news sources, providing insights beyond simple article summaries.
  * **High-Performance Caching**: Employs an efficient in-memory caching system with a time-to-live (TTL) and LRU (Least Recently Used) eviction policy for faster responses to repeated queries.
  * **Clean Architecture**: The codebase is structured for clarity and maintainability, focusing on the separation of concerns to ensure a robust and scalable application.

-----

## 📊 Summarization Capabilities

The `/summarize` endpoint is the core of the API, providing an advanced forex market analysis with the following structured components:

  * **Executive Summary**: A concise, high-level overview of current market conditions with key sentiment indicators.
  * **Currency Pair Rankings**: A detailed analysis of major forex pairs (e.g., EUR/USD, USD/JPY), including a rank, fundamental and sentiment outlook percentages, and a detailed rationale.
  * **Risk Assessment**: An analysis of potential market risks, including primary risks, correlation risks, and volatility potential.
  * **Trade Management Guidelines**: Actionable, practical recommendations for traders based on the current market dynamics.

-----

## 📁 Project Structure

```
/NewsRagnarok-API
├── api.py (FastAPI application)
├── requirements.txt (API dependencies)
├── startup.txt (App Service config)
├── clients/
│   └── qdrant_client.py (Vector database client)
├── utils/
│   └── summarization/ (Summarization utilities)
│       ├── __init__.py
│       ├── news_summarizer.py (Main summarization logic)
│       └── cache_manager.py (In-memory caching)
└── .env (environment variables)
```

-----

## 🔧 API Endpoints

  * `GET /health`: Checks the health of the API and its connection to the Qdrant database.
  * `POST /search`: Searches for news articles based on a given query.
  * `GET /documents/stats`: Retrieves statistics for the Qdrant news collection.
  * `POST /summarize`: Generates a comprehensive forex market analysis summary.
  * `GET /summarize/stats`: Provides statistics on the in-memory cache for summaries.

-----

## 🚀 Usage Examples

### Search for Articles

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "forex news",
    "limit": 5
  }'
```

### Generate Market Summary (Text Format)

```bash

```

### Generate Market Summary (JSON Format)

```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "forex news",
    "limit": 10,
    "format": "json"
  }'
```

-----

## 💡 Technology Stack

  * **FastAPI**: High-performance, low-code API framework for Python.
  * **Qdrant**: A high-speed vector database for efficient semantic search.
  * **Azure OpenAI**: Provides powerful AI models for complex summarization and analysis.
  * **In-memory Cache**: An efficient caching solution with TTL and LRU eviction for optimized performance.

-----

## 🚀 Deployment

```bash
# Start the API server
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

-----

## 🔧 Configuration

The following environment variables are required for the API to function correctly:

  * `QDRANT_URL`: URL of the Qdrant database.
  * `QDRANT_API_KEY`: API key for Qdrant.
  * `QDRANT_COLLECTION_NAME`: The collection name for news articles.
  * `OPENAI_API_KEY`: Azure OpenAI API key.
  * `AZURE_OPENAI_API_VERSION`: Azure OpenAI API version.
  * `OPENAI_BASE_URL`: The base URL for the Azure OpenAI service.
  * `AZURE_OPENAI_DEPLOYMENT`: The name of the specific Azure OpenAI deployment.

Optional settings:

  * `SUMMARY_CACHE_SIZE`: Maximum number of cached summaries (default: 100).
  * `SUMMARY_CACHE_TTL`: Cache duration in seconds (default: 1800).

-----

## 🔍 How Summarization Works

The summarization process is a multi-step workflow:

1.  **Search**: The API uses a user-provided `query` to perform a semantic search in the Qdrant vector database to find the most relevant news articles.
2.  **Preparation**: Key information from the retrieved articles is extracted and formatted into a structured input for the AI model.
3.  **Summarization**: This formatted data is sent to a pre-configured Azure OpenAI model with specific instructions to generate a structured market analysis.
4.  **Parsing**: The AI-generated analysis is then parsed and structured into either a human-readable text format or a machine-readable JSON object.
5.  **Caching**: The final result is stored in the in-memory cache to quickly serve identical future requests, reducing latency and API costs.

-----

## 📝 Recent Updates

  * **Enhanced Forex Summarization**: Implemented LangChain-based summarization for improved currency pair detection and analysis, resulting in more accurate and detailed market insights.
  * **Improved Currency Pair Ranking**: The system now analyzes currency pair mentions across articles, prioritizing pairs by frequency, sentiment strength, and recency of news.
  * **Improved Reliability**: Eliminated fallback methods to ensure consistent, high-quality analysis using only the primary AI model.
  * **Enhanced Azure OpenAI Integration**: Updated the Azure OpenAI client for improved compatibility and performance with the latest libraries.
  * **Streamlined Codebase**: Simplified the architecture by removing unused utilities and redundant code, making the application leaner and easier to maintain.
  * **Optimized Caching**: Fine-tuned the caching system with a 30-minute TTL, which is ideal for financial data that needs to be relatively current.

-----

## 🔍 Troubleshooting

If you encounter issues while using the API, consider the following steps:

1.  **Check Environment Variables**: Ensure all required environment variables are set correctly.
2.  **Service Accessibility**: Verify that both the Qdrant and Azure OpenAI services are running and accessible.
3.  **Quota and Permissions**: Confirm that your Azure OpenAI account has sufficient quota and the necessary permissions for the API to function.
4.  **Review Logs**: Check the API logs for detailed error messages that can provide clues about the root cause of the issue.

For more detailed information on the summarization feature, refer to the original `README-summarization.md` documentation.
## Multi-Environment, Multi-Region Deployment Strategy

### Overview

This project supports both **development** and **production** environments, each with its own region set and isolated infrastructure state. All deployments are managed via GitHub Actions and Terraform.

---

### Environments & Regions

- **Development (`dev` branch):**
  - Deploys to 2 regions: US (East US) and Europe (North Europe)
  - Used for validation and testing before production rollout

- **Production (`main` branch):**
  - Deploys to 3+ regions: US (East US), Europe (North Europe), India (Central India)
  - Can be extended to more regions as needed

---

### Branching & Deployment Flow

1. **Push to `dev` branch:**
   - Triggers infrastructure and app deployment to the `dev` environment (2 regions).
   - Uses a separate Terraform workspace and backend state (`newsraag-dev.tfstate`).

2. **Validation in `dev`:**
   - All changes are tested in the development environment.

3. **Pull Request to `main`:**
   - After successful validation, a PR is raised to merge `dev` into `main`.

4. **Merge to `main`:**
   - Triggers infrastructure and app deployment to the `prod` environment (all regions).
   - Uses the production Terraform workspace and backend state (`newsraag-prod.tfstate`).

---

### How It Works

- **Region Selection:**  
  The set of regions is determined by the `environment` variable (`dev` or `prod`).  
  - In `dev`, only US and Europe are deployed.
  - In `prod`, all defined regions are deployed.

- **Terraform Workspaces:**  
  Each environment uses a separate workspace and backend state file for isolation.

- **GitHub Actions:**  
  - Workflow YAMLs dynamically set the environment and region matrix based on the branch.
  - App Service names and other resources are suffixed with `-dev` or `-prod` as appropriate.

---

### Adding a New Region

1. Add the region to the `all_regions` map in [`terraform/main.tf`](terraform/main.tf).
2. It will be included in production automatically.  
   To include in development, add it to the `regions` selection logic for `dev`.

---

### Summary Table

| Branch   | Environment | Regions Deployed         | State File             |
|----------|-------------|-------------------------|------------------------|
| dev      | dev         | US, Europe              | newsraag-dev.tfstate   |
| main     | prod        | US, Europe, India, ...  | newsraag-prod.tfstate  |

---

### Security

- All secrets (Azure credentials, API keys) are managed via GitHub Secrets.
- App settings and sensitive values are injected securely in the deployment workflows.

---

### Notes

- All infrastructure and app changes should be validated in `dev` before merging to `main`.
- The deployment process is fully automated and supports safe, staged rollouts.
