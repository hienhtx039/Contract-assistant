# GreenNode Contract Guardian - AgentBase Deployment Guide

## BƯỚC 2: Deploy as AgentBase Custom Agent Runtime

### Prerequisites
- ✅ Docker image pushed: `vcr.vngcloud.vn/111480-abp111955/my-contract:v1.0`
- ✅ IAM Service Account with AgentBase permissions
- IAM credentials: `GREENNODE_CLIENT_ID` + `GREENNODE_CLIENT_SECRET`

### 2.1: Setup IAM Credentials (Local Development)

```bash
# 1. Create Service Account at https://iam.console.vngcloud.vn/service-accounts
# 2. Attach policies: AgentBaseFullAccess, vcrFullAccess, AiPlatformFullAccess
# 3. Copy Client ID + Client Secret, then export:

export GREENNODE_CLIENT_ID="your-client-id"
export GREENNODE_CLIENT_SECRET="your-client-secret"
export AI_PLATFORM_API_KEY="your-api-key-for-llm-calls"
```

### 2.2: Deploy to AgentBase Runtime

**Option A: Quick Deploy (Automated Script)**

```bash
chmod +x scripts/deploy-to-agentbase.sh
./scripts/deploy-to-agentbase.sh
```

This script will:
- Verify IAM credentials
- Obtain bearer token
- Create Custom Agent runtime with auto-scaling (1-3 replicas)
- Provision PUBLIC endpoint
- Return runtime ID + endpoint URL

**Option B: Manual Deploy (Step-by-Step)**

```bash
# 1. Get token
TOKEN=$(curl -s -X POST https://iam.api.vngcloud.vn/identity/v3.0/auth/tokens \
  -H "Content-Type: application/json" \
  -d "{\"auth\": {\"identity\": {\"methods\": [\"password\"], \"password\": {\"user\": {\"id\": \"$GREENNODE_CLIENT_ID\", \"password\": \"$GREENNODE_CLIENT_SECRET\"}}}}}" \
  | jq -r '.token.id')

echo "Token: $TOKEN"

# 2. Create runtime
curl -X POST https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "contract-guardian",
    "description": "GreenNode Contract Guardian - AI Agent for contract analysis",
    "image": "vcr.vngcloud.vn/111480-abp111955/my-contract:v1.0",
    "flavor": "s1-general-1x2",
    "environmentVariables": {
      "AI_PLATFORM_API_KEY": "'$AI_PLATFORM_API_KEY'",
      "LLM_MODEL": "qwen2.5-72b-instruct",
      "AGENTBASE_MEMORY_ID": "contract-memory"
    },
    "autoscaling": {
      "minReplicas": 1,
      "maxReplicas": 3,
      "targetCpuUtilizationPercentage": 70
    }
  }' | jq .

# 3. List runtimes to get endpoint
curl -s -X GET https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes \
  -H "Authorization: Bearer $TOKEN" | jq '.items[] | {name, id, status, endpoints}'
```

### 2.3: Auto-Scaling & Versioning

Once deployed, the runtime automatically:
- **Scales out** from 1→3 replicas when CPU > 70%
- **Scales in** when load decreases
- **Supports versioning**: Deploy new version → canary test → promote to DEFAULT
- **Zero-downtime deploys**: Gradually shift traffic between versions
- **Rollback**: Switch back to previous version instantly

### 2.4: Monitor Runtime

```bash
# View logs
curl -s -X GET "https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes/{RUNTIME_ID}/logs?limit=50" \
  -H "Authorization: Bearer $TOKEN" | jq '.logs[]'

# View metrics (CPU, Memory, Requests)
curl -s -X GET "https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes/{RUNTIME_ID}/metrics?period=1h" \
  -H "Authorization: Bearer $TOKEN" | jq '.metrics'

# Or use Console: https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime
```

---

## BƯỚC 3 (OPTIONAL): Migrate API Keys via agentbase-identity

### 3.1: Register Agent Identity

```bash
# 1. Create agent identity on the platform
TOKEN=$(bash scripts/get_token.sh)  # From agentbase skills

curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "contract-guardian-agent",
    "description": "GreenNode Contract Guardian - AI Agent for contract analysis"
  }' | jq .

# Response: { "name": "contract-guardian-agent", "createdAt": "...", ... }
```

