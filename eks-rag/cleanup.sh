#!/bin/bash

echo "Starting cleanup..."

# Delete Kubernetes resources
echo "Deleting service..."
kubectl delete service eks-rag-service

echo "Deleting deployment..."
kubectl delete deployment eks-rag

# Remove Docker images
echo "Removing local Docker image..."
docker rmi advanced-rag-mloeks/eks-rag:latest

# Remove images from nodes
echo "Removing Docker images from nodes..."
for node in $(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}')
do
    echo "Cleaning up node: $node"
    ssh -i /path/to/your/key.pem ec2-user@$node "docker rmi advanced-rag-mloeks/eks-rag:latest"
done

# Verify cleanup
echo "Verifying cleanup..."
echo "Services:"
kubectl get services
echo "Deployments:"
kubectl get deployments
echo "Pods:"
kubectl get pods

echo "Cleanup complete!"
