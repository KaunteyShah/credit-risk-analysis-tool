#!/bin/bash

# Docker Build and Push Script for Credit Risk App
# This script builds and pushes the Docker image to Docker Hub

set -e

# Configuration - UPDATE THESE VALUES
DOCKER_HUB_USERNAME="kaunteyshah974"  # Replace with your Docker Hub username
APP_NAME="credit-risk-app"
VERSION="latest"
DOCKER_IMAGE="$DOCKER_HUB_USERNAME/$APP_NAME:$VERSION"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building and pushing Docker image for Credit Risk App...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check if Docker buildx is available for multi-platform builds
echo -e "${YELLOW}Checking Docker buildx support...${NC}"
if ! docker buildx version > /dev/null 2>&1; then
    echo -e "${YELLOW}Docker buildx not available, using standard build...${NC}"
fi

# Docker Hub login assumed (you've already logged in)
echo -e "${GREEN}Proceeding with Docker build and push...${NC}"

# Build the Docker image for AMD64 architecture (Azure Container Instances compatibility)
echo -e "${YELLOW}Building Docker image for AMD64: $DOCKER_IMAGE${NC}"
docker build --platform linux/amd64 -t $DOCKER_IMAGE .

# Push to Docker Hub
echo -e "${YELLOW}Pushing image to Docker Hub...${NC}"
docker push $DOCKER_IMAGE

echo -e "${GREEN}Docker image successfully built and pushed!${NC}"
echo -e "${GREEN}Image: $DOCKER_IMAGE${NC}"

# Update the deployment script with the correct image name
if [ -f "deploy-aci.sh" ]; then
    echo -e "${YELLOW}Updating deploy-aci.sh with correct image name...${NC}"
    sed -i.bak "s|kaunteyshah974/credit-risk-app:latest|$DOCKER_IMAGE|g" deploy-aci.sh
    echo -e "${GREEN}Deploy script updated!${NC}"
fi

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Update the DOCKER_HUB_USERNAME in this script"
echo -e "2. Run: chmod +x docker-build.sh && ./docker-build.sh"
echo -e "3. Then run: chmod +x deploy-aci.sh && ./deploy-aci.sh"