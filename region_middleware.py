# Add this to your api.py to identify which region is serving requests

@app.middleware("http")
async def add_region_header(request: Request, call_next):
    response = await call_next(request)
    # Add region identifier based on environment variable
    region = os.getenv('DEPLOYMENT_REGION', 'unknown')
    response.headers["X-Served-By-Region"] = region
    return response