"""
NeoBank - Main Application Entry Point

This script serves as the main entry point to run the NeoBank application.
It imports the application factory, creates an instance of the app, and starts
the Flask server with appropriate security settings.

Security Note:
- Debug mode is disabled in production
- Load environment variables from .env file
- Use environment variable FLASK_ENV to control configuration
"""

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from app import create_app

# Load environment variables from .env file if python-dotenv is installed
if load_dotenv:
    load_dotenv()
else:
    print('Warning: python-dotenv is not installed. Using system environment variables only.')

# Initialize the Flask application using the factory function
app = create_app()

if __name__ == '__main__':
    # Get environment and debug setting from environment variables
    env = os.getenv('FLASK_ENV', 'development').lower()
    debug_mode = env == 'development'  # Only enable debug in development
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')  # Listen on all interfaces by default
    
    # Print startup information
    print(f"Starting NeoBank application")
    print(f"Environment: {env}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Host: {host}:{port}")
    print(f"Access the application at http://127.0.0.1:{port} (local) or http://<server-ip>:{port}")
    
    # Start the Flask server
    app.run(
        debug=debug_mode, 
        host=host,
        port=port,
        use_reloader=debug_mode  # Only use reloader in development
    )
