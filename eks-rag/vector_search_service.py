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

class OpenSearchManager:
    def __init__(self, collection_name='error-logs-mock', region='us-west-2'):
        self.collection_name = collection_name
        self.region = region
        self.endpoint = self._get_endpoint()

    def _get_endpoint(self):
        os_serverless = boto3.client('opensearchserverless')
        collections = os_serverless.list_collections(
            collectionFilters={'name': self.collection_name}
        )['collectionSummaries']
        
        if collections:
            collection_id = collections[0]['id']
            collection_details = os_serverless.batch_get_collection(ids=[collection_id])
            endpoint = collection_details['collectionDetails'][0]['collectionEndpoint']
            return endpoint.replace('https://', '')
        raise ValueError(f"Collection {self.collection_name} not found")

    def get_client(self):
        """Get OpenSearch client with fresh credentials"""
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'aoss',
            session_token=credentials.token
        )
        
        return OpenSearch(
            hosts=[{'host': self.endpoint, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            timeout=30,
            retry_on_timeout=True,
            max_retries=3,
            connection_class=RequestsHttpConnection
        )

class BedrockManager:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.client = self._initialize_client()

    def _initialize_client(self):
        config = Config(
            connect_timeout=5,
            read_timeout=30,
            retries={'max_attempts': 2}
        )
        return boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region,
            config=config
        )

    def generate_embedding(self, text):
        """Generate embeddings using Bedrock"""
        try:
            response = self.client.invoke_model(
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

class VectorSearchService:
    def __init__(self):
        self.opensearch_manager = None
        self.bedrock_manager = None
        self._initialize_services()

    def _initialize_services(self):
        try:
            self.opensearch_manager = OpenSearchManager()
            self.bedrock_manager = BedrockManager()
            logger.info("Services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    def vector_search(self, embedding, k=5):
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
            
            # Get client with fresh credentials
            client = self.opensearch_manager.get_client()
            
            response = client.search(
                index=self.opensearch_manager.collection_name,
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

# Initialize the service
service = VectorSearchService()

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
        embedding = service.bedrock_manager.generate_embedding(query)
        if embedding is None:
            return jsonify({"error": "Failed to generate embedding"}), 500
        
        # Perform vector search
        similar_docs = service.vector_search(embedding)
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
