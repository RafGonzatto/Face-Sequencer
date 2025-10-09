"""Minimal test to diagnose Flask startup issue."""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"Working dir: {os.getcwd()}")

try:
    print("\n1. Importing Flask...")
    import flask
    print(f"   Flask version: {flask.__version__}")
    
    print("\n2. Checking asgiref...")
    try:
        import asgiref
        print(f"   asgiref version: {asgiref.__version__}")
    except ImportError as e:
        print(f"   asgiref NOT installed: {e}")
    
    print("\n3. Creating app...")
    from app.app import create_app
    app = create_app()
    print(f"   App created: {app}")
    
    print("\n4. Starting server...")
    print(f"   Will bind to 0.0.0.0:5000...")
    print("   Press Ctrl+C to stop.")
    try:
        # Explicitly use Werkzeug development server with threaded=True
        from werkzeug.serving import run_simple
        print("   Using Werkzeug run_simple directly...")
        run_simple('0.0.0.0', 5000, app, use_reloader=False, use_debugger=False, threaded=True)
    except KeyboardInterrupt:
        print("\n   Server stopped by user.")
    except Exception as run_err:
        print(f"\n   Server error: {run_err}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"\nERROR during setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