### 3.2: Store API Key via Identity Service

```bash
# Store the GreenNode AI Platform API key securely
TOKEN=$(bash scripts/get_token.sh)

curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "greennode-aip",
    "description": "GreenNode AI Platform for LLM calls",
    "baseUrl": "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
  }' | jq .

# Then store the API key for this agent identity
curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/greennode-aip/agent-identities/contract-guardian-agent/api-key \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "'$AI_PLATFORM_API_KEY'"
  }' | jq .
```

### 3.3: Runtime Auto-Injection

Once identity is registered, AgentBase Runtime **automatically injects** into the container:

```bash
GREENNODE_CLIENT_ID=<service-account-id>
GREENNODE_CLIENT_SECRET=<service-account-secret>
GREENNODE_AGENT_IDENTITY=contract-guardian-agent
GREENNODE_ENDPOINT_URL=https://agentbase.vngcloud.vn/runtimes/contract-guardian/DEFAULT
```

The SDK automatically uses these to:
- Authenticate with platform APIs
- Retrieve stored API keys (AI_PLATFORM_API_KEY)
- Access memory stores
- Manage conversation history

**No manual credential configuration needed in agent code!**

### 3.4: Update app.py to Use Identity

Replace hardcoded API keys with automatic retrieval:

```python
# Before (hardcoded in .env):
api_key = os.getenv("AI_PLATFORM_API_KEY")

# After (auto-retrieved from identity):
from greennode_agentbase.client import SecretClient

secret_client = SecretClient()
api_key = secret_client.get_api_key("greennode-aip")  # Stored via identity service
```

---

## Full Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   GreenNode Contract Guardian                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐          ┌──────────────┐                    │
│  │  Streamlit   │          │  Agent Tools │                    │
│  │   UI (app)   │   ←→     │ (agent/main) │                    │
│  └──────────────┘          └──────────────┘                    │
│         ↓                          ↓                             │
│  ┌──────────────┐          ┌──────────────────┐                │
│  │ Memory Store │          │  LLM Calls       │                │
│  │(agent/memory)│          │  (via OpenAI API)│                │
│  └──────────────┘          └──────────────────┘                │
│         ↓                          ↓                             │
│  ┌─────────────────────────────────────────────┐                │
│  │   AgentBase Runtime (Custom Agent)          │                │
│  │  • Auto-scaling: 1-3 replicas               │                │
│  │  • Zero-downtime deploys                    │                │
│  │  • Versioning + rollback                    │                │
│  │  • Auto-injected credentials                │                │
│  └─────────────────────────────────────────────┘                │
│                      ↓                                           │
│  ┌─────────────────────────────────────────────┐                │
│  │   AgentBase Services (Managed)              │                │
│  │  • Identity Service (secrets)               │                │
│  │  • Memory Service (conversation history)    │                │
│  │  • Monitoring (logs, metrics, traces)       │                │
│  │  • Container Registry (image storage)       │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Checklist

- [ ] **2.1**: IAM credentials exported
- [ ] **2.2**: Runtime deployed (script or manual)
- [ ] **2.3**: Auto-scaling verified in console
- [ ] **2.4**: Logs visible in console or via API
- [ ] **3.1**: Agent identity registered (optional)
- [ ] **3.2**: API keys stored in identity service (optional)
- [ ] **3.3**: Memory integration tested
- [ ] **3.4**: Agent auto-injects credentials (optional)

---

## Next Steps

1. **Test the Endpoint**:
   ```bash
   curl -X POST {ENDPOINT}/invoke \
     -H "Content-Type: application/json" \
     -d '{"contract_text": "...", "question": "Điều khoản nào rủi ro nhất?"}'
   ```

2. **Setup Memory Store**: Create memory store on platform for long-term semantic extraction
3. **Monitor Dashboard**: Check console for real-time metrics, logs, distributed traces
4. **Deploy LangGraph (Advanced)**: Convert agent to LangGraph + state machines for complex workflows

---

## Useful Links

- **Console**: https://aiplatform.console.vngcloud.vn/agent-runtime
- **API Docs**: https://agentbase.api.vngcloud.vn/docs
- **Python SDK**: https://github.com/vngcloud/greennode-agentbase
- **Skills**: `.claude/skills/agentbase/` (platform reference, deployment, identity, memory, monitoring)
