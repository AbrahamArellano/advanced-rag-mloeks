import os
import requests
from flask import Flask, jsonify, request
import boto3
import json
import time
import logging
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = app.logger

# Configure boto3 with timeouts and retries
boto3_config = Config(
    connect_timeout=5,
    read_timeout=30,
    retries={'max_attempts': 2}
)

# Custom connection class that refreshes AWS credentials before each request
class RefreshingAWS4AuthConnection(RequestsHttpConnection):
    def __init__(self, region, service="aoss", **kwargs):
        self.region = region
        self.service = service
        super().__init__(**kwargs)
    
    def perform_request(self, method, url, params=None, body=None, timeout=None, ignore=(), headers=None):
        # Get fresh credentials for each request
        credentials = boto3.Session().get_credentials()
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            self.service,
            session_token=credentials.token
        )
        
        # Update session auth with fresh credentials
        self.session.auth = auth
        
        # Proceed with the request
        return super().perform_request(method, url, params, body, timeout, ignore, headers)

# Initialize Bedrock client
bedrock_runtime = None
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-west-2',
        config=boto3_config
    )
    logger.info("Bedrock client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Bedrock client: {e}")

# Initialize OpenSearch client
opensearch_client = None
try:
    # Get collection endpoint
    os_serverless = boto3.client('opensearchserverless')
    collections = os_serverless.list_collections(
        collectionFilters={'name': 'error-logs-mock'}
    )['collectionSummaries']
    
    if collections:
        collection_id = collections[0]['id']
        collection_details = os_serverless.batch_get_collection(ids=[collection_id])
        endpoint = collection_details['collectionDetails'][0]['collectionEndpoint']
        endpoint = endpoint.replace('https://', '')
        
        # Create OpenSearch client with the custom connection class
        # No need to create AWS4Auth here as it's handled by the connection class
        opensearch_client = OpenSearch(
            hosts=[{'host': endpoint, 'port': 443}],
            use_ssl=True,
            verify_certs=True,
            timeout=30,
            retry_on_timeout=True,
            max_retries=3,
            connection_class=lambda **kwargs: RefreshingAWS4AuthConnection(
                region='us-west-2', 
                service='aoss',
                **kwargs
            )
        )
        logger.info("OpenSearch client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenSearch client: {e}")

def generate_embedding(text):
    """Generate embeddings using Bedrock"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId="cohere.embed-english-v3",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "texts": [text],
                "input_type": "search_query"
            })
        )
        embedding = json.loads(response['body'].read())['embeddings'][0]
        logger.info(f"Generated embedding with dimension: {len(embedding)}")
        logger.info(f"Generated embedding type: {type(embedding)}")
        logger.info(f"First few values of embedding: {embedding[:5]}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def vector_search(embedding, k=5):
    """Search for similar vectors in OpenSearch"""
    try:
        search_query = {
            "size": k,
            "_source": [
                "message", 
                "service", 
                "error_code",
                "vehicle_id",
                "vehicle_state",
                "sensor_readings",
                "diagnostic_info"
            ],
            "query": {
                "knn": {
                    "message_embedding": {
                        "vector": embedding,
                        "k": k
                    }
                }
            }
        }
        
        logger.info(f"Executing vector search with query: {json.dumps(search_query, indent=2)}")
        
        response = opensearch_client.search(
            index='error-logs-mock',
            body=search_query
        )
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                "score": hit["_score"],
                "message": hit["_source"]["message"],
                "service": hit["_source"]["service"],
                "error_code": hit["_source"]["error_code"],
                "vehicle_id": hit["_source"].get("vehicle_id", "N/A"),
                "vehicle_state": hit["_source"].get("vehicle_state", "N/A"),
                "sensor_readings": hit["_source"].get("sensor_readings", {}),
                "diagnostic_info": hit["_source"].get("diagnostic_info", {})
            })
        
        return results
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        return None

        
        
def query_vllm(prompt, context):
    """Query the vLLM model"""
    try:
        # Use the full Kubernetes DNS name for the service
        vllm_host = os.environ.get('VLLM_HOST', 'vllm-llama3-inf2-serve-svc.vllm.svc.cluster.local')
        vllm_port = os.environ.get('VLLM_PORT', '8000')
        vllm_url = f"http://{vllm_host}:{vllm_port}/v1/chat/completions"
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "model": "NousResearch/Meta-Llama-3-8B-Instruct",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Context: {context}\n\nQuery: {prompt}"}
            ]
        }
        
        response = requests.post(vllm_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"vLLM response: {json.dumps(result, indent=2)}")  
        return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Error querying vLLM: {e}")
        logger.error(f"Error details: {str(e)}") 
        return None


@app.route('/submit_query', methods=['POST'])
def submit_query():
    start_time = time.time()
    logger.info("Received submit_query request")
    
    try:
        # Get query
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query parameter"}), 400

        query = data['query']
        logger.info(f"Processing query: {query[:50]}...")
        
        # Generate embeddings
        embedding = generate_embedding(query)
        if embedding is None:
            return jsonify({"error": "Failed to generate embedding"}), 500
        
        # Perform vector search
        similar_docs = vector_search(embedding)
        if similar_docs is None:
            return jsonify({"error": "Failed to perform vector search"}), 500

        # Prepare context for LLM with more detailed information
        context_entries = []
        for doc in similar_docs:
            context_entry = (
                f"Error: {doc['message']}\n"
                f"Service: {doc['service']}\n"
                f"Error Code: {doc['error_code']}\n"
                f"Vehicle: {doc['vehicle_id']} (State: {doc['vehicle_state']})\n"
                f"Sensor Readings: {json.dumps(doc['sensor_readings'], indent=2)}\n"
                f"Diagnostic Info: {json.dumps(doc['diagnostic_info'], indent=2)}\n"
                "---"
            )
            context_entries.append(context_entry)
        
        context = "\n".join(context_entries)

        # Query vLLM
        llm_response = query_vllm(query, context)
        if llm_response is None:
            return jsonify({"error": "Failed to get response from vLLM"}), 500

        # Prepare the response
        response = {
            "query": query,
            "llm_response": llm_response,
            "similar_documents": similar_docs[:3],  # Include top 3 similar documents
            "processing_time": time.time() - start_time
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
