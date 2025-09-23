"""
End-to-End Test for the Face Sequencer Video Export Flow

This script tests the complete export process including:
1. Creating a sequence
2. Starting the export
3. Monitoring progress
4. Validating the file
5. Downloading the file

It also includes a direct test of the FFmpeg export function.

Usage:
    python test_export_e2e.py [--direct-test]
"""

import os
import sys
import time
import requests
import json
from urllib.parse import urljoin
import argparse

# Base URL for the Face Sequencer API
BASE_URL = "http://localhost:5000/api/"

# Sample sequence for testing
TEST_SEQUENCE = [
    {"char": "H", "img": "images/AE.png", "ms": 500},
    {"char": "E", "img": "images/AE.png", "ms": 500},
    {"char": "L", "img": "images/LI.png", "ms": 500},
    {"char": "L", "img": "images/LI.png", "ms": 500},
    {"char": "O", "img": "images/OU.png", "ms": 500}
]

def api_call(endpoint, method="get", data=None):
    """Make an API call to the Face Sequencer server"""
    url = urljoin(BASE_URL, endpoint)
    print(f"\n{method.upper()} {url}")
    
    if method.lower() == "get":
        response = requests.get(url)
    elif method.lower() == "post":
        response = requests.post(url, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
        
    # Print status code and response
    print(f"Status: {response.status_code}")
    try:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    except:
        print(f"Raw response: {response.text[:200]}...")
        return response.text

def create_test_project():
    """Create a test project with a simple sequence"""
    print("\n=== Creating Test Project ===")
    
    # Update project with our test sequence
    project_data = {
        "name": "Export Test Project",
        "sequence": TEST_SEQUENCE,
        "settings": {
            "fps": 2,  # 2 fps for 500ms frames
            "bgcolor": "#000000",
            "size": [200, 200]
        }
    }
    
    # Send the project update request
    result = api_call("project", method="post", data=project_data)
    
    if result.get('success'):
        print("✅ Test project created successfully")
        return True
    else:
        print("❌ Failed to create test project")
        return False

def start_export(filename="test_export.mp4", quality="medium"):
    """Start the export process"""
    print(f"\n=== Starting Export: {filename} (Quality: {quality}) ===")
    
    export_data = {
        "filename": filename,
        "quality": quality  # Options: high, medium, fast
    }
    
    # Start the export
    result = api_call("export/video", method="post", data=export_data)
    
    if result.get('success'):
        print(f"✅ Export started with task ID: {result.get('task_id')}")
        return result.get('task_id')
    else:
        print("❌ Failed to start export")
        return None

def monitor_export_progress(task_id, timeout=120, poll_interval=2):
    """Monitor the export progress"""
    print(f"\n=== Monitoring Export Progress (Task: {task_id}) ===")
    
    start_time = time.time()
    last_progress = -1
    completed = False
    
    while time.time() - start_time < timeout:
        # Check export status
        result = api_call(f"export/status/{task_id}")
        
        if not result.get('success'):
            print(f"❌ Error checking export status: {result.get('error')}")
            return None
            
        task = result.get('task', {})
        status = task.get('status')
        progress = task.get('progress', 0)
        message = task.get('message', '')
        
        # Only print updates when progress changes
        if progress != last_progress:
            print(f"Status: {status}, Progress: {progress}%, Message: {message}")
            last_progress = progress
        
        # Check if export is complete or failed
        if status == 'completed':
            print(f"✅ Export completed successfully in {time.time() - start_time:.1f} seconds")
            completed = True
            break
        elif status == 'error':
            print(f"❌ Export failed: {task.get('error')}")
            return None
        elif status == 'cancelled':
            print(f"❌ Export was cancelled")
            return None
            
        # Sleep before next poll
        time.sleep(poll_interval)
    
    if not completed:
        print(f"❌ Export timed out after {timeout} seconds")
        return None
        
    return task

def validate_export(task_id):
    """Validate the exported file"""
    print(f"\n=== Validating Export (Task: {task_id}) ===")
    
    result = api_call(f"export/validate/{task_id}")
    
    if result.get('success') and result.get('valid'):
        print(f"✅ Export validation successful")
        print(f"   File size: {result.get('fileSize', 0)} bytes")
        return True
    else:
        print(f"❌ Export validation failed: {result.get('error')}")
        return False

def download_export(task_id):
    """Download the exported file"""
    print(f"\n=== Downloading Export (Task: {task_id}) ===")
    
    url = urljoin(BASE_URL, f"export/download/{task_id}")
    print(f"Downloading from: {url}")
    
    # Send direct request to get file
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            # Save the downloaded file
            output_path = f"test_download_{task_id}.mp4"
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            file_size = os.path.getsize(output_path)
            print(f"✅ File downloaded successfully: {output_path}")
            print(f"   File size: {file_size} bytes")
            return output_path
        else:
            try:
                error = response.json().get('error', 'Unknown error')
            except:
                error = response.text
            print(f"❌ Download failed: {error}")
            return None
    except Exception as e:
        print(f"❌ Error during download: {str(e)}")
        return None

def run_export_test():
    """Run the complete export test flow"""
    print("===== FACE SEQUENCER EXPORT E2E TEST =====")
    
    # Create test project
    if not create_test_project():
        print("❌ Test failed: Could not create project")
        return False
        
    # Try different quality presets
    for quality in ["fast", "medium"]:
        # Start the export
        task_id = start_export(filename=f"test_{quality}.mp4", quality=quality)
        if not task_id:
            print(f"❌ Test failed: Could not start {quality} export")
            continue
            
        # Monitor progress
        export_task = monitor_export_progress(task_id)
        if not export_task:
            print(f"❌ Test failed: {quality} export did not complete")
            continue
            
        # Validate export
        if not validate_export(task_id):
            print(f"❌ Test failed: {quality} export validation failed")
            continue
            
        # Download the file
        output_path = download_export(task_id)
        if not output_path:
            print(f"❌ Test failed: Could not download {quality} export")
            continue
            
        print(f"\n✅ {quality.upper()} EXPORT TEST SUCCESSFUL!")
        
    print("\n===== TEST COMPLETED =====")
    return True

def test_direct_export():
    """
    Test the direct FFmpeg export function in lipanim_core_demo.py
    This bypasses the API and tests the export function directly
    """
    from lipanim_core_demo import export_mp4
    
    def progress_callback(percent, message):
        """Display progress updates"""
        sys.stdout.write(f"\rProgress: {percent}% - {message}")
        sys.stdout.flush()
    
    print("\n===== DIRECT EXPORT TEST =====")
    
    # Create a simple test sequence using debug images
    debug_dir = os.path.join(os.path.dirname(__file__), 'debug_export')
    images = {}
    
    if os.path.exists(debug_dir):
        for image in os.listdir(debug_dir):
            if image.endswith('.png'):
                color = os.path.splitext(image)[0]
                images[color.upper()] = os.path.join(debug_dir, image)
    
    # If we don't have debug images, try using images from the images directory
    if not images:
        images_dir = os.path.join(os.path.dirname(__file__), 'images')
        if os.path.exists(images_dir):
            for image in os.listdir(images_dir):
                if image.endswith('.png'):
                    name = os.path.splitext(image)[0]
                    images[name] = os.path.join(images_dir, image)
    
    if not images:
        print("No test images found. Please create debug_export directory with test PNGs.")
        return False
    
    # Create a simple test sequence
    color_seq = list(images.keys())
    print(f"Creating test sequence with images: {color_seq}")
    
    # Build a sequence alternating through the available images
    test_seq = []
    for i in range(20):  # 20 frames
        color_key = color_seq[i % len(color_seq)]
        test_seq.append({
            'char': color_key[0],
            'img': images[color_key],
            'ms': 250  # 250ms per frame
        })
    
    # Export to MP4
    print(f"Exporting {len(test_seq)} frames to direct_test.mp4")
    output_path = os.path.join(os.path.dirname(__file__), 'direct_test.mp4')
    
    # Time the export
    start_time = time.time()
    
    success = export_mp4(
        seq=test_seq,
        path=output_path,
        fps=24,
        crf=23,
        preset="medium",
        progress_callback=progress_callback
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print the result
    print(f"\n\nExport {'succeeded' if success else 'failed'} in {duration:.2f} seconds")
    
    if success:
        print(f"Output file: {output_path}")
        print(f"File size: {os.path.getsize(output_path) / 1024:.2f} KB")
    
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the Face Sequencer Video Export')
    parser.add_argument('--direct-test', action='store_true', help='Run the direct export test only')
    args = parser.parse_args()
    
    if args.direct_test:
        success = test_direct_export()
    else:
        # Run the test
        success = run_export_test()
    
    sys.exit(0 if success else 1)