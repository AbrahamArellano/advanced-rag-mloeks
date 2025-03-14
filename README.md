# Real-Time AI Chat and Analytics Platform on AWS

## Overview

This repository contains the infrastructure and application code for deploying a real-time AI chat and analytics platform on AWS. The solution enables users to interact with a Generative AI interface, asking questions and deriving insights from real-time streaming data such as vehicle sensor data and machine IoT data.

## Architecture

The solution leverages the following AWS services and technologies:

- Amazon EKS: Hosts the Mistral LLM model
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
- [Docker] (for building and pushing container images) (https://docs.docker.com/engine/install/)

## Deployment instructions

### Step 1: Deploy Amazon EKS cluster to host the LLM

1. Clone the Data on EKS repository and deploy

`
git clone  https://github.com/awslabs/data-on-eks.git
cd data-on-eks/ai-ml/trainium-inferentia/
./install.sh
`

2. Verify the cluster is up

`
aws eks --region us-west-2 describe-cluster --name trainium-inferentia
`

3. Create kubernetes config file to authenticate with EKS

`
aws eks --region us-west-2 update-kubeconfig --name trainium-inferentia

kubectl get nodes # Output shows the EKS Managed Node group nodes
`

4. Deploy the Ray Cluster with LLama3 model

>To deploy the llama3-8B-Instruct model, it's essential to configure your Hugging Face Hub token as an environment variable. This token is required for authentication and accessing the model. For guidance on how to create and manage your Hugging Face tokens, please visit [Hugging Face Token Management](https://huggingface.co/docs/hub/security-tokens).

`
export HUGGING_FACE_HUB_TOKEN=<Your-Hugging-Face-Hub-Token-Value>

cd gen-ai/inference/vllm-rayserve-inf2

envsubst < vllm-rayserve-deployment.yaml| kubectl apply -f -

`
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

### Step 2: Deploy Lambda function for generating logs
### Step 3: Deploy Amazon MSK cluster for streaming logs into
### Step 4: Deploy RAG service to generate embeddings for user queries and timestamped logs, and run inference against deployed LLM
### Step 5: Deploy application UI