#!/usr/bin/env python3
"""Ultra-minimal Flask app for Azure testing"""
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def home():
    return jsonify({'message': 'Azure test app running'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    app.run(host='0.0.0.0', port=port, debug=False)