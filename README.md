# NewsRagnarok API

FastAPI service for news article search using Qdrant vector database.

## 🚀 Quick Deploy

```bash
chmod +x deploy-api.sh
./deploy-api.sh
```

## 📁 Structure

```
/NewsRagnarok-API
├── api.py (FastAPI application)
├── requirements.txt (API dependencies)
├── startup.txt (App Service config)
├── deploy-api.sh (deployment script)
├── clients/ (Qdrant, Redis clients)
├── utils/ (Azure, time utilities)
├── models/ (data models)
└── .env (environment variables)
```

## 🔧 API Endpoints

- `GET /health` - Health check
- `POST /search` - Search articles
- `GET /stats` - Collection statistics
- `GET /count` - Document count

## 💡 Benefits

- ✅ Clean API-only deployment
- ✅ Lightweight (~200MB total)
- ✅ Fast deployments
- ✅ Easy scaling
- ✅ Built-in monitoring

## 🔗 Dependencies

- Qdrant (vector database)
- Redis (caching)
- Azure Blob Storage (archival)


