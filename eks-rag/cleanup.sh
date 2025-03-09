#!/bin/bash
# cleanup.sh

echo "Starting cleanup process..."

# Delete Kubernetes resources
echo "Deleting Kubernetes service..."
kubectl delete service eks-rag-service --ignore-not-found
echo "Deleting Kubernetes deployment..."
kubectl delete deployment eks-rag --ignore-not-found

# Delete ECR images
echo "Deleting ECR images..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2
REPO_NAME=advanced-rag-mloeks/eks-rag

# Delete all images in the repository
aws ecr batch-delete-image \
    --repository-name $REPO_NAME \
    --image-ids $(aws ecr list-images --repository-name $REPO_NAME --query 'imageIds[*]' --output json) \
    || echo "No images to delete or repository not found."

echo "Cleanup complete!"
