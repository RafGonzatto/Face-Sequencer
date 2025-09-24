#!/usr/bin/env python3
"""
Face Sequencer Pro - Startup Script
This script handles dependency installation and launches the web application.
"""

import os
import sys
import subprocess
import platform
import importlib

# Import centralized logging after creating the initial logger
try:
    # Dynamic import to allow launch.py to be run standalone
    from logger import get_logger, log_exception
    launch_logger = get_logger('app.launch')
except ImportError:
    # Create a basic logger if the main logger module isn't available yet
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    launch_logger = logging.getLogger('app.launch')
    log_exception = lambda logger, exc, context=None: logger.exception(str(exc))

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    try:
        # Check if pip is available
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ pip is not available. Please install pip first.")
        return False
    
    try:
        # Install requirements
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available for video export"""
    try:
        subprocess.check_call(["ffmpeg", "-version"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ FFmpeg detected - video export available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  FFmpeg not found - video export may not work")
        print("   Download FFmpeg from: https://ffmpeg.org/download.html")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "uploads",
        "projects",
        "static/css",
        "static/js",
        "templates"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Directory structure created")

def launch_application():
    """Launch the Flask web application"""
    print("🚀 Starting Face Sequencer Pro...")
    print("   Web interface will be available at: http://localhost:5000")
    print("   Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Import and run the Flask app
        from app import app  # imports model preload endpoint etc.
        # Optional model warmup (non-fatal)
        try:
            from model_manager import get_model_manager
            mm = get_model_manager()
            # Register common audio models lazily if not present
            if not any(m['name'] == 'whisperx_transcribe_tiny' for m in mm.stats()['models']):
                def _loader_transcribe():
                    import whisperx_compat as whisperx  # type: ignore
                    import torch  # type: ignore
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                    return whisperx.load_model('tiny', device, compute_type='int8')
                mm.register_model('whisperx_transcribe_tiny', _loader_transcribe, size_estimate=120_000_000, tags=['audio','whisperx'])
            # Preload if env flag set
            if os.environ.get('FACE_SEQ_PRELOAD_MODELS', 'false').lower() in ('1','true','yes'):
                print('🔄 Preloading configured models...')
                mm.preload(['whisperx_transcribe_tiny'])
        except Exception as warm_err:  # noqa: BLE001
            print(f"⚠️ Model warmup skipped: {warm_err}")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except ImportError as e:
        print(f"❌ Failed to import application: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Application error: {e}")
        return False

def open_browser():
    """Attempt to open the web browser"""
    import webbrowser
    import time
    
    # Import at top level to avoid circular imports
    from logger import get_logger, log_exception
    browser_logger = get_logger('app.browser')
    
    def delayed_open():
        time.sleep(2)  # Wait for server to start
        try:
            browser_logger.info("Opening web browser to application URL")
            webbrowser.open('http://localhost:5000')
        except Exception as e:
            # Log the error instead of silently failing
            log_exception(browser_logger, e)
            print("⚠️ Could not open browser automatically. Please navigate to http://localhost:5000 manually.")
    
    import threading
    thread = threading.Thread(target=delayed_open, daemon=True)
    thread.start()

def main():
    """Main startup routine"""
    print("=" * 50)
    print("🎬 Face Sequencer Pro - Setup & Launch")
    print("=" * 50)
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    # Create directory structure
    create_directories()
    
    # Install dependencies
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found")
        sys.exit(1)
    
    if not install_dependencies():
        print("❌ Dependency installation failed")
        print("   Try running: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check optional dependencies
    check_ffmpeg()
    
    # Launch application
    print("\n" + "=" * 50)
    
    # Auto-open browser on Windows/Mac
    if platform.system() in ['Windows', 'Darwin']:
        open_browser()
    
    success = launch_application()
    
    if success:
        print("\n👋 Thanks for using Face Sequencer Pro!")
    else:
        print("\n❌ Application failed to start")
        sys.exit(1)

if __name__ == "__main__":
    main()