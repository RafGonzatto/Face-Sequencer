"""
Collaborative Subtitle Editing System - Phase 3 Implementation
Real-time collaborative editing with conflict resolution, version control, and live synchronization.
"""

import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
import logging
from enum import Enum
import hashlib
import copy

logger = logging.getLogger(__name__)

class EditOperation(Enum):
    """Types of edit operations."""
    INSERT = "insert"
    DELETE = "delete" 
    MODIFY = "modify"
    MOVE = "move"
    SPLIT = "split"
    MERGE = "merge"

@dataclass
class EditAction:
    """Represents a single edit action."""
    action_id: str
    operation: EditOperation
    segment_id: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    applied: bool = False
    conflicts_with: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'action_id': self.action_id,
            'operation': self.operation.value,
            'segment_id': self.segment_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'applied': self.applied,
            'conflicts_with': self.conflicts_with
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditAction':
        """Create from dictionary."""
        return cls(
            action_id=data['action_id'],
            operation=EditOperation(data['operation']),
            segment_id=data['segment_id'],
            user_id=data['user_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data['data'],
            applied=data.get('applied', False),
            conflicts_with=data.get('conflicts_with', [])
        )

@dataclass
class CollaborativeUser:
    """Represents a collaborative editing user."""
    user_id: str
    username: str
    role: str  # 'editor', 'reviewer', 'viewer'
    connected_at: datetime
    last_activity: datetime
    current_segment: Optional[str] = None
    cursor_position: Optional[int] = None
    selection_range: Optional[Dict[str, int]] = None
    online: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'connected_at': self.connected_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'current_segment': self.current_segment,
            'cursor_position': self.cursor_position,
            'selection_range': self.selection_range,
            'online': self.online
        }

@dataclass
class ProjectVersion:
    """Represents a version of the collaborative project."""
    version_id: str
    created_by: str
    created_at: datetime
    description: str
    subtitle_data: Dict[str, Any]
    changes_from_previous: List[str]  # List of action IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'version_id': self.version_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'description': self.description,
            'subtitle_data': self.subtitle_data,
            'changes_from_previous': self.changes_from_previous
        }

class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    MERGE_AUTOMATIC = "merge_automatic"
    PREFER_LATEST = "prefer_latest"
    PREFER_ROLE_PRIORITY = "prefer_role_priority"
    MANUAL_REVIEW = "manual_review"

