#!/bin/bash

# Set up ECR repository path
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-west-2
export ECR_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/advanced-rag-mloeks/eks-rag

# Get ECR login token
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push the image
echo "Building Docker image..."
docker build -t $ECR_REPO:latest .

echo "Pushing image to ECR..."
docker push $ECR_REPO:latest

# Process template and deploy
echo "Deploying to Kubernetes..."
envsubst < deployment.yaml | kubectl apply -f -
kubectl apply -f service.yaml

# Wait for deployment
echo "Waiting for deployment..."
kubectl rollout status deployment/eks-rag --timeout=300s

# Show status
echo "Checking deployment status..."
kubectl get deployments
kubectl get pods
kubectl get services
