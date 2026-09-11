"""
MiroFish Backend Entry Point
"""

import os
import sys

# Environment configuration for UTF-8 stability
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Inject project root into path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    """Main execution entry point"""
    # Validate environment configuration
    errors = Config.validate()
    if errors:
        print("Configuration Error:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease verify your .env configuration.")
        sys.exit(1)
    
    # Initialize Flask application
    app = create_app()
    
    # Extract runtime parameters
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    # Launch service
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()