class CollaborativeSubtitleEditor:
    """
    Real-time collaborative subtitle editing system.
    Supports multiple users, conflict resolution, and version control.
    """
    
    def __init__(self, project_id: str, conflict_resolution: ConflictResolution = ConflictResolution.MERGE_AUTOMATIC):
        self.project_id = project_id
        self.conflict_resolution = conflict_resolution
        
        # Project state
        self.current_subtitle_data: Dict[str, Any] = {}
        self.edit_history: List[EditAction] = []
        self.version_history: List[ProjectVersion] = []
        
        # Collaborative state
        self.connected_users: Dict[str, CollaborativeUser] = {}
        self.active_locks: Dict[str, str] = {}  # segment_id -> user_id
        self.pending_changes: List[EditAction] = []
        
        # Real-time synchronization
        self.sync_callbacks: List[Callable] = []
        self.change_buffer: Dict[str, EditAction] = {}
        self.last_sync_time = datetime.now()
        
        # Conflict management
        self.conflict_queue: List[EditAction] = []
        self.auto_save_interval = 30  # seconds
        
        logger.info(f"Collaborative editor initialized for project {project_id}")
    
    async def connect_user(self, user_id: str, username: str, role: str = 'editor') -> bool:
        """Connect a user to the collaborative session."""
        try:
            user = CollaborativeUser(
                user_id=user_id,
                username=username,
                role=role,
                connected_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            self.connected_users[user_id] = user
            
            # Notify other users
            await self._broadcast_user_event('user_connected', {
                'user': user.to_dict(),
                'total_users': len(self.connected_users)
            }, exclude_user=user_id)
            
            logger.info(f"User {username} ({user_id}) connected with role {role}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect user {user_id}: {e}")
            return False
    
    async def disconnect_user(self, user_id: str) -> bool:
        """Disconnect a user from the collaborative session."""
        if user_id not in self.connected_users:
            return False
        
        try:
            user = self.connected_users[user_id]
            user.online = False
            
            # Release any locks held by this user
            segments_to_unlock = [seg_id for seg_id, lock_user in self.active_locks.items() if lock_user == user_id]
            for segment_id in segments_to_unlock:
                del self.active_locks[segment_id]
            
            # Remove user after a delay (in case of reconnection)
            asyncio.create_task(self._delayed_user_removal(user_id, 30))
            
            # Notify other users
            await self._broadcast_user_event('user_disconnected', {
                'user_id': user_id,
                'username': user.username,
                'unlocked_segments': segments_to_unlock
            }, exclude_user=user_id)
            
            logger.info(f"User {user.username} ({user_id}) disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect user {user_id}: {e}")
            return False
    
    async def apply_edit(self, user_id: str, operation: EditOperation, segment_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply an edit operation to the subtitle project.
        
        Args:
            user_id: ID of the user making the edit
            operation: Type of edit operation
            segment_id: ID of the segment being edited
            data: Edit-specific data
            
        Returns:
            Result of the edit operation
        """
        if user_id not in self.connected_users:
            return {'success': False, 'error': 'User not connected'}
        
        user = self.connected_users[user_id]
        
        # Check permissions
        if not self._check_edit_permission(user, operation, segment_id):
            return {'success': False, 'error': 'Insufficient permissions'}
        
        # Check for locks
        if segment_id in self.active_locks and self.active_locks[segment_id] != user_id:
            lock_user = self.connected_users.get(self.active_locks[segment_id])
            return {
                'success': False, 
                'error': f'Segment locked by {lock_user.username if lock_user else "another user"}'
            }
        
        # Create edit action
        action = EditAction(
            action_id=str(uuid.uuid4()),
            operation=operation,
            segment_id=segment_id,
            user_id=user_id,
            timestamp=datetime.now(),
            data=data
        )
        
        try:
            # Check for conflicts
            conflicts = await self._detect_conflicts(action)
            if conflicts:
                action.conflicts_with = [c.action_id for c in conflicts]
                
                # Handle conflict based on resolution strategy
                resolution_result = await self._resolve_conflicts(action, conflicts)
                if not resolution_result['success']:
                    return resolution_result
            
            # Apply the edit
            apply_result = await self._apply_edit_action(action)
            if apply_result['success']:
                # Add to history
                self.edit_history.append(action)
                action.applied = True
                
                # Update user activity
                user.last_activity = datetime.now()
                
                # Broadcast to other users
                await self._broadcast_edit(action)
                
                # Check if auto-save is needed
                await self._check_auto_save()
                
                logger.info(f"Edit applied: {operation.value} on {segment_id} by {user.username}")
            
            return apply_result
            
        except Exception as e:
            logger.error(f"Failed to apply edit: {e}")
            return {'success': False, 'error': str(e)}
    
    async def lock_segment(self, user_id: str, segment_id: str) -> bool:
        """Lock a segment for exclusive editing."""
        if user_id not in self.connected_users:
            return False
        
        if segment_id in self.active_locks:
            return self.active_locks[segment_id] == user_id
        
        self.active_locks[segment_id] = user_id
        user = self.connected_users[user_id]
        user.current_segment = segment_id
        
        # Broadcast lock to other users
        await self._broadcast_user_event('segment_locked', {
            'segment_id': segment_id,
            'locked_by': user.username,
            'user_id': user_id
        }, exclude_user=user_id)
        
        return True
    
    async def unlock_segment(self, user_id: str, segment_id: str) -> bool:
        """Unlock a segment."""
        if segment_id not in self.active_locks or self.active_locks[segment_id] != user_id:
            return False
        
        del self.active_locks[segment_id]
        
        if user_id in self.connected_users:
            user = self.connected_users[user_id]
            user.current_segment = None
            
            # Broadcast unlock to other users
            await self._broadcast_user_event('segment_unlocked', {
                'segment_id': segment_id,
                'unlocked_by': user.username
            }, exclude_user=user_id)
        
        return True
    
    async def update_cursor_position(self, user_id: str, segment_id: str, position: int, selection_range: Optional[Dict[str, int]] = None):
        """Update user's cursor position for live collaboration."""
        if user_id not in self.connected_users:
            return
        
        user = self.connected_users[user_id]
        user.current_segment = segment_id
        user.cursor_position = position
        user.selection_range = selection_range
        user.last_activity = datetime.now()
        
        # Broadcast cursor update to other users
        await self._broadcast_user_event('cursor_update', {
            'user_id': user_id,
            'username': user.username,
            'segment_id': segment_id,
            'position': position,
            'selection_range': selection_range
        }, exclude_user=user_id)
    
    async def create_version(self, user_id: str, description: str) -> str:
        """Create a new version of the project."""
        if user_id not in self.connected_users:
            raise ValueError("User not connected")
        
        user = self.connected_users[user_id]
        if user.role not in ['editor', 'admin']:
            raise ValueError("Insufficient permissions to create version")
        
        version_id = str(uuid.uuid4())
        
        # Get changes since last version
        last_version_time = self.version_history[-1].created_at if self.version_history else datetime.min
        changes_since_last = [
            action.action_id for action in self.edit_history 
            if action.timestamp > last_version_time and action.applied
        ]
        
        version = ProjectVersion(
            version_id=version_id,
            created_by=user_id,
            created_at=datetime.now(),
            description=description,
            subtitle_data=copy.deepcopy(self.current_subtitle_data),
            changes_from_previous=changes_since_last
        )
        
        self.version_history.append(version)
        
        # Broadcast version creation
        await self._broadcast_user_event('version_created', {
            'version': version.to_dict(),
            'created_by': user.username
        })
        
        logger.info(f"Version {version_id} created by {user.username}: {description}")
        return version_id
    
    async def revert_to_version(self, user_id: str, version_id: str) -> bool:
        """Revert project to a specific version."""
        if user_id not in self.connected_users:
            return False
        
        user = self.connected_users[user_id]
        if user.role != 'admin':
            return False  # Only admins can revert versions
        
        # Find the version
        target_version = None
        for version in self.version_history:
            if version.version_id == version_id:
                target_version = version
                break
        
        if not target_version:
            return False
        
        # Revert the data
        self.current_subtitle_data = copy.deepcopy(target_version.subtitle_data)
        
        # Create revert action
        revert_action = EditAction(
            action_id=str(uuid.uuid4()),
            operation=EditOperation.MODIFY,
            segment_id='project',
            user_id=user_id,
            timestamp=datetime.now(),
            data={'reverted_to': version_id}
        )
        revert_action.applied = True
        self.edit_history.append(revert_action)
        
        # Broadcast revert
        await self._broadcast_user_event('project_reverted', {
            'version_id': version_id,
            'reverted_by': user.username,
            'subtitle_data': self.current_subtitle_data
        })
        
        logger.info(f"Project reverted to version {version_id} by {user.username}")
        return True
    
    async def get_project_state(self, user_id: str) -> Dict[str, Any]:
        """Get current project state for a user."""
        if user_id not in self.connected_users:
            return {}
        
        return {
            'project_id': self.project_id,
            'subtitle_data': self.current_subtitle_data,
            'connected_users': [user.to_dict() for user in self.connected_users.values() if user.online],
            'active_locks': {
                segment_id: self.connected_users[lock_user].username 
                for segment_id, lock_user in self.active_locks.items()
                if lock_user in self.connected_users
            },
            'version_history': [v.to_dict() for v in self.version_history[-10:]],  # Last 10 versions
            'edit_history_count': len(self.edit_history),
            'last_modified': max(
                (action.timestamp for action in self.edit_history if action.applied),
                default=datetime.now()
            ).isoformat()
        }
    
    async def get_conflict_queue(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending conflicts that need manual resolution."""
        if user_id not in self.connected_users:
            return []
        
        user = self.connected_users[user_id]
        if user.role not in ['editor', 'admin']:
            return []
        
        return [action.to_dict() for action in self.conflict_queue]
    
    async def resolve_conflict_manually(self, user_id: str, action_id: str, resolution: str) -> bool:
        """Manually resolve a conflict."""
        if user_id not in self.connected_users:
            return False
        
        user = self.connected_users[user_id]
        if user.role not in ['editor', 'admin']:
            return False
        
        # Find the conflicted action
        conflict_action = None
        for action in self.conflict_queue:
            if action.action_id == action_id:
                conflict_action = action
                break
        
        if not conflict_action:
            return False
        
        # Apply resolution
        if resolution == 'accept':
            apply_result = await self._apply_edit_action(conflict_action)
            if apply_result['success']:
                conflict_action.applied = True
                self.edit_history.append(conflict_action)
                self.conflict_queue.remove(conflict_action)
                await self._broadcast_edit(conflict_action)
                return True
        elif resolution == 'reject':
            self.conflict_queue.remove(conflict_action)
            return True
        
        return False
    
    async def _detect_conflicts(self, action: EditAction) -> List[EditAction]:
        """Detect conflicts with pending or recent actions."""
        conflicts = []
        
        # Check against recent actions (last 5 minutes)
        recent_threshold = datetime.now() - timedelta(minutes=5)
        for existing_action in self.edit_history:
            if (existing_action.timestamp > recent_threshold and 
                existing_action.segment_id == action.segment_id and
                existing_action.user_id != action.user_id and
                existing_action.applied):
                
                # Check if operations conflict
                if self._operations_conflict(action, existing_action):
                    conflicts.append(existing_action)
        
        # Check against pending changes
        for pending_action in self.pending_changes:
            if (pending_action.segment_id == action.segment_id and
                pending_action.user_id != action.user_id):
                
                if self._operations_conflict(action, pending_action):
                    conflicts.append(pending_action)
        
        return conflicts
    
    def _operations_conflict(self, action1: EditAction, action2: EditAction) -> bool:
        """Check if two operations conflict with each other."""
        # Same segment, different users = potential conflict
        if action1.segment_id != action2.segment_id or action1.user_id == action2.user_id:
            return False
        
        # Text modifications on same segment always conflict
        if (action1.operation in [EditOperation.MODIFY, EditOperation.DELETE] and
            action2.operation in [EditOperation.MODIFY, EditOperation.DELETE]):
            return True
        
        # Timing changes can conflict
        if ('start_time' in action1.data or 'end_time' in action1.data) and \
           ('start_time' in action2.data or 'end_time' in action2.data):
            return True
        
        return False
    
    async def _resolve_conflicts(self, action: EditAction, conflicts: List[EditAction]) -> Dict[str, Any]:
        """Resolve conflicts based on the configured strategy."""
        
        if self.conflict_resolution == ConflictResolution.MERGE_AUTOMATIC:
            # Try to merge changes automatically
            merge_result = await self._attempt_automatic_merge(action, conflicts)
            if merge_result['success']:
                return merge_result
        
        elif self.conflict_resolution == ConflictResolution.PREFER_LATEST:
            # Always accept the latest change
            return {'success': True, 'message': 'Accepting latest change'}
        
        elif self.conflict_resolution == ConflictResolution.PREFER_ROLE_PRIORITY:
            # Resolve based on user roles
            action_user = self.connected_users[action.user_id]
            role_priority = {'admin': 3, 'editor': 2, 'reviewer': 1, 'viewer': 0}
            
            action_priority = role_priority.get(action_user.role, 0)
            for conflict in conflicts:
                if conflict.user_id in self.connected_users:
                    conflict_user = self.connected_users[conflict.user_id]
                    conflict_priority = role_priority.get(conflict_user.role, 0)
                    if conflict_priority >= action_priority:
                        return {'success': False, 'error': 'Higher priority user has conflicting change'}
            
            return {'success': True, 'message': 'Role priority resolved'}
        
        # Manual resolution required
        self.conflict_queue.append(action)
        return {'success': False, 'error': 'Manual resolution required', 'requires_manual': True}
    
    async def _attempt_automatic_merge(self, action: EditAction, conflicts: List[EditAction]) -> Dict[str, Any]:
        """Attempt to automatically merge conflicting changes."""
        
        # For text modifications, try to merge if they don't overlap
        if action.operation == EditOperation.MODIFY and 'text' in action.data:
            # This is a simplified merge - a full implementation would use
            # operational transforms or similar techniques
            
            # Check if the text changes can be merged
            for conflict in conflicts:
                if conflict.operation == EditOperation.MODIFY and 'text' in conflict.data:
                    # If both are simple text changes, merge them
                    if self._can_merge_text_changes(action.data, conflict.data):
                        merged_text = self._merge_text_changes(action.data, conflict.data)
                        action.data['text'] = merged_text
                        return {'success': True, 'message': 'Automatically merged text changes'}
        
        # For timing changes, use the most recent
        if ('start_time' in action.data or 'end_time' in action.data):
            return {'success': True, 'message': 'Using latest timing'}
        
        return {'success': False, 'message': 'Cannot merge automatically'}
    
    def _can_merge_text_changes(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> bool:
        """Check if two text changes can be merged."""
        # Simplified check - in practice would need more sophisticated analysis
        text1 = data1.get('text', '')
        text2 = data2.get('text', '')
        
        # If texts are similar length and don't have major differences
        if abs(len(text1) - len(text2)) < 50:  # Arbitrary threshold
            return True
        
        return False
    
    def _merge_text_changes(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> str:
        """Merge two text changes."""
        # Simplified merge - take the longer text
        text1 = data1.get('text', '')
        text2 = data2.get('text', '')
        
        return text1 if len(text1) >= len(text2) else text2
    
    async def _apply_edit_action(self, action: EditAction) -> Dict[str, Any]:
        """Apply an edit action to the project data."""
        try:
            if action.operation == EditOperation.MODIFY:
                # Modify segment
                if action.segment_id in self.current_subtitle_data.get('segments', {}):
                    segment = self.current_subtitle_data['segments'][action.segment_id]
                    for key, value in action.data.items():
                        segment[key] = value
                    return {'success': True, 'message': 'Segment modified'}
                else:
                    return {'success': False, 'error': 'Segment not found'}
            
            elif action.operation == EditOperation.INSERT:
                # Insert new segment
                segments = self.current_subtitle_data.setdefault('segments', {})
                segments[action.segment_id] = action.data
                return {'success': True, 'message': 'Segment inserted'}
            
            elif action.operation == EditOperation.DELETE:
                # Delete segment
                if action.segment_id in self.current_subtitle_data.get('segments', {}):
                    del self.current_subtitle_data['segments'][action.segment_id]
                    return {'success': True, 'message': 'Segment deleted'}
                else:
                    return {'success': False, 'error': 'Segment not found'}
            
            elif action.operation == EditOperation.MOVE:
                # Move segment (change timing)
                if action.segment_id in self.current_subtitle_data.get('segments', {}):
                    segment = self.current_subtitle_data['segments'][action.segment_id]
                    if 'new_start_time' in action.data:
                        segment['start_time'] = action.data['new_start_time']
                    if 'new_end_time' in action.data:
                        segment['end_time'] = action.data['new_end_time']
                    return {'success': True, 'message': 'Segment moved'}
                else:
                    return {'success': False, 'error': 'Segment not found'}
            
            else:
                return {'success': False, 'error': f'Unknown operation: {action.operation}'}
                
        except Exception as e:
            logger.error(f"Failed to apply edit action: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_edit_permission(self, user: CollaborativeUser, operation: EditOperation, segment_id: str) -> bool:
        """Check if user has permission to perform edit."""
        role_permissions = {
            'viewer': [],
            'reviewer': [EditOperation.MODIFY],  # Can only modify text
            'editor': [EditOperation.MODIFY, EditOperation.INSERT, EditOperation.DELETE, EditOperation.MOVE],
            'admin': list(EditOperation)  # Can do everything
        }
        
        allowed_operations = role_permissions.get(user.role, [])
        return operation in allowed_operations
    
    async def _broadcast_edit(self, action: EditAction):
        """Broadcast edit to all connected users."""
        await self._broadcast_user_event('edit_applied', {
            'action': action.to_dict(),
            'applied_by': self.connected_users[action.user_id].username
        }, exclude_user=action.user_id)
    
    async def _broadcast_user_event(self, event_type: str, data: Dict[str, Any], exclude_user: str = None):
        """Broadcast event to all connected users."""
        for callback in self.sync_callbacks:
            try:
                await callback(event_type, data, exclude_user)
            except Exception as e:
                logger.error(f"Broadcast callback error: {e}")
    
    async def _delayed_user_removal(self, user_id: str, delay_seconds: int):
        """Remove user after delay if still offline."""
        await asyncio.sleep(delay_seconds)
        
        if (user_id in self.connected_users and 
            not self.connected_users[user_id].online):
            del self.connected_users[user_id]
            logger.info(f"User {user_id} removed after timeout")
    
    async def _check_auto_save(self):
        """Check if auto-save is needed."""
        if not self.edit_history:
            return
        
        last_edit_time = max(action.timestamp for action in self.edit_history if action.applied)
        
        if (datetime.now() - last_edit_time).total_seconds() >= self.auto_save_interval:
            # Auto-save logic would go here
            logger.info("Auto-save triggered")
    
    def add_sync_callback(self, callback: Callable):
        """Add callback for real-time synchronization."""
        self.sync_callbacks.append(callback)
    
    def remove_sync_callback(self, callback: Callable):
        """Remove sync callback."""
        if callback in self.sync_callbacks:
            self.sync_callbacks.remove(callback)