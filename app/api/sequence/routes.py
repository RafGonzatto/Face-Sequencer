"""
Phase 3 Advanced API Endpoints - Video Editor
AI-powered optimization, batch processing, and collaborative editing endpoints.
"""

from flask import Blueprint, request, jsonify, stream_with_context, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Create Blueprint for Phase 3 API
phase3_api_bp = Blueprint('phase3_api', __name__)

from app.core.subtitles.ai_subtitle_optimizer import AISubtitleOptimizer, AIOptimizationResult
from app.core.subtitles.batch_subtitle_processor import BatchSubtitleProcessor, BatchJob
from app.services.collaborative_editor import CollaborativeSubtitleEditor, EditOperation, ConflictResolution
from app.core.subtitles.enhanced_subtitle_engine import EnhancedSubtitleEngine, SubtitleSegment

# Initialize components
ai_optimizer = AISubtitleOptimizer()
batch_processor = BatchSubtitleProcessor()
collaborative_editors: Dict[str, CollaborativeSubtitleEditor] = {}
socketio = None  # Will be set by the main app

logger = logging.getLogger(__name__)

# Create Blueprint for Phase 3 endpoints
phase3_bp = Blueprint('phase3', __name__, url_prefix='/api/v3')

def init_socketio(app_socketio):
    """Initialize SocketIO for real-time collaboration."""
    global socketio
    socketio = app_socketio

# =============================================================================
# AI-Powered Optimization Endpoints
# =============================================================================

@phase3_bp.route('/ai/optimize-subtitles', methods=['POST'])
async def optimize_subtitles_ai():
    """Advanced AI-powered subtitle optimization."""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['segments']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: segments'
            }), 400
        
        # Convert to SubtitleSegment objects
        segments = []
        for seg_data in data['segments']:
            segment = SubtitleSegment(
                id=seg_data['id'],
                text=seg_data['text'],
                start_time=seg_data['start_time'],
                end_time=seg_data['end_time'],
                confidence=seg_data.get('confidence', 1.0)
            )
            segments.append(segment)
        
        # Optimization parameters
        optimization_level = data.get('optimization_level', 'balanced')
        target_platform = data.get('target_platform', 'general')
        user_preferences = data.get('user_preferences', {})
        
        # Apply AI optimization
        result = await ai_optimizer.optimize_subtitles_ai(
            segments=segments,
            optimization_level=optimization_level,
            target_platform=target_platform,
            user_preferences=user_preferences
        )
        
        # Convert result to serializable format
        response_data = {
            'success': True,
            'optimized_segments': [
                {
                    'id': seg.id,
                    'text': seg.text,
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'confidence': seg.confidence,
                    'word_count': seg.word_count,
                    'reading_speed': seg.reading_speed,
                    'platform_optimized': seg.platform_optimized,
                    'style_overrides': seg.style_overrides
                }
                for seg in result.optimized_segments
            ],
            'optimization_metrics': {
                'optimization_score': result.optimization_score,
                'readability_improvement': result.readability_improvement,
                'timing_adjustments': result.timing_adjustments,
                'text_modifications': result.text_modifications,
                'ai_confidence': result.ai_confidence,
                'optimization_time': result.optimization_time,
                'suggestions': result.suggestions
            }
        }
        
        logger.info(f"AI optimization completed with {result.ai_confidence:.1%} confidence")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"AI optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/ai/analyze-readability', methods=['POST'])
