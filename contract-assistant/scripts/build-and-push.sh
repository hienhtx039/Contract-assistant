#!/bin/bash
# Quick rebuild, tag, and push Docker image with latest memory integration

set -e

echo "🐳 Building & Pushing GreenNode Contract Guardian Image"
echo "======================================================"

IMAGE_NAME="my-contract"
REGISTRY="vcr.vngcloud.vn"
NAMESPACE="111480-abp111955"
TAG="${1:-v1.1}"

FULL_IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${TAG}"
LOCAL_IMAGE="${IMAGE_NAME}:latest"

echo "📦 Step 1: Building Docker image..."
docker build -f docker/Dockerfile.contract-guardian -t "$LOCAL_IMAGE" .
echo "✓ Image built: $LOCAL_IMAGE"

echo ""
echo "🏷️  Step 2: Tagging image..."
docker tag "$LOCAL_IMAGE" "$FULL_IMAGE"
echo "✓ Tagged: $FULL_IMAGE"

echo ""
echo "📤 Step 3: Pushing to VCR..."
docker push "$FULL_IMAGE"
echo "✓ Pushed: $FULL_IMAGE"

echo ""
echo "✅ Build & Push Complete!"
echo ""
echo "Next: Deploy to AgentBase Runtime"
echo "  bash scripts/deploy-to-agentbase.sh"
echo ""
echo "Or update existing runtime:"
echo "  Image URI: $FULL_IMAGE"
echo ""
