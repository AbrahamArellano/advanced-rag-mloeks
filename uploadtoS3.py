import gradio as gr
import boto3
import random
import os
from botocore.exceptions import ClientError
import logging
from dotenv import load_dotenv
import tempfile

#load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_to_s3(file):
    try:

        # Access your AWS credentials
        s3_client = boto3.client('s3')

        # Get the bucket name from environment variable
        bucket_name = os.environ.get('AWS_BUCKET_NAME')

        if not bucket_name:
            raise ValueError("AWS_BUCKET_NAME environment variable is not set.")
        
        if isinstance(file, dict):
            file_path = file['name']
        else:
            file_path = file.name

        s3_client.upload_file(file_path, bucket_name, os.path.basename(file_path))
        return "File uploaded successfully!"

    except ClientError as e:
        return f"ClientError: Error uploading file: {str(e)}"
    except Exception as e:
        return f"Error uploading file: {str(e)}"

def random_response(message, history):
    return random.choice(["Yes", "No"])

with gr.Blocks() as interface:
    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(label="Chat input")
            text_output = gr.Textbox(label="Chat output")
            chat_button = gr.Button("Send Message")
    
    #File upload
    with gr.Row():
        file_input = gr.UploadButton("Upload File", file_types=[".pdf"])
        file_output = gr.Textbox()
        file_input.upload(upload_to_s3, [file_input], file_output)

if __name__ == "__main__":
    interface.launch() 