async def analyze_readability():
    """Analyze subtitle readability and provide recommendations."""
    try:
        data = request.get_json()
        
        if 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: text'
            }), 400
        
        text = data['text']
        platform = data.get('platform', 'general')
        
        # Perform readability analysis
        analysis_result = await ai_optimizer._optimize_readability(
            [SubtitleSegment('temp', text, 0.0, 5.0)], 
            'balanced'
        )
        
        if analysis_result['results']:
            result_data = analysis_result['results'][0]
            
            return jsonify({
                'success': True,
                'readability_score': result_data['readability_score'],
                'improved_text': result_data['improved_text'],
                'improvement_made': result_data['improvement_made'],
                'confidence': analysis_result['confidence'],
                'recommendations': [
                    'Consider shorter sentences for better readability',
                    'Use simpler vocabulary when possible',
                    'Ensure proper punctuation and capitalization'
                ]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Analysis failed'
            }), 500
        
    except Exception as e:
        logger.error(f"Readability analysis failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/ai/cache-stats', methods=['GET'])
def get_ai_cache_stats():
    """Get AI optimization cache statistics."""
    try:
        stats = ai_optimizer.get_cache_stats()
        return jsonify({
            'success': True,
            'cache_stats': stats
        })
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/ai/clear-cache', methods=['POST'])
def clear_ai_cache():
    """Clear AI optimization cache."""
    try:
        ai_optimizer.clear_optimization_cache()
        return jsonify({
            'success': True,
            'message': 'AI optimization cache cleared'
        })
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# Batch Processing Endpoints
# =============================================================================

@phase3_bp.route('/batch/start-processor', methods=['POST'])
async def start_batch_processor():
    """Start the batch processing system."""
    try:
        await batch_processor.start_processing()
        return jsonify({
            'success': True,
            'message': 'Batch processor started',
            'max_workers': batch_processor.max_workers
        })
    except Exception as e:
        logger.error(f"Failed to start batch processor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/stop-processor', methods=['POST'])
async def stop_batch_processor():
    """Stop the batch processing system."""
    try:
        graceful = request.get_json().get('graceful', True) if request.is_json else True
        await batch_processor.stop_processing(graceful=graceful)
        return jsonify({
            'success': True,
            'message': 'Batch processor stopped'
        })
    except Exception as e:
        logger.error(f"Failed to stop batch processor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/submit-job', methods=['POST'])
async def submit_batch_job():
    """Submit a single job to the batch processor."""
    try:
        data = request.get_json()
        
        required_fields = ['job_type', 'input_data']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: job_type, input_data'
            }), 400
        
        job_id = await batch_processor.submit_batch_job(
            job_type=data['job_type'],
            input_data=data['input_data'],
            priority=data.get('priority', 5)
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to submit batch job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/submit-multiple-jobs', methods=['POST'])
async def submit_multiple_batch_jobs():
    """Submit multiple jobs to the batch processor."""
    try:
        data = request.get_json()
        
        if 'jobs' not in data or not isinstance(data['jobs'], list):
            return jsonify({
                'success': False,
                'error': 'Missing or invalid jobs array'
            }), 400
        
        job_ids = await batch_processor.submit_multiple_jobs(data['jobs'])
        
        return jsonify({
            'success': True,
            'job_ids': job_ids,
            'total_jobs': len(job_ids),
            'message': f'Successfully submitted {len(job_ids)} jobs'
        })
        
    except Exception as e:
        logger.error(f"Failed to submit multiple jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/process-generation', methods=['POST'])
async def process_batch_generation():
    """Process multiple videos for subtitle generation."""
    try:
        data = request.get_json()
        
        required_fields = ['video_files', 'transcripts']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: video_files, transcripts'
            }), 400
        
        batch_job_id = await batch_processor.process_batch_generation(
            video_files=data['video_files'],
            transcripts=data['transcripts'],
            options=data.get('options', {})
        )
        
        return jsonify({
            'success': True,
            'batch_job_id': batch_job_id,
            'total_videos': len(data['video_files']),
            'message': 'Batch generation started'
        })
        
    except Exception as e:
        logger.error(f"Failed to start batch generation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/process-optimization', methods=['POST'])
async def process_batch_optimization():
    """Process multiple subtitle sets for AI optimization."""
    try:
        data = request.get_json()
        
        if 'subtitle_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: subtitle_data'
            }), 400
        
        batch_job_id = await batch_processor.process_batch_optimization(
            subtitle_data=data['subtitle_data'],
            optimization_options=data.get('optimization_options', {})
        )
        
        return jsonify({
            'success': True,
            'batch_job_id': batch_job_id,
            'total_subtitles': len(data['subtitle_data']),
            'message': 'Batch optimization started'
        })
        
    except Exception as e:
        logger.error(f"Failed to start batch optimization: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/job-status/<job_id>', methods=['GET'])
async def get_batch_job_status(job_id):
    """Get status of a specific batch job."""
    try:
        status = await batch_processor.get_job_status(job_id)
        
        if status is None:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'job_status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/job-result/<job_id>', methods=['GET'])
