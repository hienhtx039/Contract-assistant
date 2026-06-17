# GreenNode Contract Guardian - Quick Start Guide

> AI-powered contract analysis agent with semantic memory, deployed on GreenNode AgentBase.

## What's New

✅ **Phase 1 - Local Development (Complete)**
- ✓ Streamlit UI dashboard (app.py)
- ✓ Contract analysis tools (agent/main.py)
- ✓ Semantic memory tracking (agent/memory.py)
- ✓ Session conversation history

🚀 **Phase 2 - Cloud Deployment (Ready)**
- Deploy to AgentBase Runtime (auto-scaling 1-3 replicas)
- Zero-downtime versioning
- Integrated monitoring

🔐 **Phase 3 - Enterprise Security (Optional)**
- API key management via agentbase-identity
- Auto-injected credentials in container

---

## Quick Start (5 minutes)

### 1. Local Testing (Streamlit)

```bash
# Install dependencies
pip install -e ".[dev]" streamlit

# Set API key
export AI_PLATFORM_API_KEY="your-key"

# Run dashboard
streamlit run app.py

# Open: http://localhost:8501
```

**Features:**
- Upload .docx / .pdf / .txt contracts
- Analyze legal, financial, compliance risks
- Chat with agent about contract details
- Memory auto-extracts patterns (shown in sidebar)

---

### 2. Build & Push Docker Image

```bash
# Make scripts executable
chmod +x scripts/build-and-push.sh scripts/deploy-to-agentbase.sh

# Build, tag, push to VCR (with v1.1 tag)
./scripts/build-and-push.sh v1.1

# Or manually:
docker build -f docker/Dockerfile.contract-guardian -t my-contract:latest .
docker tag my-contract:latest vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1
docker push vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1
```

---

### 3. Deploy to AgentBase Runtime

```bash
# Setup credentials
export GREENNODE_CLIENT_ID="<your-client-id>"
export GREENNODE_CLIENT_SECRET="<your-client-secret>"
export AI_PLATFORM_API_KEY="<your-api-key>"

# Deploy with auto-scaling
./scripts/deploy-to-agentbase.sh

# Or check DEPLOY_AGENTBASE.md for manual/advanced steps
```

**What happens:**
- ✓ Runtime created with 1-3 auto-scaling replicas
- ✓ Endpoint provisioned (check console)
- ✓ Environment variables injected
- ✓ Monitor logs + metrics in console

---

### 4. Test Endpoint

```bash
# Get endpoint URL from console:
# https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime

curl -X POST https://<endpoint>/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "contract_text": "Điều 1: Giá dịch vụ là 100 triệu...",
    "question": "Điều khoản nào rủi ro nhất?"
  }'
```

---

## Architecture

```
┌─────────────┐
│  Streamlit  │  (Local dev)
│  Dashboard  │
└──────┬──────┘
       │
    ┌──┴──────────────────────────┐
    │   Contract Guardian Agent    │
    │  ┌──────────────────────┐    │
    │  │ Memory Module        │    │
    │  │ • Sessions           │    │
    │  │ • Pattern Extraction │    │
    │  └──────────────────────┘    │
    │  ┌──────────────────────┐    │
    │  │ Analysis Tools       │    │
    │  │ • extract_risks()    │    │
    │  │ • check_compliance() │    │
    │  │ • generate_email()   │    │
    │  └──────────────────────┘    │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │  AgentBase Runtime (Cloud)   │
    │  • Auto-scaling              │
    │  • Zero-downtime deploys     │
    │  • Versioning + Rollback     │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │  Managed Services            │
    │  • Memory Service            │
    │  • Identity Service          │
    │  • Monitoring                │
    │  • Container Registry        │
    └──────────────────────────────┘
```

---

## File Structure

```
agent/
├── main.py                    # Core agent + tools
├── memory.py                  # Session memory + pattern extraction
└── __init__.py

app.py                         # Streamlit UI

scripts/
├── build-and-push.sh         # Docker build → tag → push
└── deploy-to-agentbase.sh    # Deploy to AgentBase runtime

docker/
├── Dockerfile.contract-guardian    # Streamlit app image
├── Dockerfile.cpu             # Whisper server (unchanged)
└── Dockerfile.openvino       # Whisper server (unchanged)

.env.agentbase                # Template for credentials
DEPLOY_AGENTBASE.md           # Full deployment guide
```

---

## Key Features

### Memory Integration
- **Session Tracking**: Each user gets a unique session ID
- **Conversation History**: All turns stored (user input → agent response)
- **Pattern Extraction**: Auto-detects common risks, compliance topics, negotiation points
- **Sidebar Display**: Shows extracted patterns in real-time

### Analysis Tools (3 Skills)
1. **extract_contract_risks()** - Trích xuất rủi ro pháp lý + tài chính
2. **check_compliance_mock()** - Quét tuân thủ Điều 10/11 (với mock data)
3. **generate_negotiation_email()** - Sinh email đàm phán chuyên nghiệp

### Agent System Prompt
```
"Bạn là Chuyên gia Thẩm định Hợp đồng kỳ cựu. 
Phân tích theo 3 góc độ: Pháp lý, Tài chính, Thẩm định đối tác."
```

### UI Tabs
1. **Tóm tắt** - Summary + yellow warnings
2. **Pháp lý** - Legal risks table
3. **Tài chính** - Metrics + cashflow forecast
4. **Thẩm định** - Compliance check results

---

## Next Steps

### Short Term (This Week)
- [ ] Test Streamlit locally
- [ ] Setup IAM credentials
- [ ] Deploy to AgentBase Runtime
- [ ] Monitor logs + metrics in console

### Medium Term (Next Sprint)
- [ ] Create AgentBase memory store for long-term semantic extraction
- [ ] Setup agentbase-identity for secure credential rotation
- [ ] Add LangGraph for complex workflows
- [ ] Integrate with GreenNode Gateway for API authentication

### Long Term (Future)
- [ ] Multi-tenant support
- [ ] Custom knowledge base (company precedents)
- [ ] Integration with document management systems
- [ ] Audit trail + compliance reporting

---

## Documentation

- **Full Deployment Guide**: [DEPLOY_AGENTBASE.md](DEPLOY_AGENTBASE.md)
- **Agent Code**: [agent/main.py](agent/main.py)
- **Memory Module**: [agent/memory.py](agent/memory.py)
- **UI Code**: [app.py](app.py)
- **Docker Config**: [docker/Dockerfile.contract-guardian](docker/Dockerfile.contract-guardian)
- **Credentials Template**: [.env.agentbase](.env.agentbase)

---

## Support

For questions about:
- **AgentBase Platform**: Check `.claude/skills/agentbase/` (reference + scripts)
- **Deployment Issues**: See [DEPLOY_AGENTBASE.md](DEPLOY_AGENTBASE.md)
- **Code Issues**: Review [agent/main.py](agent/main.py), [app.py](app.py), [agent/memory.py](agent/memory.py)

---

**Last Updated**: 2026-06-17  
**Version**: 1.1 (with memory integration)
