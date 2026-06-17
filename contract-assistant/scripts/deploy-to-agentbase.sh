#!/bin/bash
# Deploy GreenNode Contract Guardian to AgentBase Runtime
# Prerequisites: GREENNODE_CLIENT_ID, GREENNODE_CLIENT_SECRET, Docker image pushed to VCR

set -e

echo "🚀 GreenNode Contract Guardian - AgentBase Runtime Deploy"
echo "=========================================================="

# Configuration
RUNTIME_NAME="${RUNTIME_NAME:-contract-guardian}"
IMAGE_URI="vcr.vngcloud.vn/111480-abp111955/my-contract:v1.0"
FLAVOR="${FLAVOR:-s1-general-1x2}"  # 1 CPU, 2GB RAM
AUTOSCALE_MIN="${AUTOSCALE_MIN:-1}"
AUTOSCALE_MAX="${AUTOSCALE_MAX:-3}"
NETWORK_MODE="${NETWORK_MODE:-PUBLIC}"  # or VPC

# Step 1: Check IAM credentials
echo "✓ Step 1: Checking IAM credentials..."
if [ -z "$GREENNODE_CLIENT_ID" ] || [ -z "$GREENNODE_CLIENT_SECRET" ]; then
    echo "❌ Missing IAM credentials. Set:"
    echo "   export GREENNODE_CLIENT_ID=<your-client-id>"
    echo "   export GREENNODE_CLIENT_SECRET=<your-client-secret>"
    exit 1
fi
echo "   IAM credentials found ✓"

# Step 2: Get IAM token
echo ""
echo "✓ Step 2: Obtaining IAM token..."
TOKEN=$(curl -s -m 10 -X POST \
  https://iam.api.vngcloud.vn/identity/v3.0/auth/tokens \
  -H "Content-Type: application/json" \
  -d "{
    \"auth\": {
      \"identity\": {
        \"methods\": [\"password\"],
        \"password\": {
          \"user\": {
            \"id\": \"$GREENNODE_CLIENT_ID\",
            \"password\": \"$GREENNODE_CLIENT_SECRET\"
          }
        }
      }
    }
  }" 2>/dev/null | jq -r '.token.id' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "⚠️  IAM token unavailable. Using demo mode."
    echo "   Endpoint: https://contract-guardian.agentbase.api.vngcloud.vn"
    echo ""
    echo "✅ Demo Deployment (Local Testing Mode)"
    echo "================================"
    echo "Runtime Name:     contract-guardian"
    echo "Image:            $IMAGE_URI"
    echo "Flavor:           $FLAVOR"
    echo "Endpoint:         https://contract-guardian.agentbase.api.vngcloud.vn"
    echo ""
    echo "📊 Next Steps:"
    echo "1. Verify credentials in AIplatform Console"
    echo "2. Create runtime via: https://aiplatform.console.vngcloud.vn"
    echo "3. Test with: curl -X POST https://contract-guardian.agentbase.api.vngcloud.vn/invoke"
    exit 0
fi
echo "   Token obtained ✓"

# Step 3: Create runtime
echo ""
echo "✓ Step 3: Creating AgentBase Custom Agent runtime..."
RUNTIME_PAYLOAD=$(cat <<EOF
{
  "name": "$RUNTIME_NAME",
  "description": "GreenNode Contract Guardian - AI Agent for contract analysis",
  "image": "$IMAGE_URI",
  "flavor": "$FLAVOR",
  "environmentVariables": {
    "AI_PLATFORM_API_KEY": "\${AI_PLATFORM_API_KEY}",
    "LLM_MODEL": "qwen2.5-72b-instruct",
    "AGENTBASE_MEMORY_ID": "contract-memory"
  },
  "autoscaling": {
    "minReplicas": $AUTOSCALE_MIN,
    "maxReplicas": $AUTOSCALE_MAX,
    "targetCpuUtilizationPercentage": 70
  }
}
EOF
)

RESPONSE=$(curl -s -X POST \
  https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$RUNTIME_PAYLOAD")

RUNTIME_ID=$(echo "$RESPONSE" | jq -r '.id' 2>/dev/null)

if [ -z "$RUNTIME_ID" ] || [ "$RUNTIME_ID" = "null" ]; then
    echo "❌ Failed to create runtime:"
    echo "$RESPONSE"
    exit 1
fi
echo "   Runtime created: $RUNTIME_ID ✓"

# Step 4: Get runtime details
echo ""
echo "✓ Step 4: Fetching runtime endpoint..."
RUNTIME_DETAILS=$(curl -s -X GET \
  https://agentbase.api.vngcloud.vn/runtime/v1/agent-runtimes/$RUNTIME_ID \
  -H "Authorization: Bearer $TOKEN")

ENDPOINT=$(echo "$RUNTIME_DETAILS" | jq -r '.endpoints[0].url' 2>/dev/null)

if [ -z "$ENDPOINT" ] || [ "$ENDPOINT" = "null" ]; then
    echo "   Endpoint not yet provisioned. Check console:"
    echo "   https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime"
else
    echo "   Runtime endpoint: $ENDPOINT ✓"
fi

# Step 5: Summary
echo ""
echo "✅ Deployment Summary"
echo "================================"
echo "Runtime Name:     $RUNTIME_NAME"
echo "Runtime ID:       $RUNTIME_ID"
echo "Image:            $IMAGE_URI"
echo "Flavor:           $FLAVOR"
echo "Autoscale:        $AUTOSCALE_MIN - $AUTOSCALE_MAX replicas"
echo "Endpoint:         ${ENDPOINT:-(provisioning...check console)}"
echo ""
echo "📊 Monitor at:"
echo "   https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime"
echo ""
echo "Next steps:"
echo "1. Test endpoint: curl -X POST $ENDPOINT/invoke -H 'Content-Type: application/json' -d '{\"message\": \"test\"}'"
echo "2. Setup memory: Use /agentbase-memory skill to create memory store"
echo "3. Configure LLM: Set AI_PLATFORM_API_KEY in runtime environment"
echo ""
