# project_templates.py - Project Templates and Management
import json
import os
from datetime import datetime

class ProjectTemplates:
    """Manage project templates and presets"""
    
    TEMPLATES = {
        "basic_alphabet": {
            "name": "Basic Alphabet Animation",
            "description": "Simple alphabet animation with standard settings",
            "settings": {
                "frame_duration": 80,
                "pause_duration": 120,
                "fps": 30,
                "quality": 18,
                "preset": "medium"
            },
            "sample_text": "HELLO WORLD",
            "recommended_images": [
                "A.png", "B.png", "C.png", "D.png", "E.png", "F.png", "G.png",
                "H.png", "I.png", "J.png", "K.png", "L.png", "M.png", "N.png",
                "O.png", "P.png", "Q.png", "R.png", "S.png", "T.png", "U.png",
                "V.png", "W.png", "X.png", "Y.png", "Z.png"
            ]
        },
        
        "lip_sync": {
            "name": "Lip Sync Animation",
            "description": "Optimized for realistic lip synchronization",
            "settings": {
                "frame_duration": 60,
                "pause_duration": 100,
                "fps": 30,
                "quality": 14,
                "preset": "slow"
            },
            "sample_text": "The quick brown fox jumps over the lazy dog",
            "recommended_images": [
                "mouth_A.png", "mouth_E.png", "mouth_I.png", "mouth_O.png", "mouth_U.png",
                "mouth_M.png", "mouth_B.png", "mouth_P.png", "mouth_F.png", "mouth_V.png",
                "mouth_T.png", "mouth_D.png", "mouth_N.png", "mouth_L.png", "mouth_R.png",
                "mouth_S.png", "mouth_Z.png", "mouth_TH.png", "mouth_SH.png", "mouth_CH.png"
            ]
        },
        
        "fast_animation": {
            "name": "Fast Animation",
            "description": "Quick animation with shorter frame durations",
            "settings": {
                "frame_duration": 40,
                "pause_duration": 60,
                "fps": 60,
                "quality": 20,
                "preset": "fast"
            },
            "sample_text": "FAST TEXT ANIMATION",
            "recommended_images": [
                "fast_A.png", "fast_B.png", "fast_C.png", "fast_D.png", "fast_E.png"
            ]
        },
        
        "high_quality": {
            "name": "High Quality Export",
            "description": "Maximum quality settings for professional output",
            "settings": {
                "frame_duration": 100,
                "pause_duration": 150,
                "fps": 30,
                "quality": 12,
                "preset": "slow"
            },
            "sample_text": "PROFESSIONAL ANIMATION",
            "recommended_images": [
                "hq_face_A.png", "hq_face_B.png", "hq_face_C.png"
            ]
        }
    }
    
    @classmethod
    def get_template(cls, template_name):
        """Get a specific template"""
        return cls.TEMPLATES.get(template_name)
    
    @classmethod
    def list_templates(cls):
        """List all available templates"""
        return {
            name: {
                "name": template["name"],
                "description": template["description"]
            }
            for name, template in cls.TEMPLATES.items()
        }
    
    @classmethod
    def apply_template(cls, template_name, project_state):
        """Apply template settings to project state"""
        template = cls.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Apply template settings
        project_state['settings'].update(template['settings'])
        project_state['text'] = template['sample_text']
        project_state['name'] = f"New Project - {template['name']}"
        
        return project_state

class ProjectManager:
    """Manage project saving, loading, and recent projects"""
    
    def __init__(self, projects_dir="projects"):
        self.projects_dir = projects_dir
        os.makedirs(projects_dir, exist_ok=True)
        self.recent_projects_file = os.path.join(projects_dir, "recent.json")
    
    def save_project(self, project_data, filename=None):
        """Save project to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"project_{timestamp}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        project_path = os.path.join(self.projects_dir, filename)
        
        # Add metadata
        project_data['saved_at'] = datetime.now().isoformat()
        project_data['version'] = '2.0'
        project_data['filename'] = filename
        
        # Save project file
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        # Update recent projects
        self._add_to_recent(project_path, project_data)
        
        return project_path
    
    def load_project(self, project_path):
        """Load project from file"""
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project file not found: {project_path}")
        
        with open(project_path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Update recent projects
        self._add_to_recent(project_path, project_data)
        
        return project_data
    
    def get_recent_projects(self, limit=10):
        """Get list of recent projects"""
        try:
            if os.path.exists(self.recent_projects_file):
                with open(self.recent_projects_file, 'r', encoding='utf-8') as f:
                    recent = json.load(f)
                
                # Filter out non-existent files and limit results
                valid_recent = []
                for project in recent:
                    if os.path.exists(project['path']):
                        valid_recent.append(project)
                    if len(valid_recent) >= limit:
                        break
                
                return valid_recent
        except Exception:
            pass
        
        return []
    
    def _add_to_recent(self, project_path, project_data):
        """Add project to recent projects list"""
        try:
            recent_projects = []
            
            # Load existing recent projects
            if os.path.exists(self.recent_projects_file):
                with open(self.recent_projects_file, 'r', encoding='utf-8') as f:
                    recent_projects = json.load(f)
            
            # Create new project entry
            project_entry = {
                'path': project_path,
                'name': project_data.get('name', 'Untitled Project'),
                'last_opened': datetime.now().isoformat(),
                'text_preview': project_data.get('text', '')[:50] + ('...' if len(project_data.get('text', '')) > 50 else ''),
                'frame_count': len(project_data.get('sequence', [])),
                'folder_path': project_data.get('folder_path', '')
            }
            
            # Remove if already exists (to update position)
            recent_projects = [p for p in recent_projects if p['path'] != project_path]
            
            # Add to beginning
            recent_projects.insert(0, project_entry)
            
            # Keep only last 20 projects
            recent_projects = recent_projects[:20]
            
            # Save updated recent projects
            with open(self.recent_projects_file, 'w', encoding='utf-8') as f:
                json.dump(recent_projects, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"Error updating recent projects: {e}")
    
    def delete_project(self, project_path):
        """Delete project file and remove from recent"""
        if os.path.exists(project_path):
            os.remove(project_path)
        
        # Remove from recent projects
        try:
            if os.path.exists(self.recent_projects_file):
                with open(self.recent_projects_file, 'r', encoding='utf-8') as f:
                    recent_projects = json.load(f)
                
                # Filter out the deleted project
                recent_projects = [p for p in recent_projects if p['path'] != project_path]
                
                with open(self.recent_projects_file, 'w', encoding='utf-8') as f:
                    json.dump(recent_projects, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def export_project_settings(self, project_data):
        """Export only project settings as a template"""
        template_data = {
            'name': f"{project_data.get('name', 'Custom')} Template",
            'description': f"Custom template created from {project_data.get('name', 'project')}",
            'settings': project_data.get('settings', {}),
            'created_at': datetime.now().isoformat(),
            'type': 'custom_template'
        }
        
        return template_data