async def get_batch_job_result(job_id):
    """Get result of a completed batch job."""
    try:
        result = await batch_processor.get_job_result(job_id)
        
        if result is None:
            return jsonify({
                'success': False,
                'error': 'Job not found or not completed'
            }), 404
        
        return jsonify({
            'success': True,
            'job_result': result
        })
        
    except Exception as e:
        logger.error(f"Failed to get job result: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/queue-status', methods=['GET'])
async def get_batch_queue_status():
    """Get current batch processing queue status."""
    try:
        status = await batch_processor.get_queue_status()
        return jsonify({
            'success': True,
            'queue_status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/cancel-job/<job_id>', methods=['POST'])
async def cancel_batch_job(job_id):
    """Cancel a batch job."""
    try:
        cancelled = await batch_processor.cancel_job(job_id)
        
        if cancelled:
            return jsonify({
                'success': True,
                'message': 'Job cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Job not found or cannot be cancelled'
            }), 404
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/batch/metrics', methods=['GET'])
async def get_batch_metrics():
    """Get detailed batch processing metrics."""
    try:
        metrics = await batch_processor.get_processing_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Failed to get batch metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# Collaborative Editing Endpoints
# =============================================================================

@phase3_bp.route('/collaborative/create-session', methods=['POST'])
async def create_collaborative_session():
    """Create a new collaborative editing session."""
    try:
        data = request.get_json()
        
        project_id = data.get('project_id')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Missing project_id'
            }), 400
        
        conflict_resolution = data.get('conflict_resolution', 'merge_automatic')
        
        # Create collaborative editor
        editor = CollaborativeSubtitleEditor(
            project_id=project_id,
            conflict_resolution=ConflictResolution(conflict_resolution)
        )
        
        collaborative_editors[project_id] = editor
        
        # Set up SocketIO callback for real-time sync
        if socketio:
            def sync_callback(event_type, data, exclude_user=None):
                socketio.emit(event_type, data, room=f'project_{project_id}', skip_sid=exclude_user)
            
            editor.add_sync_callback(sync_callback)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'conflict_resolution': conflict_resolution,
            'message': 'Collaborative session created'
        })
        
    except Exception as e:
        logger.error(f"Failed to create collaborative session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/connect/<project_id>', methods=['POST'])
async def connect_to_collaborative_session(project_id):
    """Connect a user to a collaborative editing session."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        role = data.get('role', 'editor')
        
        if not user_id or not username:
            return jsonify({
                'success': False,
                'error': 'Missing user_id or username'
            }), 400
        
        editor = collaborative_editors[project_id]
        connected = await editor.connect_user(user_id, username, role)
        
        if connected:
            # Get current project state
            project_state = await editor.get_project_state(user_id)
            
            return jsonify({
                'success': True,
                'project_state': project_state,
                'message': f'Connected as {role}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to session'
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to connect to collaborative session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/edit/<project_id>', methods=['POST'])
async def apply_collaborative_edit(project_id):
    """Apply an edit in collaborative session."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        operation = data.get('operation')
        segment_id = data.get('segment_id')
        edit_data = data.get('data', {})
        
        if not all([user_id, operation, segment_id]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: user_id, operation, segment_id'
            }), 400
        
        editor = collaborative_editors[project_id]
        result = await editor.apply_edit(
            user_id=user_id,
            operation=EditOperation(operation),
            segment_id=segment_id,
            data=edit_data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to apply collaborative edit: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/lock/<project_id>/<segment_id>', methods=['POST'])
async def lock_collaborative_segment(project_id, segment_id):
    """Lock a segment for exclusive editing."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        editor = collaborative_editors[project_id]
        locked = await editor.lock_segment(user_id, segment_id)
        
        return jsonify({
            'success': locked,
            'message': 'Segment locked' if locked else 'Failed to lock segment'
        })
        
    except Exception as e:
        logger.error(f"Failed to lock segment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/unlock/<project_id>/<segment_id>', methods=['POST'])
async def unlock_collaborative_segment(project_id, segment_id):
    """Unlock a segment."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        editor = collaborative_editors[project_id]
        unlocked = await editor.unlock_segment(user_id, segment_id)
        
        return jsonify({
            'success': unlocked,
            'message': 'Segment unlocked' if unlocked else 'Failed to unlock segment'
        })
        
    except Exception as e:
        logger.error(f"Failed to unlock segment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/create-version/<project_id>', methods=['POST'])
async def create_collaborative_version(project_id):
    """Create a new version of the collaborative project."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        description = data.get('description', 'New version')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        editor = collaborative_editors[project_id]
        version_id = await editor.create_version(user_id, description)
        
        return jsonify({
            'success': True,
            'version_id': version_id,
            'message': 'Version created successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/project-state/<project_id>', methods=['GET'])
async def get_collaborative_project_state(project_id):
    """Get current state of collaborative project."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        editor = collaborative_editors[project_id]
        project_state = await editor.get_project_state(user_id)
        
        return jsonify({
            'success': True,
            'project_state': project_state
        })
        
    except Exception as e:
        logger.error(f"Failed to get project state: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@phase3_bp.route('/collaborative/conflicts/<project_id>', methods=['GET'])
async def get_collaborative_conflicts(project_id):
    """Get pending conflicts for manual resolution."""
    try:
        if project_id not in collaborative_editors:
            return jsonify({
                'success': False,
                'error': 'Collaborative session not found'
            }), 404
        
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        editor = collaborative_editors[project_id]
        conflicts = await editor.get_conflict_queue(user_id)
        
        return jsonify({
            'success': True,
            'conflicts': conflicts
        })
        
    except Exception as e:
        logger.error(f"Failed to get conflicts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# WebSocket Events for Real-time Collaboration
# =============================================================================

def register_socketio_events(socketio_instance):
    """Register SocketIO events for real-time collaboration."""
    global socketio
    socketio = socketio_instance
    
    @socketio.on('join_project')
    def on_join_project(data):
        """Join a project room for real-time updates."""
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        
        if project_id and user_id:
            join_room(f'project_{project_id}')
            emit('joined_project', {'project_id': project_id})
            logger.info(f"User {user_id} joined project {project_id}")
    
    @socketio.on('leave_project')
    def on_leave_project(data):
        """Leave a project room."""
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        
        if project_id and user_id:
            leave_room(f'project_{project_id}')
            emit('left_project', {'project_id': project_id})
            logger.info(f"User {user_id} left project {project_id}")
    
    @socketio.on('cursor_update')
    async def on_cursor_update(data):
        """Handle cursor position updates for live collaboration."""
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        segment_id = data.get('segment_id')
        position = data.get('position')
        selection_range = data.get('selection_range')
        
        if project_id in collaborative_editors:
            editor = collaborative_editors[project_id]
            await editor.update_cursor_position(user_id, segment_id, position, selection_range)
    
    @socketio.on('disconnect')
    async def on_disconnect():
        """Handle user disconnection."""
        # In a real implementation, you'd track user sessions
        # and disconnect them from collaborative sessions
        logger.info("User disconnected from WebSocket")

# Add blueprint registration function
def register_phase3_blueprint(app):
    """Register the Phase 3 blueprint with the Flask app."""
    app.register_blueprint(phase3_bp)