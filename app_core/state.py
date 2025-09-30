"""State helpers extracted from app.py"""
from __future__ import annotations
from config import config

DEFAULT_PROJECT_SETTINGS = {
    'frame_duration': config.project_defaults.frame_duration(),
    'pause_duration': config.project_defaults.pause_duration(),
    'fps': config.project_defaults.fps(),
    'quality': config.project_defaults.quality(),
    'preset': config.project_defaults.preset(),
}

def create_default_project_state():
    return {
        'name': 'New Project',
        'folder_path': '',
        'fallback_image': '',
        'pause_image': '',
        'text': '',
        'sequence': [],
        'letter_map': {},
        'special_tokens': {},
        'audio_alignment': None,
        'audio_file': None,
        'timing_mode': 'manual',
        'frame_states': [],
        'last_alignment': None,
        'fps': config.project_defaults.fps(),
        'settings': DEFAULT_PROJECT_SETTINGS.copy(),
    }
