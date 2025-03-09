import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def get_opensearch_client(collection_endpoint):
    credentials = boto3.Session().get_credentials()
    region = 'us-west-2'
    
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'aoss',  # Use 'aoss' for OpenSearch Serverless
        session_token=credentials.token
    )
    
    client = OpenSearch(
        hosts=[{'host': collection_endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60
    )
    
    return client

def create_index_mapping(client, index_name):
    mapping = {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "level": {"type": "keyword"},
                "service": {"type": "keyword"},
                "error_code": {"type": "keyword"},
                "message": {"type": "text"},
                "stack_trace": {"type": "text"},
                "correlation_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "metadata": {
                    "properties": {
                        "environment": {"type": "keyword"},
                        "region": {"type": "keyword"},
                        "version": {"type": "keyword"}
                    }
                },
                "message_embedding": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib"
                    }
                }
            }
        }
    }
    
    client.indices.create(index=index_name, body=mapping)
    print(f"Created index mapping for {index_name}")

def generate_embedding(bedrock, text):
    try:
        response = bedrock.invoke_model(
            modelId="cohere.embed-english-v3",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "texts": [text],
                "input_type": "search_query"
            })
        )
        embedding = json.loads(response['body'].read())['embeddings'][0]
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def get_collection_endpoint(client, collection_name):
    print(f"Getting endpoint for collection {collection_name}...")
    
    collections = client.list_collections(
        collectionFilters={'name': collection_name}
    )['collectionSummaries']
    
    if not collections:
        raise ValueError(f"Collection {collection_name} not found")
        
    collection_id = collections[0]['id']
    
    response = client.batch_get_collection(
        ids=[collection_id]
    )
    
    if not response['collectionDetails']:
        raise ValueError(f"No details found for collection {collection_name}")
        
    endpoint = response['collectionDetails'][0]['collectionEndpoint']
    print(f"Found endpoint: {endpoint}")
    return endpoint.replace('https://', '')

def main():
    try:
        # Initialize clients
        bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
        opensearch_client = boto3.client('opensearchserverless')
        collection_name = 'error-logs-mock'
        
        # Get collection endpoint
        collection_endpoint = get_collection_endpoint(opensearch_client, collection_name)
        
        # Initialize OpenSearch client
        os_client = get_opensearch_client(collection_endpoint)
        
        # Create index mapping
        index_name = 'error-logs-mock'
        try:
            create_index_mapping(os_client, index_name)
        except Exception as e:
            if 'resource_already_exists_exception' not in str(e):
                raise
            print(f"Index {index_name} already exists")
        
        # Load error logs
        with open('error_logs.json', 'r') as f:
            logs = json.load(f)
        
        # Index logs with embeddings
        print("Indexing logs with embeddings...")
        successful_indexes = 0
        
        for log in logs:
            embedding = generate_embedding(bedrock, log['message'])
            if embedding:
                log['message_embedding'] = embedding
                try:
                    # Remove id parameter, let OpenSearch generate it
                    os_client.index(
                        index=index_name,
                        body=log
                    )
                    successful_indexes += 1
                    if successful_indexes % 10 == 0:  # Progress update every 10 documents
                        print(f"Successfully indexed {successful_indexes} documents...")
                except Exception as e:
                    print(f"Error indexing log: {e}")
        
        print(f"\nIndexing complete. Successfully indexed {successful_indexes} out of {len(logs)} logs")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
