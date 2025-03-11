import gradio as gr
import requests
import json
import sseclient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


RAG_SERVICE_URL = "http://eks-rag-service/submit_query"


# Send query to RAG service
def send_query(query):
    logger.info(f"Sending query: {query}")
    try:
        payload = {
            "query": query
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        # amazonq-ignore-next-line
        response = requests.post(RAG_SERVICE_URL,
                                 headers=headers,
                                 data=json.dumps(payload),
                                 stream=True)
        response.raise_for_status()
        
        client = sseclient.SSEClient(response)
        
        full_response = ""
        for event in client.events():
            if event.data != "[DONE]":
                try:
                    decoded_data = json.loads(event.data)
                    chunk = decoded_data['choices'][0]['delta'].get('content', '')
                    full_response += chunk
                    yield full_response
                except json.JSONDecodeError:
                    continue
        
        logger.info("Query completed successfully")
        return full_response
    
    except requests.RequestException as e:
        error_msg = f"Error: {str(e)}\nResponse content: {response.text if 'response' in locals() else 'No response'}"
        logger.error(error_msg)
        return error_msg

# Default prompts for testing
default_prompts = [
    "What are the user authentication failed errors?",
    "Show me the payment transaction failed errors",
    "Show me the timeout errors",
]

iface = gr.Interface(
    fn=send_query,
    inputs=gr.components.Textbox(
        lines=3, 
        placeholder="Enter your question here...",
        label="Question"
    ),
    outputs=gr.components.Textbox(lines=10, label="Answer"),
    title="AI Assistant",
    description="Ask questions about the system being observed! (Responses will stream in real-time)",
    examples=[[prompt] for prompt in default_prompts],
    theme="default"
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=7860)
