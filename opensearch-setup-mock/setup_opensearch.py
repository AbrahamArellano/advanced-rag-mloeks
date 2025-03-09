import boto3
import json
import time
from botocore.exceptions import ClientError

def create_encryption_policy(client, collection_name):
    try:
        policy_document = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"]
                }
            ],
            "AWSOwnedKey": True
        }
        
        client.create_security_policy(
            name=f"{collection_name}-policy",
            policy=json.dumps(policy_document),
            type="encryption"
        )
        print(f"Created encryption policy for {collection_name}")
        return True
        
    except ClientError as e:
        print(f"Error creating encryption policy: {e}")
        return False


def create_collection(client, collection_name):
    try:
        # Create VECTORSEARCH collection (required for embeddings)
        response = client.create_collection(
            name=collection_name,
            description='Error logs for RAG demo with vector search',
            type='VECTORSEARCH'
        )
        print(f"Creating collection: {collection_name}")
        
        # Wait for collection to be active
        print("Waiting for collection to be active...")
        while True:
            collections = client.list_collections(
                collectionFilters={'name': collection_name}
            )['collectionSummaries']
            if collections and collections[0]['status'] == 'ACTIVE':
                break
            print("Still creating...")
            time.sleep(30)
        
        print("Collection is active")
        return True
        
    except ClientError as e:
        print(f"Error creating collection: {e}")
        return False

def create_access_policy(client, collection_name):
    try:
        # Get current identity
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        current_identity = identity['Arn']
        
        policy_document = [{
            "Rules": [
                {
                    "ResourceType": "index",
                    "Resource": [f"index/{collection_name}/*"],
                    "Permission": ["aoss:*"]
                },
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"],
                    "Permission": ["aoss:*"]
                }
            ],
            "Principal": [current_identity]
        }]
        
        client.create_access_policy(
            name=f"{collection_name}-access",
            policy=json.dumps(policy_document),
            type="data"
        )
        print(f"Created access policy for {collection_name}")
        return True
        
    except ClientError as e:
        print(f"Error creating access policy: {e}")
        return False

def create_network_policy(client, collection_name):
    try:
        policy_document = [{
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"]
                }
            ],
            "AllowFromPublic": True
        }]
        
        client.create_security_policy(
            name=f"{collection_name}-network",
            policy=json.dumps(policy_document),
            type="network"
        )
        print(f"Created network policy for {collection_name}")
        return True
        
    except ClientError as e:
        print(f"Error creating network policy: {e}")
        return False

def main():
    try:
        # Initialize AWS client
        client = boto3.client('opensearchserverless')
        collection_name = 'error-logs-mock'
        
        print(f"\nStarting setup for collection: {collection_name}")
        
        # Create encryption policy first
        if not create_encryption_policy(client, collection_name):
            raise Exception("Failed to create encryption policy")
        
        # Create collection
        if not create_collection(client, collection_name):
            raise Exception("Failed to create collection")
        
        # Create network policy
        if not create_network_policy(client, collection_name):
            raise Exception("Failed to create network policy")
        
        # Create access policy
        if not create_access_policy(client, collection_name):
            raise Exception("Failed to create access policy")
        
        print("\nSetup completed successfully!")
        
    except Exception as e:
        print(f"\nError during setup: {str(e)}")
        raise

if __name__ == "__main__":
    main()
