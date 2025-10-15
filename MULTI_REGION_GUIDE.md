# Multi-Region Deployment Guide - NewsRAG API

## Current Status ✅
- Traffic Manager: `newsraag-global-prod.trafficmanager.net`
- US Endpoint: `newsraag-us-prod.azurewebsites.net` (Online, HTTPS working)
- EU Endpoint: `newsraag-eu-prod.azurewebsites.net` (Online, HTTPS working)
- Geographic Routing: US/CA/MX → US endpoint, Rest of World → EU endpoint

## The SSL/HTTPS Issue 🔐

**Traffic Manager does NOT support SSL/TLS termination**. This is by design.
- Traffic Manager operates at the DNS level (not HTTP level)
- It routes DNS queries, not actual HTTPS traffic
- You cannot access `https://newsraag-global-prod.trafficmanager.net` directly

## Production-Ready Solutions

### Option 1: Azure Front Door (⭐ RECOMMENDED)

**Why Front Door?**
- ✅ Native SSL/TLS support with managed certificates
- ✅ Global CDN for better performance
- ✅ Intelligent routing based on latency, health, and geography
- ✅ WAF (Web Application Firewall) protection
- ✅ No custom domain required
- ✅ Better than Traffic Manager for modern applications

**Cost:** ~$35-75/month + bandwidth

**Setup:**
```bash
# Run the provided script
./setup_front_door.ps1
```

**What you get:**
- HTTPS endpoint: `https://newsraag-global-<hash>.z01.azurefd.net`
- Automatic SSL certificate
- Health monitoring on both regions
- Latency-based routing

---

### Option 2: Custom Domain + Traffic Manager

**Requirements:**
1. Own a domain (e.g., `api.newsraag.com`)
2. Configure SSL certificate on Azure App Service
3. Use Traffic Manager for DNS routing

**Setup Steps:**

1. **Buy a domain** (e.g., from GoDaddy, Namecheap, or Azure)
2. **Add custom domain to both App Services:**
   ```bash
   # Add custom domain to US App Service
   az webapp config hostname add \
       --webapp-name newsraag-us-prod \
       --resource-group vibetrader-rag-rg \
       --hostname api.newsraag.com
   
   # Add custom domain to EU App Service
   az webapp config hostname add \
       --webapp-name newsraag-eu-prod \
       --resource-group vibetrader-rag-rg \
       --hostname api.newsraag.com
   ```

3. **Configure SSL certificates** (App Service provides free managed certificates)
   ```bash
   az webapp config ssl bind \
       --name newsraag-us-prod \
       --resource-group vibetrader-rag-rg \
       --certificate-thumbprint auto \
       --ssl-type SNI
   ```

4. **Update Traffic Manager** to use custom domain
5. **Update DNS** at your domain registrar to point to Traffic Manager

**Pros:**
- ✅ Your own branded domain
- ✅ Full control

**Cons:**
- ❌ Requires domain purchase (~$10-15/year)
- ❌ More complex setup
- ❌ Manual SSL certificate management

---

### Option 3: Direct App Service URLs (Current Setup)

**Use this for testing or development:**
- US: `https://newsraag-us-prod.azurewebsites.net`
- EU: `https://newsraag-eu-prod.azurewebsites.net`

**Pros:**
- ✅ Works immediately
- ✅ Free
- ✅ HTTPS built-in

**Cons:**
- ❌ No automatic routing
- ❌ Clients must choose endpoint manually
- ❌ Not production-ready

---

## How Traffic Manager Actually Works

Traffic Manager is a **DNS-based** load balancer:

1. Client queries: `newsraag-global-prod.trafficmanager.net`
2. Traffic Manager returns IP of closest healthy endpoint
3. Client connects directly to that App Service

**This means:**
- Traffic Manager doesn't handle HTTPS traffic
- Clients connect directly to App Services
- SSL certificates must be on App Services, not Traffic Manager

---

## Recommendation for Your Use Case 🎯

**For Production: Use Azure Front Door**
- Run `./setup_front_door.ps1` 
- Get instant HTTPS endpoint
- Better performance than Traffic Manager
- No domain needed

**For Development/Testing:**
- Use direct App Service URLs
- Keep Traffic Manager for health monitoring

---

## Testing Your Current Setup

Since you have Traffic Manager configured, here's how to test it properly:

### Test Individual Endpoints (HTTPS works):
```bash
# US Endpoint
curl https://newsraag-us-prod.azurewebsites.net/health

# EU Endpoint  
curl https://newsraag-eu-prod.azurewebsites.net/health
```

### Test Traffic Manager (DNS resolution):
```bash
# This will show which endpoint Traffic Manager resolves to
nslookup newsraag-global-prod.trafficmanager.net
```

### Simulate Geographic Routing:
```bash
# From US location - should get US endpoint
# From EU location - should get EU endpoint
# Test using VPN or proxy from different regions
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENT REQUEST                        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   OPTION 1: Azure Front Door   │  ⭐ RECOMMENDED
        │   (SSL/TLS Termination)        │
        │   https://newsraag-xyz.fd.net  │
        └────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────┐                  ┌──────────────┐
│  US Region   │                  │  EU Region   │
│ newsraag-us  │                  │ newsraag-eu  │
│   (HTTPS)    │                  │   (HTTPS)    │
└──────────────┘                  └──────────────┘


        ┌────────────────────────────────┐
        │ OPTION 2: Traffic Manager      │  (DNS only)
        │ newsraag-global-prod.tm.net    │  
        └────────────────────────────────┘
                         │
            (DNS Resolution Only)
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────┐                  ┌──────────────┐
│  US Region   │                  │  EU Region   │
│ Direct HTTPS │                  │ Direct HTTPS │
└──────────────┘                  └──────────────┘
```

---

## Next Steps

1. **For immediate production use:**
   ```bash
   cd C:\Users\harip\NewsRag-api
   ./setup_front_door.ps1
   ```

2. **For testing/development:**
   - Use direct URLs: `https://newsraag-us-prod.azurewebsites.net`
   - Traffic Manager is working correctly for health checks

3. **Future enhancement:**
   - Add custom domain
   - Configure WAF rules
   - Set up Application Insights for monitoring

---

## Cost Comparison

| Solution | Monthly Cost | SSL/HTTPS | Performance | Setup Time |
|----------|-------------|-----------|-------------|------------|
| Front Door | $35-75 | ✅ Built-in | ⭐⭐⭐⭐⭐ | 10 mins |
| Traffic Manager + Domain | $10-15 | ⚠️ Manual | ⭐⭐⭐ | 30 mins |
| Direct URLs | $0 | ✅ Built-in | ⭐⭐⭐ | 0 mins |

---

## Troubleshooting

### "404 Web Site not found" on Traffic Manager URL
**Cause:** Traffic Manager doesn't support direct HTTPS access
**Solution:** Use Front Door or direct App Service URLs

### SSL Certificate Errors
**Cause:** Traffic Manager domain doesn't have SSL cert
**Solution:** Use Front Door (provides managed certs automatically)

### Endpoints showing as "Degraded"
**Check:**
```bash
az network traffic-manager endpoint list \
    --profile-name tm-newsraag-prod \
    --resource-group vibetrader-rag-rg \
    --query "[].{Name:name,Status:endpointMonitorStatus}"
```

---

## Contact & Support

If you need help with setup, check:
- Azure documentation: https://docs.microsoft.com/azure/frontdoor
- This project's README: ./README.md
