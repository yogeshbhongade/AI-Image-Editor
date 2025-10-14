#!/usr/bin/env python3
"""
Main application runner for AI Image Editor
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main application entry point"""
    try:
        from app import create_app
        
        # Create Flask app
        app = create_app()
        
        # Get configuration
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_ENV', 'development') == 'development'
        
        print("🚀 Starting AI Image Editor...")
        print(f"📍 Running on http://localhost:{port}")
        print("📋 Press Ctrl+C to stop")
        
        # Run the application
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
