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

from flask import Flask, render_template, request, jsonify, send_file
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        
        app_state['export_tasks'][task_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': filename,
            'path': export_path,
            'error': None,
            'started_at': datetime.now()
        }
        
        # Start export in background thread
        def export_worker():
            try:
                app_state['export_tasks'][task_id]['status'] = 'processing'
                
                export_mp4(
                    seq=sequence,
                    path=export_path,
                    fps=settings['fps'],
                    crf=quality_config['crf'],
                    preset=quality_config['preset']
                )
                
                app_state['export_tasks'][task_id]['status'] = 'completed'
                app_state['export_tasks'][task_id]['progress'] = 100
            
            except Exception as e:
                app_state['export_tasks'][task_id]['status'] = 'error'
                app_state['export_tasks'][task_id]['error'] = str(e)
        
        thread = threading.Thread(target=export_worker, daemon=True)
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
        
        return send_file(task['path'], as_attachment=True, download_name=task['filename'])
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

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

if __name__ == '__main__':
    print("Starting Face Sequencer Pro web server...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)