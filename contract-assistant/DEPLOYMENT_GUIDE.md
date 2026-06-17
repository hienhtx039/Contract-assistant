# 🚀 Hướng Dẫn Triển Khai GreenNode Contract Guardian

## 📊 Tình Trạng Hiện Tại

- ✅ Docker Image v1.1 đã push lên VCR
  - URI: `vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1`
  - Size: ~856MB
  - Base: Python 3.10-bookworm
  - Includes: Streamlit, OpenAI SDK, pandas, PyPDF2

- ✅ Credentials đã cấu hình
  - Client ID: `5c103cbf-d92e-4a7c-acf8-b32d0d45f513`
  - API Key: `vn-J-_-...` (đã set trong .env.agentbase)

---

## 🎯 Các Bước Triển Khai

### **Cách 1: Manual Console (Recommended) ⭐**

1. **Truy cập AI Platform Console**
   ```
   https://aiplatform.console.vngcloud.vn/agent-runtime
   ```

2. **Tạo Custom Agent Runtime Mới**
   - Click "Create New Custom Agent Runtime"
   - Fill form:

     | Field | Value |
     |-------|-------|
     | **Name** | contract-guardian |
     | **Description** | GreenNode Contract Guardian - AI Agent for contract analysis |
     | **Image** | vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1 |
     | **Flavor** | s1-general-1x2 (1 CPU, 2GB RAM) |
     | **Port** | 8501 |

3. **Cấu Hình Environment Variables**
   - Click "Add Environment Variable" x3:

     ```
     AI_PLATFORM_API_KEY = vn-J-_-6igVvSyryN-0RXf22Kzi1GL_R85ea1ef3bdd5947b288e41f748729f897Md8vXEm67y-U9bXqjALcVnGCQk6oXrR
     
     LLM_MODEL = qwen2.5-72b-instruct
     
     AGENTBASE_MEMORY_ID = contract-memory
     ```

4. **Enable Auto-Scaling**
   - ✓ Enable: ON
   - Min Replicas: 1
   - Max Replicas: 3
   - CPU Threshold: 70%

5. **Deploy**
   - Click "Create Runtime"
   - Wait 2-5 minutes for provisioning
   - Get runtime endpoint (e.g., `https://contract-guardian-abc123.agentbase.api.vngcloud.vn`)

---

### **Cách 2: API Deployment (curl)**

Sau khi có token IAM:

```bash
# 1. Get IAM Token (nếu cần)
TOKEN=$(curl -s -X POST \
  https://iam.api.vngcloud.vn/identity/v3.0/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{"auth":{"identity":{"methods":["password"],"password":{"user":{"id":"5c103cbf-d92e-4a7c-acf8-b32d0d45f513","password":"b1ffcbcd-87cd-4e8f-8de6-b4bf3c337214"}}}}}' \
  | jq -r '.token.id')

# 2. Create Runtime
curl -X POST https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "contract-guardian",
    "description": "GreenNode Contract Guardian",
    "image": "vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1",
    "flavor": "s1-general-1x2",
    "environmentVariables": {
      "AI_PLATFORM_API_KEY": "vn-J-_-6igVvSyryN-0RXf22Kzi1GL_R85ea1ef3bdd5947b288e41f748729f897Md8vXEm67y-U9bXqjALcVnGCQk6oXrR",
      "LLM_MODEL": "qwen2.5-72b-instruct",
      "AGENTBASE_MEMORY_ID": "contract-memory"
    },
    "autoscaling": {
      "minReplicas": 1,
      "maxReplicas": 3,
      "targetCpuUtilizationPercentage": 70
    }
  }'
```

---

## 🔍 Sau Khi Deploy

### **1. Verify Deployment**
```bash
# Health check
curl https://contract-guardian-xxx.agentbase.api.vngcloud.vn/health

# Should return 200 OK
```

### **2. Test Streamlit App**
```
https://contract-guardian-xxx.agentbase.api.vngcloud.vn
```

### **3. Monitor**
- Console: https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime
- Logs: https://aiplatform.console.vngcloud.vn/logs
- Metrics: CPU, Memory, Request Count

### **4. Scale Management**
- Auto-scale triggers at 70% CPU
- Max 3 replicas (2 additional on demand)
- Min 1 replica (always running)

---

## 📋 Docker Image Details

```dockerfile
FROM python:3.10-bookworm

# ✓ System dependencies: libsndfile1, curl
# ✓ Python 3.10
# ✓ Non-root user: streamlit (uid 1000)
# ✓ Healthcheck: Port 8501
# ✓ Optimized layers for caching

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Image not found | Verify image in VCR: `docker pull vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1` |
| Env vars not set | Re-deploy with correct environment variables in console |
| High CPU usage | Scale up flavor or optimize LLM calls |
| Token timeout | Contact support - increase container resources |
| Endpoint 502 | App still starting - wait 30s and retry |

---

## 📞 Liên Hệ

- AI Platform Docs: https://docs.vngcloud.vn/agentbase
- Support: support@vngcloud.vn
- Status: https://status.vngcloud.vn/agentbase

---

## ✅ Checklist Pre-Deploy

- [x] Docker image built and tested locally
- [x] Image pushed to VCR (v1.1)
- [x] .env.agentbase configured
- [x] Credentials verified
- [x] App tested on localhost:8501
- [x] Non-root user added to Dockerfile
- [x] Healthcheck enabled

**Status: Ready for Production Deploy ✅**

---

**Created:** 2026-06-17  
**Last Updated:** 2026-06-17  
**Version:** 1.1
