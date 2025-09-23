# app.py - Flask Web Server for Face Sequencer Pro
import os
import json
import string
import time
import threading
from datetime import datetime
from pathlib import Path
import base64
import io

# Apply PyTorch 2.6 compatibility fix for WhisperX (top of file to ensure patch is applied early)
try:
    import torch
    original_torch_load = torch.load
    torch.load = lambda f, *args, **kwargs: original_torch_load(f, *args, weights_only=False, **{k: v for k, v in kwargs.items() if k != 'weights_only'})
    print("✅ PyTorch load function patched for WhisperX compatibility")
except Exception as e:
    print(f"⚠️ Warning: Could not patch torch.load: {e}")

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

# Import original functionality
from lipanim_core_demo import (
    load_letter_map_from_dir, 
    build_sequence as create_sequence, 
    export_json, 
    export_mp4, 
    valid_img
)

# Import project management
from project_templates import ProjectTemplates, ProjectManager

# Import audio alignment system
try:
    from audio_aligner import AudioAligner, AlignmentToken, TokenType
    AUDIO_ALIGNMENT_AVAILABLE = True
except ImportError as e:
    print(f"Audio alignment not available: {e}")
    AUDIO_ALIGNMENT_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['AUDIO_FOLDER'] = 'uploads/audio'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['ALLOWED_AUDIO_EXTENSIONS'] = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['AUDIO_FOLDER'], exist_ok=True)

# Initialize project manager
project_manager = ProjectManager()

# Global state for the application
app_state = {
    'current_project': {
        'name': 'Untitled Project',
        'folder_path': '',
        'fallback_image': '',
        'text': '',
        'letter_map': {},
        'sequence': [],
        'settings': {
            'frame_duration': 80,
            'pause_duration': 120,
            'fps': 30,
            'quality': 14,
            'preset': 'medium'
        }
    },
    'export_tasks': {},
    'preview_state': {
        'current_frame': 0,
        'playing': False,
        'loop': True
    }
}

LETTERS = list(string.ascii_uppercase)

@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/api/project', methods=['GET'])
def get_project():
    """Get current project state"""
    return jsonify({
        'success': True,
        'project': app_state['current_project']
    })

