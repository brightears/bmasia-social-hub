#!/usr/bin/env python3
"""
Absolute bare minimum HTTP server for Render deployment.
No external dependencies except standard library.
"""

import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with health endpoint"""
    
    def do_GET(self):
        """Handle GET requests"""
        logger.info(f"Received GET request: {self.path}")
        
        if self.path == '/health':
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            logger.info("Health check successful")
            
        elif self.path == '/':
            # Root endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'BMA Social API - Minimal Mode')
            
        else:
            # 404 for other paths
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use logger instead of stderr"""
        logger.info(f"{self.address_string()} - {format % args}")

def main():
    """Main entry point"""
    port = int(os.environ.get('PORT', 8000))
    
    logger.info("=" * 50)
    logger.info("Starting Bare Minimum Server")
    logger.info(f"Python version: {os.sys.version}")
    logger.info(f"PORT environment variable: {os.environ.get('PORT', 'NOT SET')}")
    logger.info(f"Binding to port: {port}")
    logger.info("=" * 50)
    
    # Create and start server
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Server listening on 0.0.0.0:{port}")
    logger.info(f"Health check available at: http://0.0.0.0:{port}/health")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == '__main__':
    main()