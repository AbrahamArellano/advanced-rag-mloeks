from flask import Flask, jsonify, request
import boto3
import json
import time
import logging
import os
from botocore.config import Config
from botocore.exceptions import ClientError
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
        
        # Get credentials
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            'us-west-2',
            'aoss',
            session_token=credentials.token
        )
        
        # Create OpenSearch client
        opensearch_client = OpenSearch(
            hosts=[{'host': endpoint, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            timeout=30,
            retry_on_timeout=True,
            max_retries=3,
            connection_class=RequestsHttpConnection
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
            "_source": ["message", "service", "error_code"],
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
        
        logger.info(f"OpenSearch response: {json.dumps(response, indent=2)}")
        logger.info(f"Total hits: {response['hits']['total']['value'] if 'hits' in response and 'total' in response['hits'] else 0}")
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                "score": hit["_score"],
                "message": hit["_source"]["message"],
                "service": hit["_source"]["service"],
                "error_code": hit["_source"]["error_code"]
            })
        
        logger.info(f"Processed results: {json.dumps(results, indent=2)}")
        
        return results
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        logger.error(f"Error type: {type(e)}")
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

        return jsonify({
            "query": query,
            "similar_documents": similar_docs,
            "processing_time": time.time() - start_time
        }), 200

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
