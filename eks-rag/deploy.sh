#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t advanced-rag-mloeks/eks-rag:latest .

# Save the image
echo "Saving Docker image..."
docker save advanced-rag-mloeks/eks-rag:latest > eks-rag.tar

# Get external IP addresses of the nodes
NODES=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}')

# Copy and load image to each node
for node in $NODES
do
    echo "Processing node: $node"
    echo "Copying image to node..."
    scp -i /path/to/your/key.pem eks-rag.tar ec2-user@$node:~
    
    echo "Loading image on node..."
    ssh -i /path/to/your/key.pem ec2-user@$node "docker load < eks-rag.tar"
done

# Clean up the tar file
echo "Cleaning up..."
rm eks-rag.tar

# Update deployment.yaml to use the correct image name
sed -i 's/image: .*/image: advanced-rag-mloeks\/eks-rag:latest/' deployment.yaml

# Deploy to Kubernetes
echo "Deploying to Kubernetes..."
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/eks-rag

# Show status
echo "Deployment status:"
kubectl get deployments
echo "Pod status:"
kubectl get pods
echo "Service status:"
kubectl get services

echo "Deployment complete!"