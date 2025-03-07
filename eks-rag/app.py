from flask import Flask, jsonify, request
import boto3
import json
import time
import logging
import os
from botocore.config import Config
from botocore.exceptions import ClientError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = app.logger

# Configure boto3 with timeouts and retries
boto3_config = Config(
    connect_timeout=5,
    read_timeout=30,
    retries={'max_attempts': 2}
)

# Initialize both Bedrock clients
bedrock_runtime = None
bedrock = None

try:
    start_time = time.time()
    logger.info("Initializing Bedrock clients...")
    
    # For model invocation
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-west-2',
        config=boto3_config
    )
    
    # For management operations
    bedrock = boto3.client(
        service_name='bedrock',
        region_name='us-west-2',
        config=boto3_config
    )
    
    logger.info(f"Bedrock client initialization took: {time.time() - start_time:.2f} seconds")
except Exception as e:
    logger.error(f"Failed to initialize Bedrock clients: {e}")

# Constants
EMBEDDING_MODEL_ID = "cohere.embed-english-v3"

def check_model_availability():
    """Check if the specified model is available for use"""
    try:
        if not bedrock:
            logger.error("Bedrock client not initialized")
            return False
            
        response = bedrock.list_foundation_models()
        available_models = [model.get('modelId') for model in response.get('modelSummaries', [])]
        
        if EMBEDDING_MODEL_ID not in available_models:
            logger.error(f"Model {EMBEDDING_MODEL_ID} not found in available models")
            logger.info(f"Available models: {available_models}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error checking model availability: {e}")
        return False

def generate_embedding(text):
    """Generate embeddings for the provided text using Bedrock"""
    if not text or not isinstance(text, str):
        logger.error("Invalid text input")
        return None
        
    if not bedrock_runtime:
        logger.error("Bedrock runtime client not initialized")
        return None
        
    try:
        start_total = time.time()
        
        # Log request preparation
        logger.info(f"Preparing embedding request for text: {text[:50]}...")
        request_body = {
            "texts": [text],
            "input_type": "search_query"
        }
        logger.info(f"Request body prepared in: {time.time() - start_total:.2f} seconds")

        # Log API call start
        logger.info("Starting Bedrock API call...")
        api_start = time.time()
        
        response = bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        api_time = time.time() - api_start
        logger.info(f"Bedrock API call completed in: {api_time:.2f} seconds")

        # Log response processing
        logger.info("Processing response...")
        process_start = time.time()
        
        response_body = json.loads(response['body'].read())
        
        if 'embeddings' not in response_body:
            logger.error(f"Unexpected response format: {response_body}")
            return None
            
        embedding = response_body['embeddings'][0]
        
        process_time = time.time() - process_start
        total_time = time.time() - start_total
        
        logger.info(f"Response processing took: {process_time:.2f} seconds")
        logger.info(f"Total embedding generation took: {total_time:.2f} seconds")
        logger.info(f"Embedding dimension: {len(embedding)}")
        
        return embedding

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'No message')
        
        logger.error(f"Bedrock ClientError: {error_code} - {error_message}")
        
        if error_code == 'AccessDeniedException':
            logger.error("Access denied. Check IAM permissions for Bedrock.")
        elif error_code == 'ModelNotReadyException':
            logger.error(f"Model {EMBEDDING_MODEL_ID} is not ready for invocation")
        elif error_code == 'ModelNotFoundException':
            logger.error(f"Model {EMBEDDING_MODEL_ID} not found. Check model ID and region.")
        elif error_code == 'ValidationException':
            logger.error(f"Invalid request: {error_message}")
        elif error_code == 'ThrottlingException':
            logger.error("Request throttled. Consider implementing backoff strategy.")
        
        return None
    except Exception as e:
        logger.error(f"Error in generate_embedding: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@app.route('/submit_query', methods=['POST'])
def submit_query():
    start_time = time.time()
    logger.info("Received submit_query request")
    
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query parameter"}), 400

        query = data['query']
        logger.info(f"Processing query: {query[:50]}...")
        
        # Generate embedding
        embedding = generate_embedding(query)
        if embedding is None:
            return jsonify({"error": "Failed to generate embedding"}), 500

        total_time = time.time() - start_time
        
        # Return limited response (embedding vectors can be large)
        return jsonify({
            "query": query[:100] + ("..." if len(query) > 100 else ""),
            "embedding_dimension": len(embedding),
            "processing_time_seconds": total_time
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in submit_query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    health_status = {
        "status": "degraded",
        "components": {
            "app": "healthy",
            "bedrock_clients": "unknown"
        },
        "checks": []
    }
    
    # Check Bedrock clients initialization
    if bedrock and bedrock_runtime:
        health_status["components"]["bedrock_clients"] = "healthy"
        health_status["checks"].append({
            "name": "bedrock_clients_initialization",
            "status": "pass"
        })
    else:
        health_status["components"]["bedrock_clients"] = "unhealthy"
        health_status["checks"].append({
            "name": "bedrock_clients_initialization",
            "status": "fail",
            "message": "One or more Bedrock clients failed to initialize"
        })
        return jsonify(health_status), 500
    
    # Check model availability
    try:
        model_available = check_model_availability()
        health_status["checks"].append({
            "name": "model_availability",
            "status": "pass" if model_available else "fail",
            "message": None if model_available else f"Model {EMBEDDING_MODEL_ID} not available"
        })
        
        if not model_available:
            health_status["status"] = "degraded"
            return jsonify(health_status), 200
    except Exception as e:
        health_status["checks"].append({
            "name": "model_availability",
            "status": "fail",
            "message": f"Error checking model availability: {str(e)}"
        })
        health_status["status"] = "degraded"
        return jsonify(health_status), 200
    
    # All checks passed
    health_status["status"] = "healthy"
    return jsonify(health_status), 200

@app.route('/test_embedding', methods=['GET'])
def test_embedding():
    """Simple endpoint to test embedding generation with a fixed input"""
    try:
        test_text = "This is a test query to verify embedding generation"
        start_time = time.time()
        
        embedding = generate_embedding(test_text)
        if embedding is None:
            return jsonify({
                "status": "error",
                "message": "Failed to generate test embedding"
            }), 500
            
        return jsonify({
            "status": "success",
            "test_text": test_text,
            "embedding_dimension": len(embedding),
            "processing_time_seconds": time.time() - start_time
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))