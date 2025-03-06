from flask import Flask, jsonify, request
import time

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/echo', methods=['GET'])
def echo():
    return jsonify({"message": "Hello from the future RAG service!"}), 200

@app.route('/submit_query', methods=['POST'])
def submit_query():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({
            "error": "Missing query parameter"
        }), 400

    user_query = data['query']
    
    # Simulate some processing time
    time.sleep(1)

    # Simple mock response
    response = {
        "answer": f"This is a mock response to your query: '{user_query}'"
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
