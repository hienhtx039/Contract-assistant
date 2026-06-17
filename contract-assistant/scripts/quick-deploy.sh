#!/bin/bash
# Quick Deploy to AgentBase Runtime (Simplified)

set -e

echo "🚀 GreenNode Contract Guardian - Quick Deploy"
echo "=============================================="
echo ""

# Configuration
RUNTIME_NAME="contract-guardian"
IMAGE_URI="vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1"
FLAVOR="s1-general-1x2"

echo "📋 Deployment Configuration:"
echo "   Runtime Name:  $RUNTIME_NAME"
echo "   Image:         $IMAGE_URI"
echo "   Flavor:        $FLAVOR"
echo "   Replicas:      1-3 (auto-scaling at 70% CPU)"
echo ""

# Check credentials
if [ -z "$GREENNODE_CLIENT_ID" ] || [ -z "$GREENNODE_CLIENT_SECRET" ]; then
    echo "❌ Missing credentials. Please set:"
    echo ""
    echo "export GREENNODE_CLIENT_ID='5c103cbf-d92e-4a7c-acf8-b32d0d45f513'"
    echo "export GREENNODE_CLIENT_SECRET='b1ffcbcd-87cd-4e8f-8de6-b4bf3c337214'"
    echo ""
    echo "Then run: bash scripts/quick-deploy.sh"
    exit 1
fi

echo "✓ Credentials found"
echo ""

# Option 1: Manual Console Deployment
echo "📖 OPTION 1: Manual Deployment via Console (Recommended)"
echo "=========================================================="
echo "1. Go to: https://aiplatform.console.vngcloud.vn/agent-runtime"
echo "2. Click 'Create New Custom Agent Runtime'"
echo "3. Fill in:"
echo "   - Name: contract-guardian"
echo "   - Description: GreenNode Contract Guardian - AI Agent for contract analysis"
echo "   - Image: $IMAGE_URI"
echo "   - Flavor: $FLAVOR"
echo "   - Environment Variables:"
echo "     * AI_PLATFORM_API_KEY: (from .env.agentbase)"
echo "     * LLM_MODEL: qwen2.5-72b-instruct"
echo "     * AGENTBASE_MEMORY_ID: contract-memory"
echo "4. Enable autoscaling: 1-3 replicas at 70% CPU trigger"
echo "5. Click Deploy ✓"
echo ""

# Option 2: API Deployment
echo "📡 OPTION 2: API Deployment (curl)"
echo "==================================="
echo "$ curl -X POST https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes \\"
echo "  -H 'Authorization: Bearer \$TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"name\": \"$RUNTIME_NAME\","
echo "    \"description\": \"GreenNode Contract Guardian - AI Agent for contract analysis\","
echo "    \"image\": \"$IMAGE_URI\","
echo "    \"flavor\": \"$FLAVOR\","
echo "    \"autoscaling\": {"
echo "      \"minReplicas\": 1,"
echo "      \"maxReplicas\": 3,"
echo "      \"targetCpuUtilizationPercentage\": 70"
echo "    }"
echo "  }'"
echo ""

# Summary
echo "✅ Deployment Ready!"
echo "===================="
echo ""
echo "After deployment, you can:"
echo "1. View runtime: https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime"
echo "2. Test endpoint: curl -X GET https://contract-guardian.agentbase.api.vngcloud.vn/health"
echo "3. Monitor logs: https://aiplatform.console.vngcloud.vn/logs"
echo ""
echo "💡 Troubleshooting:"
echo "   - Check image exists: docker pull vcr.vngcloud.vn/111480-abp111955/my-contract:v1.1"
echo "   - Verify credentials: echo \$GREENNODE_CLIENT_ID"
echo "   - Check logs: tail -f deployment.log"
echo ""