@app.route('/api/project', methods=['POST'])
def update_project():
    """Update project settings"""
    try:
        data = request.get_json()
        
        # Update project fields
        if 'name' in data:
            app_state['current_project']['name'] = data['name']
        
        if 'text' in data:
            app_state['current_project']['text'] = data['text']
        
        if 'settings' in data:
            app_state['current_project']['settings'].update(data['settings'])
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/folder/scan', methods=['POST'])
def scan_folder():
    """Scan folder for character mappings"""
    try:
        data = request.get_json()
        folder_path = data.get('path', '')
        
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify({'success': False, 'error': 'Invalid folder path'}), 400
        
        # Load letter mappings
        letter_map = load_letter_map_from_dir(folder_path)
        
        # Update app state
        app_state['current_project']['folder_path'] = folder_path
        app_state['current_project']['letter_map'] = letter_map
        
        # Generate mapping info for frontend
        mapping_info = {}
        for letter in LETTERS:
            mapping_info[letter] = {
                'mapped': letter in letter_map,
                'path': letter_map.get(letter, ''),
                'filename': os.path.basename(letter_map.get(letter, '')) if letter in letter_map else ''
            }
        
        return jsonify({
            'success': True,
            'mapped_count': len(letter_map),
            'total_letters': len(LETTERS),
            'mappings': mapping_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mapping/thumbnails', methods=['POST'])
def get_mapping_thumbnails():
    """Generate thumbnails for character mappings"""
    try:
        data = request.get_json()
        letters = data.get('letters', LETTERS)
        
        thumbnails = {}
        letter_map = app_state['current_project']['letter_map']
        
        for letter in letters:
            if letter in letter_map and valid_img(letter_map[letter]):
                try:
                    # Generate base64 thumbnail
                    with Image.open(letter_map[letter]) as img:
                        img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        thumbnail_data = base64.b64encode(buffer.getvalue()).decode()
                        thumbnails[letter] = f"data:image/png;base64,{thumbnail_data}"
                except Exception:
                    pass  # Skip invalid images
        
        return jsonify({
            'success': True,
            'thumbnails': thumbnails
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sequence/build', methods=['POST'])
def build_sequence():
    """Build animation sequence from text"""
    try:
        project = app_state['current_project']
        text = project['text']
        letter_map = project['letter_map']
        settings = project['settings']
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        # Build sequence using original function
        sequence = create_sequence(
            text,
            letter_map,
            settings['frame_duration'],
            settings['pause_duration'],
            project['fallback_image'] or None
        )
        
        # Update app state
        app_state['current_project']['sequence'] = sequence
        
        # Generate sequence info for frontend
        sequence_info = []
        for i, frame in enumerate(sequence):
            frame_info = {
                'index': i,
                'char': frame['char'],
                'duration': frame['ms'],
                'is_pause': frame['img'] is None,
                'filename': os.path.basename(frame['img']) if frame['img'] else None
            }
            
            # Generate thumbnail for non-pause frames
            if frame['img'] and valid_img(frame['img']):
                try:
                    with Image.open(frame['img']) as img:
                        img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        thumbnail_data = base64.b64encode(buffer.getvalue()).decode()
                        frame_info['thumbnail'] = f"data:image/png;base64,{thumbnail_data}"
                except Exception:
                    pass
            
            sequence_info.append(frame_info)
        
        return jsonify({
            'success': True,
            'sequence': sequence_info,
            'total_frames': len(sequence),
            'total_duration': sum(f['ms'] for f in sequence)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sequence/frame/<int:frame_id>', methods=['GET'])
def get_frame_image(frame_id):
    """Get full-size frame image for preview"""
    try:
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify({'success': False, 'error': 'Invalid frame ID'}), 400
        
        frame = sequence[frame_id]
        
        if frame['img'] is None:
            # Generate pause frame
            return jsonify({
                'success': True,
                'is_pause': True,
                'char': frame['char'],
                'duration': frame['ms']
            })
        
        if not valid_img(frame['img']):
            return jsonify({'success': False, 'error': 'Invalid image path'}), 400
        
        # Generate base64 image for preview
        with Image.open(frame['img']) as img:
            # Resize for web preview if too large
            if max(img.size) > 800:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'is_pause': False,
            'char': frame['char'],
            'duration': frame['ms'],
            'image': f"data:image/png;base64,{image_data}",
            'dimensions': img.size
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sequence/update', methods=['POST'])
def update_sequence():
    """Update sequence frame properties"""
    try:
        data = request.get_json()
        frame_id = data.get('frame_id')
        updates = data.get('updates', {})
        
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify({'success': False, 'error': 'Invalid frame ID'}), 400
        
        # Update frame properties
        if 'duration' in updates:
            sequence[frame_id]['ms'] = max(1, int(updates['duration']))
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sequence/reorder', methods=['POST'])
def reorder_sequence():
    """Reorder sequence frames"""
    try:
        data = request.get_json()
        from_index = data.get('from_index')
        to_index = data.get('to_index')
        
        sequence = app_state['current_project']['sequence']
        
        if (from_index < 0 or from_index >= len(sequence) or 
            to_index < 0 or to_index >= len(sequence)):
            return jsonify({'success': False, 'error': 'Invalid frame indices'}), 400
        
        # Reorder frames
        frame = sequence.pop(from_index)
        sequence.insert(to_index, frame)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/sequence/delete', methods=['POST'])
def delete_frame():
    """Delete frame from sequence"""
    try:
        data = request.get_json()
        frame_id = data.get('frame_id')
        
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify({'success': False, 'error': 'Invalid frame ID'}), 400
        
        # Delete frame
        del sequence[frame_id]
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/json', methods=['POST'])
def export_sequence_json():
    """Export sequence as JSON"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'sequence.json')
        
        sequence = app_state['current_project']['sequence']
        
        if not sequence:
            return jsonify({'success': False, 'error': 'No sequence to export'}), 400
        
        # Generate unique filename
        export_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        # Export using original function
        export_json(sequence, export_path)
        
        return send_file(export_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/video', methods=['POST'])
def export_sequence_video():
    """Start video export task"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'sequence.mp4')
        quality_preset = data.get('quality', 'medium')
        
        sequence = app_state['current_project']['sequence']
        settings = app_state['current_project']['settings']
        
        if not sequence:
            return jsonify({'success': False, 'error': 'No sequence to export'}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Quality presets
        quality_settings = {
            'high': {'crf': 12, 'preset': 'slow'},
            'medium': {'crf': 18, 'preset': 'medium'},
            'fast': {'crf': 24, 'preset': 'fast'}
        }
        
        quality_config = quality_settings.get(quality_preset, quality_settings['medium'])
        
        # Create export task
        export_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        
        app_state['export_tasks'][task_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': filename,
            'path': export_path,
            'error': None,
            'message': 'Preparing to export video',
            'started_at': datetime.now()
        }
        
        # Start export in background thread
        def export_worker():
            try:
                app_state['export_tasks'][task_id]['status'] = 'processing'
                
                # Define progress callback function
                def update_progress(progress, message=None):
                    # Update task progress
                    app_state['export_tasks'][task_id]['progress'] = progress
                    if message:
                        app_state['export_tasks'][task_id]['message'] = message
                    
                    # Handle error signal
                    if progress < 0:
                        app_state['export_tasks'][task_id]['status'] = 'error'
                        app_state['export_tasks'][task_id]['error'] = message if message else "Unknown error"
                
                # Get the global fallback image for the project
                fallback_path = app_state['current_project'].get('fallback_image')
                if fallback_path:
                    print(f"Using project fallback image: {fallback_path}")
                
                # Ensure all sequence frames have the project fallback for consistency
                for frame in sequence:
                    if not frame.get('fallback_img') and fallback_path:
                        frame['fallback_img'] = fallback_path
                
                # Call export with progress callback
                success = export_mp4(
                    seq=sequence,
                    path=export_path,
                    fps=settings['fps'],
                    crf=quality_config['crf'],
                    preset=quality_config['preset'],
                    progress_callback=update_progress
                )
                
                # Update final status based on success flag
                if success:
                    app_state['export_tasks'][task_id]['status'] = 'completed'
                    app_state['export_tasks'][task_id]['progress'] = 100
                    app_state['export_tasks'][task_id]['message'] = "Export completed successfully"
                else:
                    # If export_mp4 returned False but didn't set error status via callback
                    if app_state['export_tasks'][task_id]['status'] != 'error':
                        app_state['export_tasks'][task_id]['status'] = 'error'
                        app_state['export_tasks'][task_id]['error'] = "Export failed"
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                app_state['export_tasks'][task_id]['status'] = 'error'
                app_state['export_tasks'][task_id]['error'] = str(e)
        
        # Create a non-daemon thread so it won't be killed when Flask reloads
        thread = threading.Thread(target=export_worker)
        thread.daemon = False  # Set to non-daemon so it completes even if main thread exits
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/status/<task_id>', methods=['GET'])
def get_export_status(task_id):
    """Get export task status"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = app_state['export_tasks'][task_id]
        return jsonify({
            'success': True,
            'task': task
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/retry/<task_id>', methods=['POST'])
def retry_export(task_id):
    """Retry a failed export task"""
    try:
        # Check if task exists
        if task_id not in app_state['export_tasks']:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        original_task = app_state['export_tasks'][task_id]
        
        # Only retry if task was in error state
        if original_task['status'] != 'error':
            return jsonify({'success': False, 'error': 'Can only retry failed exports'}), 400
        
        # Get current sequence and settings
        sequence = app_state['current_project']['sequence']
        settings = app_state['current_project']['settings']
        
        if not sequence:
            return jsonify({'success': False, 'error': 'No sequence to export'}), 400
        
        # Generate a new task ID
        new_task_id = str(uuid.uuid4())
        
        # Use same quality settings as original
        # Default to medium quality if original settings not available
        quality_preset = 'medium'
        if 'quality_preset' in original_task:
            quality_preset = original_task['quality_preset']
            
        # Quality presets
        quality_settings = {
            'high': {'crf': 12, 'preset': 'slow'},
            'medium': {'crf': 18, 'preset': 'medium'},
            'fast': {'crf': 24, 'preset': 'fast'}
        }
        
        quality_config = quality_settings.get(quality_preset, quality_settings['medium'])
        
        # Create new export task
        export_path = original_task['path']
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        
        app_state['export_tasks'][new_task_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': original_task['filename'],
            'path': export_path,
            'error': None,
            'message': 'Preparing to retry export',
            'started_at': datetime.now(),
            'quality_preset': quality_preset
        }
        
        # Start export in background thread
        def export_worker():
            try:
                app_state['export_tasks'][new_task_id]['status'] = 'processing'
                
                # Define progress callback function
                def update_progress(progress, message=None):
                    try:
                        # Ensure progress is a valid number
                        if progress is not None and not isinstance(progress, (int, float)):
                            print(f"Warning: Invalid progress value: {progress}, type: {type(progress)}")
                            progress = 0
                            
                        # Update task progress (ensure it's an integer)
                        if progress is not None:
                            app_state['export_tasks'][new_task_id]['progress'] = int(progress)
                        
                        # Update message if provided
                        if message:
                            app_state['export_tasks'][new_task_id]['message'] = message
                            print(f"Export progress: {progress}% - {message}")
                        
                        # Handle error signal
                        if progress is not None and progress < 0:
                            app_state['export_tasks'][new_task_id]['status'] = 'error'
                            app_state['export_tasks'][new_task_id]['error'] = message if message else "Unknown error"
                            print(f"Export error: {message}")
                    except Exception as e:
                        print(f"Error in update_progress: {e} (progress: {progress}, message: {message})")
                
                # Get the global fallback image for the project
                fallback_path = app_state['current_project'].get('fallback_image')
                if fallback_path:
                    print(f"Using project fallback image: {fallback_path}")
                
                # Ensure all sequence frames have the project fallback for consistency
                for frame in sequence:
                    if not frame.get('fallback_img') and fallback_path:
                        frame['fallback_img'] = fallback_path
                
                # Call export with progress callback
                success = export_mp4(
                    seq=sequence,
                    path=export_path,
                    fps=settings['fps'],
                    crf=quality_config['crf'],
                    preset=quality_config['preset'],
                    progress_callback=update_progress
                )
                
                # Update final status based on success flag
                if success:
                    app_state['export_tasks'][new_task_id]['status'] = 'completed'
                    app_state['export_tasks'][new_task_id]['progress'] = 100
                    app_state['export_tasks'][new_task_id]['message'] = "Export retry completed successfully"
                else:
                    # If export_mp4 returned False but didn't set error status via callback
                    if app_state['export_tasks'][new_task_id]['status'] != 'error':
                        app_state['export_tasks'][new_task_id]['status'] = 'error'
                        app_state['export_tasks'][new_task_id]['error'] = "Export retry failed"
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                app_state['export_tasks'][new_task_id]['status'] = 'error'
                app_state['export_tasks'][new_task_id]['error'] = str(e)
        
        # Create a non-daemon thread so it won't be killed when Flask reloads
        thread = threading.Thread(target=export_worker)
        thread.daemon = False  # Set to non-daemon so it completes even if main thread exits
        thread.start()
        
        return jsonify({
            'success': True,
            'original_task_id': task_id,
            'new_task_id': new_task_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def validate_mp4_file(file_path):
    """Validate that a file is a proper MP4 file
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        tuple: (is_valid, error_message, file_size)
    """
    # Check file existence
    if not os.path.exists(file_path):
        return False, "File not found", 0
    
    # Check file size
    file_size = os.path.getsize(file_path)
    print(f"Validating MP4 file: {file_path} (size: {file_size} bytes)")
    
    if file_size < 1024:  # If file is smaller than 1KB
        return False, f"File too small ({file_size} bytes)", file_size
    
    # Check if the file is a text file (error output)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith("Error") or "error" in first_line.lower():
                return False, f"File contains error message: {first_line}", file_size
    except UnicodeDecodeError:
        # Not a text file, which is good for an MP4
        pass
    
    # Check MP4 signature
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read more bytes to be safe
            # MP4 files typically start with ftyp or mdat
            if not any(sig in header for sig in [b'ftyp', b'mdat', b'moov', b'free']):
                return False, f"Invalid MP4 signature", file_size
    except Exception as e:
        return False, f"Error reading file header: {str(e)}", file_size
    
    # Optional: Try to check video with FFmpeg if available
    try:
        import subprocess
        # Use FFprobe to check if file is valid
        result = subprocess.run(
            ['ffprobe', '-v', 'error', file_path],
            capture_output=True,
            text=True,
            timeout=3  # 3 second timeout
        )
        
        if result.returncode != 0:
            error = result.stderr.strip()
            return False, f"FFprobe validation failed: {error}", file_size
    except Exception as e:
        # FFprobe unavailable or failed, just log and continue
        print(f"FFprobe validation skipped: {e}")
    
    print(f"MP4 validation passed for {file_path}")
    return True, f"Valid MP4 file ({file_size} bytes)", file_size

@app.route('/api/export/validate/<task_id>', methods=['GET'])
def validate_export(task_id):
    """Validate that an exported MP4 file is proper"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = app_state['export_tasks'][task_id]
        
        if task['status'] != 'completed':
            return jsonify({
                'success': False, 
                'error': 'Export not completed',
                'status': task['status'],
                'progress': task['progress'],
                'message': task['message']
            }), 400
        
        is_valid, error_msg, filesize = validate_mp4_file(task['path'])
        
        if not is_valid:
            app_state['export_tasks'][task_id]['status'] = 'error'
            app_state['export_tasks'][task_id]['error'] = error_msg
            return jsonify({
                'success': False, 
                'error': error_msg,
                'valid': False,
                'fileSize': filesize,
                'filename': task['filename']
            }), 400
        
        return jsonify({
            'success': True,
            'valid': True,
            'fileSize': filesize,
            'filename': task['filename'],
            'message': error_msg  # This will contain the validation success message
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/download/<task_id>', methods=['GET'])
def download_export(task_id):
    """Download completed export"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = app_state['export_tasks'][task_id]
        
        if task['status'] != 'completed':
            return jsonify({'success': False, 'error': 'Export not completed'}), 400
        
        if not os.path.exists(task['path']):
            return jsonify({'success': False, 'error': 'Export file not found'}), 404
        
        # Always validate the MP4 file before downloading
        print(f"Validating file before download: {task['path']}")
        is_valid, error_msg, filesize = validate_mp4_file(task['path'])
        
        if not is_valid:
            print(f"Validation failed: {error_msg}")
            app_state['export_tasks'][task_id]['status'] = 'error'
            app_state['export_tasks'][task_id]['error'] = error_msg
            return jsonify({'success': False, 'error': error_msg, 'fileSize': filesize}), 400
            
        print(f"Validation passed: {error_msg}, size: {filesize} bytes")
        
        # If validation passes, try different approaches to serve the file
        file_path = os.path.abspath(task['path'])
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Define common headers for all response methods
        headers = {
            'Content-Disposition': f'attachment; filename="{task["filename"]}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(filesize),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        # Try different methods to send the file
        try:
            # Method 1: Flask's send_file
            response = send_file(
                task['path'], 
                as_attachment=True,
                download_name=task['filename'],
                mimetype='video/mp4'
            )
            
            # Add custom headers
            for header, value in headers.items():
                response.headers[header] = value
                
            print(f"Using send_file method to serve {task['filename']} ({filesize} bytes)")
            return response
            
        except Exception as e1:
            print(f"send_file failed: {str(e1)}, trying alternate method...")
            
            try:
                # Method 2: send_from_directory
                response = send_from_directory(
                    directory, 
                    filename,
                    as_attachment=True,
                    download_name=task['filename'],
                    mimetype='video/mp4'
                )
                
                # Add custom headers
                for header, value in headers.items():
                    response.headers[header] = value
                    
                print(f"Using send_from_directory method to serve {task['filename']}")
                return response
                
            except Exception as e2:
                print(f"send_from_directory failed: {str(e2)}, using direct Response...")
                
                # Method 3: Direct response with file data
                try:
                    with open(file_path, 'rb') as file_data:
                        response = Response(
                            file_data.read(),
                            mimetype='video/mp4',
                            headers=headers
                        )
                        print(f"Using direct Response method to serve {task['filename']}")
                        return response
                        
                except Exception as e3:
                    print(f"Direct Response method failed: {str(e3)}")
                    return jsonify({
                        'success': False, 
                        'error': f"All file serving methods failed: {str(e3)}"
                    }), 500
    
    except Exception as e:
        error_msg = f"Error downloading export: {str(e)}"
        app.logger.error(error_msg)  # Log the error
        return jsonify({'success': False, 'error': error_msg}), 400

@app.route('/api/project/save', methods=['POST'])
def save_project():
    """Save project to JSON file"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'project.json')
        
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'created_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        project_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        return send_file(project_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/project/load', methods=['POST'])
def load_project():
    """Load project from JSON file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Read and parse project file
        project_data = json.load(file.stream)
        
        # Update app state
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        
        # Clear existing sequence and mappings
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        
        return jsonify({
            'success': True,
            'project': app_state['current_project']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get available project templates"""
    try:
        templates = ProjectTemplates.list_templates()
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/templates/<template_name>/apply', methods=['POST'])
def apply_template(template_name):
    """Apply template to current project"""
    try:
        # Apply template settings to current project
        ProjectTemplates.apply_template(template_name, app_state['current_project'])
        
        return jsonify({
            'success': True,
            'project': app_state['current_project']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/projects/recent', methods=['GET'])
def get_recent_projects():
    """Get recent projects list"""
    try:
        recent_projects = project_manager.get_recent_projects()
        return jsonify({
            'success': True,
            'projects': recent_projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/projects/<path:project_path>/load', methods=['POST'])
def load_project_by_path(project_path):
    """Load project by file path"""
    try:
        project_data = project_manager.load_project(project_path)
        
        # Update app state
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        
        # Clear existing sequence and mappings
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        
        return jsonify({
            'success': True,
            'project': app_state['current_project']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/projects/save-managed', methods=['POST'])
def save_managed_project():
    """Save project using project manager"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'sequence': app_state['current_project']['sequence']
        }
        
        project_path = project_manager.save_project(project_data, filename)
        
        return jsonify({
            'success': True,
            'project_path': project_path,
            'message': 'Project saved successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============================================================================
# AUDIO ALIGNMENT SYSTEM
# ============================================================================

def allowed_audio_file(filename):
    """Check if file has allowed audio extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_AUDIO_EXTENSIONS']

def get_audio_aligner():
    """Get or create audio aligner instance"""
    if not AUDIO_ALIGNMENT_AVAILABLE:
        return None
        
    if not hasattr(get_audio_aligner, '_aligner'):
        get_audio_aligner._aligner = AudioAligner(language="pt-BR")
        print("🎵 Audio aligner initialized (Portuguese-first)")
    
    return get_audio_aligner._aligner

@app.route('/api/audio/status', methods=['GET'])
def audio_status():
    """Get audio alignment system status"""
    return jsonify({
        'success': True,
        'available': AUDIO_ALIGNMENT_AVAILABLE,
        'language': 'pt-BR' if AUDIO_ALIGNMENT_AVAILABLE else None,
        'supported_formats': list(app.config['ALLOWED_AUDIO_EXTENSIONS'])
    })

@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    """Upload and validate audio file"""
    # Import error handling
    from audio_error_handling import (
        AudioProcessingError, 
        AudioErrorType, 
        validate_audio_file, 
        validate_audio_content,
        detect_speech_activity,
        handle_audio_errors
    )
    
    @handle_audio_errors()
    def process_audio_upload():
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AudioProcessingError(
                AudioErrorType.SYSTEM_UNAVAILABLE,
                'Audio alignment system not available'
            )
            
        # Check if file was uploaded
        if 'audio' not in request.files:
            raise AudioProcessingError(
                AudioErrorType.UPLOAD_ERROR,
                'No audio file provided'
            )
        
        file = request.files['audio']
        
        # Check if this is an ElevenLabs file and we have a pre-processed version
        optimized_elevenlabs_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
        is_elevenlabs = "ElevenLabs" in file.filename
        use_optimized = is_elevenlabs and os.path.exists(optimized_elevenlabs_path)
        
        if is_elevenlabs:
            print(f"⚠️ ElevenLabs audio file detected: {file.filename}")
            if use_optimized:
                print(f"✅ Using pre-processed optimized version for better alignment")
        
        # Validate file
        validate_audio_file(file)
        
        # Generate unique filename
        timestamp = int(time.time())
        safe_filename = secure_filename(file.filename)
        unique_filename = f"{timestamp}_{safe_filename}"
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], unique_filename)
        
        try:
            # Save file
            file.save(audio_path)
            
            # Use the optimized version for processing if available for ElevenLabs audio
            processing_path = optimized_elevenlabs_path if use_optimized else audio_path
            
            # Validate audio content (using optimized version if available)
            audio_metadata = validate_audio_content(processing_path)
            
            # Detect speech in the audio (using optimized version if available)
            speech_info = detect_speech_activity(processing_path)
            
            # Get basic audio info with our audio aligner
            aligner = get_audio_aligner()
            if not aligner:
                raise AudioProcessingError(
                    AudioErrorType.SYSTEM_UNAVAILABLE,
                    'Audio aligner not initialized'
                )
            
            # Use the optimized version for preprocessing if available
            audio_data, sample_rate = aligner.preprocess_audio(processing_path)
            
            audio_info = {
                'filename': unique_filename,
                'original_filename': file.filename,
                'path': audio_path,
                'duration_ms': audio_metadata['duration_ms'],
                'sample_rate': sample_rate,
                'samples': len(audio_data),
                'speech_info': speech_info,
                'is_elevenlabs': is_elevenlabs,
                'using_optimized': use_optimized,
                'processing_path': processing_path
            }
        except Exception as e:
            # Clean up on error
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Re-raise as AudioProcessingError if not already
            if not isinstance(e, AudioProcessingError):
                raise AudioProcessingError(
                    AudioErrorType.PROCESSING_TIMEOUT,
                    f'Audio processing failed: {str(e)}',
                    {'error': str(e)}
                )
            raise
        
        return jsonify({
            'success': True,
            'audio': audio_info,
            'message': 'Audio uploaded and validated successfully'
        })
    
    # Call the wrapped function
    return process_audio_upload()

@app.route('/api/audio/align', methods=['POST'])
def align_audio():
    """Align audio with text to generate timing sequence"""
    # Import error handling
    from audio_error_handling import (
        AudioProcessingError, 
        AudioErrorType, 
        handle_audio_errors,
        with_timeout,
        AudioFallbackHandler
    )
    
    @handle_audio_errors(fallback_handler=AudioFallbackHandler.fallback_to_manual_timing)
    def process_audio_alignment():
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AudioProcessingError(
                AudioErrorType.SYSTEM_UNAVAILABLE,
                'Audio alignment system not available'
            )
            
        data = request.get_json()
        if not data:
            raise AudioProcessingError(
                AudioErrorType.UPLOAD_ERROR,
                'No JSON data provided'
            )
            
        audio_filename = data.get('filename')
        text = data.get('text', '')
        language = data.get('language', 'pt-BR')  # Default to Portuguese
        
        if not audio_filename:
            raise AudioProcessingError(
                AudioErrorType.UPLOAD_ERROR,
                'No audio filename provided'
            )
            
        if not text.strip():
            raise AudioProcessingError(
                AudioErrorType.ALIGNMENT_FAILED,
                'No text provided for alignment'
            )
        
        # Check if audio file exists
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        if not os.path.exists(audio_path):
            raise AudioProcessingError(
                AudioErrorType.UPLOAD_ERROR,
                'Audio file not found',
                {'filename': audio_filename}
            )
            
        # Check if this is an ElevenLabs file and we have a pre-processed version
        is_elevenlabs = "ElevenLabs" in audio_filename
        optimized_elevenlabs_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
        use_optimized = is_elevenlabs and os.path.exists(optimized_elevenlabs_path)
        
        # Use optimized version if available for ElevenLabs audio
        processing_path = optimized_elevenlabs_path if use_optimized else audio_path
        
        if is_elevenlabs:
            print(f"⚠️ ElevenLabs audio file detected in alignment: {audio_filename}")
            if use_optimized:
                print(f"✅ Using pre-processed optimized version for better alignment")
                print(f"   Original: {audio_path}")
                print(f"   Optimized: {optimized_elevenlabs_path}")
        
        # Get aligner and process
        aligner = get_audio_aligner()
        if not aligner:
            raise AudioProcessingError(
                AudioErrorType.SYSTEM_UNAVAILABLE,
                'Audio aligner not available'
            )
        
        # Perform alignment with timeout
        @with_timeout(timeout_seconds=300)  # Allow up to 5 minutes for alignment (increased from 180)
        def run_alignment():
            print(f"🎵 Starting audio alignment for: {audio_filename}")
            print(f"📝 Text: {text[:100]}...")
            print(f"⏳ First alignment may take longer as models are downloaded...")
            
            try:
                # Call the alignment function with the appropriate audio file
                alignment_result = aligner.align_audio_to_text(processing_path, text, language=language)
                
                if not alignment_result:
                    raise AudioProcessingError(
                        AudioErrorType.ALIGNMENT_FAILED,
                        'Alignment failed - no result returned',
                        {'text': text[:100]}
                    )
                
                # Converter o objeto AlignmentResult para dicionário
                result_dict = {
                    'success': True,
                    'language': alignment_result.language,
                    'sample_rate': alignment_result.sample_rate,
                    'used_optimized': use_optimized if is_elevenlabs else False,
                    'tokens': [
                        {
                            'type': token.type.value,
                            'text': token.text,
                            'viseme': token.viseme,
                            'start_ms': token.start_ms,
                            'end_ms': token.end_ms,
                            'confidence': token.confidence,
                            'lang': token.lang
                        }
                        for token in alignment_result.tokens
                    ],
                    'stats': {
                        'audio_ms': alignment_result.stats.audio_ms,
                        'drift_ms': alignment_result.stats.drift_ms,
                        'unaligned_count': alignment_result.stats.unaligned_count,
                        'avg_confidence': alignment_result.stats.avg_confidence,
                        'pause_count': alignment_result.stats.pause_count
                    },
                    'total_duration_ms': alignment_result.stats.audio_ms
                }
                
                return result_dict
            except Exception as e:
                print(f"❌ Alignment error: {e}")
                raise AudioProcessingError(
                    AudioErrorType.ALIGNMENT_FAILED,
                    str(e),
                    {'text': text[:100]}
                )
            
        # Run alignment with timeout
        alignment_result = run_alignment()
        
        # Convert alignment tokens to sequence format
        tokens = alignment_result.get('tokens', [])
        sequence = []
        
        for token in tokens:
            # Os tokens já são dicionários devido à nossa conversão acima
            token_dict = token.copy() if isinstance(token, dict) else token
            
            # Adicionar duração se não estiver presente
            if isinstance(token_dict, dict) and 'start_ms' in token_dict and 'end_ms' in token_dict and 'duration_ms' not in token_dict:
                token_dict['duration_ms'] = token_dict['end_ms'] - token_dict['start_ms']
                
            sequence.append(token_dict)
        
        # Update current project with audio-driven sequence
        app_state['current_project']['text'] = text
        app_state['current_project']['audio_alignment'] = {
            'filename': audio_filename,
            'alignment_method': alignment_result.get('method', 'unknown'),
            'total_duration_ms': alignment_result.get('total_duration_ms', 0),
            'confidence_score': alignment_result.get('confidence_score', 0.0),
            'created_at': datetime.now().isoformat()
        }
        
        print(f"✅ Audio alignment completed: {len(sequence)} tokens generated")
        
        # Add a special message if using optimized ElevenLabs audio
        success_message = 'Audio alignment completed successfully'
        if is_elevenlabs and use_optimized:
            success_message = 'Audio alignment completed successfully using optimized ElevenLabs audio'
        
        return jsonify({
            'success': True,
            'alignment': alignment_result,
            'sequence': sequence,
            'stats': {
                'total_tokens': len(sequence),
                'word_tokens': len([t for t in sequence if t.get('type') == 'word']),
                'gap_tokens': len([t for t in sequence if t.get('type') == 'gap']),
                'total_duration_ms': alignment_result.get('total_duration_ms', 0),
                'method': alignment_result.get('method', 'energy-based'),
                'is_elevenlabs': is_elevenlabs,
                'used_optimized': use_optimized if is_elevenlabs else False
            },
            'message': success_message
        })
    
    # Call the wrapped function
    return process_audio_alignment()

@app.route('/api/sequence/build-from-audio', methods=['POST'])
def build_sequence_from_audio():
    """Build animation sequence using audio timing"""
    # Import error handling
    from audio_error_handling import (
        AudioProcessingError, 
        AudioErrorType, 
        AudioFallbackHandler
    )
    
    def process_audio_sequence_building():
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False, 
                'error': 'No JSON data provided',
                'error_info': {'type': 'UPLOAD_ERROR'}
            }), 400
            
        # Extract required parameters
        audio_filename = data.get('audio_filename')
        text = data.get('text', '')
        alignment_tokens = data.get('alignment_tokens', [])
        
        # Validate parameters
        if not audio_filename:
            return jsonify({
                'success': False, 
                'error': 'No audio filename provided',
                'error_info': {'type': 'UPLOAD_ERROR', 'parameter': 'audio_filename'}
            }), 400
            
        if not text.strip():
            return jsonify({
                'success': False, 
                'error': 'No text provided for alignment',
                'error_info': {'type': 'ALIGNMENT_FAILED', 'parameter': 'text'}
            }), 400
            
        if not alignment_tokens:
            return jsonify({
                'success': False, 
                'error': 'No alignment tokens provided',
                'error_info': {'type': 'ALIGNMENT_FAILED', 'parameter': 'alignment_tokens'}
            }), 400
        
        # Check if audio file exists
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        if not os.path.exists(audio_path):
            return jsonify({
                'success': False, 
                'error': 'Audio file not found',
                'error_info': {'type': 'UPLOAD_ERROR', 'filename': audio_filename}
            }), 400
        
        # Process alignment tokens to build sequence
        project = app_state['current_project']
        letter_map = project['letter_map']
        settings = project['settings']
        fallback_image = project['fallback_image'] or None
        
        try:
            # Calculate timing based on alignment tokens
            sequence = []
            
            # Process each token to create frame entries
            for token in alignment_tokens:
                token_type = token.get('type')
                token_text = token.get('text', '')
                token_viseme = token.get('viseme', '')
                start_ms = token.get('start_ms', 0)
                end_ms = token.get('end_ms', 0)
                duration_ms = end_ms - start_ms if end_ms > start_ms else settings['frame_duration']
                
                if token_type == 'word':
                    # Check if token has text content
                    if not token_text:
                        # If no text is available in the token but we have a viseme, use that for animation
                        if token_viseme and token_viseme != 'neutral':
                            # Map the viseme back to a character
                            viseme_to_char = {
                                'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
                                'BMP': 'M', 'FV': 'F', 'L': 'L', 'TH': 'T',
                                'R': 'R', 'CDGKNSTXYZ': 'T', 'QW': 'Q'
                            }
                            # Find the character that corresponds to the viseme
                            char_to_use = next((k for k, v in viseme_to_char.items() if token_viseme == v), 'A')
                            
                            sequence.append({
                                'char': char_to_use,
                                'img': letter_map.get(char_to_use, fallback_image),
                                'ms': duration_ms,
                                'audio_start': start_ms,
                                'audio_end': end_ms,
                                'source': 'audio_alignment_viseme'
                            })
                        else:
                            # If we have neither text nor viseme, add a neutral frame
                            if 'A' in letter_map:
                                sequence.append({
                                    'char': 'A',  # Default to 'A' viseme as fallback
                                    'img': letter_map.get('A'),
                                    'ms': duration_ms,
                                    'audio_start': start_ms,
                                    'audio_end': end_ms,
                                    'source': 'audio_alignment_fallback'
                                })
                            else:
                                # No 'A' in letter map, use global fallback
                                sequence.append({
                                    'char': 'A',
                                    'img': fallback_image,
                                    'fallback_img': fallback_image,
                                    'ms': duration_ms,
                                    'audio_start': start_ms,
                                    'audio_end': end_ms,
                                    'source': 'audio_alignment_fallback',
                                    'is_symbol_fallback': True
                                })
                    else:
                        # Process each character in the word normally when text is available
                        for char in token_text.upper():
                            if char in letter_map or char.isalpha():
                                # Calculate proportional duration
                                char_duration = max(40, duration_ms // max(1, len(token_text)))
                                
                                # Check if character is in letter map
                                if char in letter_map:
                                    sequence.append({
                                        'char': char,
                                        'img': letter_map.get(char),
                                        'ms': char_duration,
                                        'audio_start': start_ms,
                                        'audio_end': end_ms,
                                        'source': 'audio_alignment'
                                    })
                                else:
                                    # Character not in letter map, use fallback
                                    sequence.append({
                                        'char': char,
                                        'img': fallback_image,
                                        'fallback_img': fallback_image,
                                        'ms': char_duration,
                                        'audio_start': start_ms,
                                        'audio_end': end_ms,
                                        'source': 'audio_alignment',
                                        'is_symbol_fallback': True
                                    })
                
                elif token_type == 'gap':
                    # Add pause frame with fallback image
                    gap_duration = max(settings['pause_duration'], duration_ms)
                    sequence.append({
                        'char': ' ',
                        'img': None,  # Keep as None for UI purposes
                        'fallback_img': fallback_image,  # Add fallback image for export
                        'ms': gap_duration,
                        'audio_start': start_ms,
                        'audio_end': end_ms,
                        'is_pause': True,
                        'source': 'audio_gap'
                    })
            
            # Update app state
            app_state['current_project']['sequence'] = sequence
            app_state['current_project']['text'] = text
            app_state['current_project']['audio_file'] = audio_filename
            app_state['current_project']['timing_mode'] = 'audio_driven'
            
            return jsonify({
                'success': True,
                'sequence': sequence,
                'stats': {
                    'total_frames': len(sequence),
                    'total_duration_ms': sum(frame['ms'] for frame in sequence),
                    'source': 'audio_alignment'
                },
                'message': 'Sequence built from audio alignment successfully'
            })
            
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': f"Failed to build sequence from audio alignment: {str(e)}",
                'error_info': {'type': 'PROCESSING_TIMEOUT', 'error': str(e)}
            }), 500
    
    # Call the function
    return process_audio_sequence_building()

@app.route('/api/audio/analyze', methods=['POST'])  
def analyze_audio():
    """Analyze audio file for timing and features without full alignment"""
    try:
        if not AUDIO_ALIGNMENT_AVAILABLE:
            return jsonify({
                'success': False, 
                'error': 'Audio alignment system not available'
            }), 503
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        audio_filename = data.get('audio_filename')
        if not audio_filename:
            return jsonify({'success': False, 'error': 'No audio filename provided'}), 400
        
        # Check if audio file exists
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        if not os.path.exists(audio_path):
            return jsonify({'success': False, 'error': 'Audio file not found'}), 404
        
        # Get aligner and analyze
        aligner = get_audio_aligner()
        if not aligner:
            return jsonify({'success': False, 'error': 'Audio aligner not available'}), 500
        
        # Load and preprocess audio
        audio_data, sample_rate = aligner.preprocess_audio(audio_path)
        duration_ms = len(audio_data) * 1000 / sample_rate
        
        # Detect gaps/pauses
        gaps = aligner._detect_gaps_energy_based(audio_data, sample_rate)
        
        # Calculate basic statistics
        analysis = {
            'filename': audio_filename,
            'duration_ms': duration_ms,
            'sample_rate': sample_rate,
            'samples': len(audio_data),
            'gaps': [
                {
                    'start_ms': start_ms,
                    'end_ms': end_ms, 
                    'duration_ms': end_ms - start_ms
                }
                for start_ms, end_ms in gaps
            ],
            'speech_segments': [],
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Calculate speech segments (between gaps)
        speech_segments = []
        last_end = 0.0
        
        for gap_start, gap_end in gaps:
            if gap_start > last_end:
                speech_segments.append({
                    'start_ms': last_end,
                    'end_ms': gap_start,
                    'duration_ms': gap_start - last_end
                })
            last_end = gap_end
        
        # Add final segment if needed
        if last_end < duration_ms:
            speech_segments.append({
                'start_ms': last_end,
                'end_ms': duration_ms,
                'duration_ms': duration_ms - last_end
            })
        
        analysis['speech_segments'] = speech_segments
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'stats': {
                'total_gaps': len(gaps),
                'total_speech_segments': len(speech_segments),
                'speech_ratio': sum(seg['duration_ms'] for seg in speech_segments) / duration_ms if duration_ms > 0 else 0,
                'silence_ratio': sum(gap['duration_ms'] for gap in analysis['gaps']) / duration_ms if duration_ms > 0 else 0
            },
            'message': 'Audio analysis completed successfully'
        })
        
    except Exception as e:
        print(f"❌ Audio analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio/markers', methods=['POST'])
def get_audio_markers():
    """Get timing markers for audio playback synchronization"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    alignment = data.get('alignment')
    if not alignment:
        return jsonify({'success': False, 'error': 'No alignment provided'}), 400
    
    # Extract tokens and audio duration
    tokens = alignment.get('tokens', [])
    audio_duration_ms = alignment.get('audio', {}).get('duration_ms', 3000)  # Default 3s
    
    # Extract word tokens only (not gaps)
    word_tokens = [t for t in tokens if t.get('type') == 'word']
    
    # Calculate marker positions as percentages
    markers = []
    for token in word_tokens:
        start_ms = token.get('start_ms', 0)
        position_percent = (start_ms / audio_duration_ms) * 100 if audio_duration_ms > 0 else 0
        
        markers.append({
            'text': token.get('text', ''),
            'position': position_percent,
            'time_ms': start_ms
        })
    
    return jsonify({
        'success': True,
        'markers': markers
    })

if __name__ == '__main__':
    print("Starting Face Sequencer Pro web server...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)