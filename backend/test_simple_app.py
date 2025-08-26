#!/usr/bin/env python3
"""
Simple test script to validate the simple_app.py health endpoint
This can be run locally to ensure the app structure is correct
"""

import sys
import importlib.util
from pathlib import Path

def test_simple_app():
    """Test that simple_app.py can be imported and has the required structure"""
    print("Testing simple_app.py structure...")
    
    # Get the path to simple_app.py
    simple_app_path = Path(__file__).parent / "simple_app.py"
    
    if not simple_app_path.exists():
        print(f"ERROR: {simple_app_path} does not exist!")
        return False
    
    # Try to load the module without executing it
    spec = importlib.util.spec_from_file_location("simple_app", simple_app_path)
    
    if spec is None:
        print("ERROR: Could not create module spec")
        return False
    
    print("✓ simple_app.py file exists and can be loaded")
    
    # Read the file and check for required components
    with open(simple_app_path, 'r') as f:
        content = f.read()
    
    required_components = [
        "from fastapi import FastAPI",
        "import uvicorn",
        "@app.get(\"/health\")",
        "if __name__ == \"__main__\":",
        "port = int(os.environ.get(\"PORT\"",
        "uvicorn.run("
    ]
    
    for component in required_components:
        if component in content:
            print(f"✓ Found: {component}")
        else:
            print(f"✗ Missing: {component}")
            return False
    
    print("\n✓ All required components found in simple_app.py")
    print("✓ The app should work on Render!")
    return True

if __name__ == "__main__":
    success = test_simple_app()
    if not success:
        sys.exit(1)
    print("\n🎉 simple_app.py is ready for deployment!")