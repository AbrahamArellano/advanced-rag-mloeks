# Real-Time AI Chat and Analytics Platform on AWS

## Overview

> [!CAUTION]
> This is an experimental solution to demonstrate the pattern. Do not use it in production. Deploying this will incur AWS charges.


This repository contains the infrastructure and application code for deploying a real-time AI chat and analytics platform on AWS. The solution enables users to interact with a Generative AI interface, asking questions and deriving insights from real-time streaming data such as vehicle sensor data and machine IoT data.

## Architecture

The solution leverages the following AWS services and technologies:

- Amazon EKS: Hosts the Llama3 LLM model
- vLLM and Ray: Used for efficient inference
- Amazon OpenSearch Serverless: Stores vector embeddings of user queries and real-time input data
- AWS Lambda: Generates random timestamped logs
- Amazon MSK: Streams and stores logs


![image](/arag-doeks.jpg)


## Prerequisites

- AWS account
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- [Docker](https://docs.docker.com/engine/install/) {for building and pushing container images}

## Deployment instructions

- [Step 1: Deploy Amazon EKS cluster to host the LLM](#step-1-deploy-amazon-eks-cluster-to-host-the-llm)
- [Step 2: Deploy Amazon MSK cluster for streaming logs into](#step-2-deploy-amazon-msk-cluster-for-streaming-logs-into)
- [Step 3: Deploy RAG service to generate embeddings for user queries and timestamped logs, and run inference against deployed LLM](#step-3-deploy-rag-service-to-generate-embeddings-for-user-queries-and-timestamped-logs-and-run-inference-against-deployed-llm)
- [Step 4: Deploy application UI](#step-4-deploy-application-ui)

### Step 1: Deploy Amazon EKS cluster to host the LLM

1. Clone the Data on EKS repository and deploy

```
git clone  https://github.com/awslabs/data-on-eks.git
cd data-on-eks/ai-ml/trainium-inferentia/
./install.sh
```

2. Verify the cluster is up

```
aws eks --region us-west-2 describe-cluster --name trainium-inferentia
```

3. Create kubernetes config file to authenticate with EKS

```
aws eks --region us-west-2 update-kubeconfig --name trainium-inferentia

kubectl get nodes # Output shows the EKS Managed Node group nodes
```

4. Deploy the Ray Cluster with LLama3 model

>To deploy the llama3-8B-Instruct model, it's essential to configure your Hugging Face Hub token as an environment variable. This token is required for authentication and accessing the model. For guidance on how to create and manage your Hugging Face tokens, please visit [Hugging Face Token Management](https://huggingface.co/docs/hub/security-tokens).

```
export HUGGING_FACE_HUB_TOKEN=<Your-Hugging-Face-Hub-Token-Value>

cd gen-ai/inference/vllm-rayserve-inf2

envsubst < vllm-rayserve-deployment.yaml| kubectl apply -f -
```
5. Verify the deployment by running the following commands

> The deployment process may take up to 10 minutes. The Head Pod is expected to be ready within 2 to 3 minutes, while the Ray Serve worker pod may take up to 10 minutes for image retrieval and Model deployment from Huggingface.

```
kubectl get all -n vllm
NAME                                                          READY   STATUS    RESTARTS   AGE
pod/lm-llama3-inf2-raycluster-gf5cv-worker-inf2-group-t2ftw   1/1     Running   0          19h
pod/vllm-llama3-inf2-raycluster-gf5cv-head-bxjvl              2/2     Running   0          19h

NAME                                 TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                                         AGE
service/vllm                         ClusterIP   172.20.174.59   <none>        8080/TCP,6379/TCP,8265/TCP,10001/TCP,8000/TCP   38d
service/vllm-llama3-inf2-head-svc    ClusterIP   172.20.246.2    <none>        6379/TCP,8265/TCP,10001/TCP,8000/TCP,8080/TCP   38d
service/vllm-llama3-inf2-serve-svc   ClusterIP   172.20.52.67    <none>        8000/TCP                                        38d

NAME                                                  DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS   AGE
raycluster.ray.io/vllm-llama3-inf2-raycluster-gf5cv   1                 1                   32     130G     0      ready    38d

NAME                                 SERVICE STATUS   NUM SERVE ENDPOINTS
rayservice.ray.io/vllm-llama3-inf2   Running          2
```

### Step 2: Deploy Amazon MSK cluster for streaming logs into

First, we need to grab the VPC and private subnet IDs created in the previous step.

Get the VPC ID
```
export VPC_ID=`aws ec2 describe-vpcs --filters Name=tag:Name,Values=trainium-inferentia --region us-west-2 --query 'Vpcs[*].VpcId' --output text`
```

Get the private subnets
```
export SUBNET_ID1=`aws ec2 describe-subnets --filter Name=cidr-block,Values=10.1.0.0/24 Name=vpc-id,Values=$VPC_ID --region us-west-2 --query Subnets[*].SubnetId --output text`

export SUBNET_ID2=`aws ec2 describe-subnets --filter Name=cidr-block,Values=10.1.1.0/24 Name=vpc-id,Values=$VPC_ID --region us-west-2 --query Subnets[*].SubnetId --output text`
```

Create MSK cluster
```
#create serverless collection config JSON
cat << EOF > kafka-config.json
{
  "VpcConfigs": [
    {
      "SubnetIds": ["$SUBNET_ID1","$SUBNET_ID2"],
      "SecurityGroupIds": ["$SECURITY_GROUP_ID"]
    }
  ],
  "ClientAuthentication":{
    "Sasl":{
      "Iam":{
        "Enabled": true
      }
    }
  }
}
EOF

aws kafka create-cluster-v2 --cluster-name mycluster --serverless file://kafka-config.json --region us-west-2
```

### Step 3: Deploy RAG service to generate embeddings for user queries and timestamped logs, and run inference against deployed LLM

The RAG service handles vector embeddings generation, semantic search, and LLM inference orchestration.

Clone the RAG service repository

```    
git clone https://github.com/your-repo/advanced-rag-mloeks.git
cd advanced-rag-mloeks/opensearch-setup-mock
```

Set up OpenSearch Serverless collection and policies

```    
python3 setup_opensearch.py
```
    
Generate and index initial logs with embeddings

``` 
python3 generate_logs.py
python3 index_logs.py
```
    
Deploy the RAG service to EKS
```
# Create kubernetes deployment
kubectl apply -f deployment.yaml
```

```
# Create kubernetes service
kubectl apply -f service.yaml
```

```
# Create network policy to allow access to vLLM
kubectl apply -f network-policy.yaml
```
    
Verify the deployment

```    
# Check if pods are running
kubectl get pods
```

```
# Check if service is created
kubectl get service eks-rag-service
```
```
# Test the service
export SERVICE_IP=$(kubectl get service eks-rag-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```
```
# Test with a sample query
curl -X POST \
  http://$SERVICE_IP/submit_query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show critical engine temperature alerts"}' | json_pp
```

> For production use cases, we recommend using sophisticated consumers in Lambda function to consume logs from the Kafka cluster and then store embeddings in an Opensearch serverless collection. Sample code for a consumer Lambda is available at opensearch-setup/consume_logs.py.

### Step 4: Deploy application UI

To deploy the sample Gradio UI appliction, deploy the provided `ui/deployment.yaml`

```sh
kubectl apply -f ui/deployment.yaml
```

This will create AWS Load Balancer for ingress.

```sh
kubectl get ingress gradio-app-ingress
```
Open the ADDRESS in a web browser to open the UI.



## Cleanup
Finally, here are the instructions for cleaning up and deprovisioning the resources when they are no longer needed.

### Delete the UI

```sh
kubectl delete -f ui/deployment.yaml
```

### Delete the RayCluster
```
cd data-on-eks/gen-ai/inference/vllm-rayserve-inf2

kubectl delete -f vllm-rayserve-deployment.yaml
```

### Destroy the EKS Cluster
```
cd data-on-eks/ai-ml/trainium-inferentia/

./cleanup.sh
```