from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/echo', methods=['GET'])
def echo():
    return jsonify({"message": "Hello from the future RAG service!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)