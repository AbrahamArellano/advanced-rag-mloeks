#!/bin/bash
# cleanup.sh

# Delete Kubernetes resources
kubectl delete service eks-rag-service
kubectl delete deployment eks-rag

# Optional: Delete the ECR images
aws ecr batch-delete-image \
    --repository-name advanced-rag-mloeks/eks-rag \
    --image-ids imageTag=latest