"""Server-Sent Events (SSE) Manager for real-time progress updates."""

import json
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Callable, Optional
from queue import Queue, Empty

class SSEManager:
    """
    Server-Sent Events Manager to handle real-time progress updates.
    Provides a way to send progress updates to clients in real-time without polling.
    """
    
    def __init__(self, max_stored_events: int = 50):
        self._lock = threading.Lock()
        self._clients: Dict[str, Dict[str, List[Queue]]] = defaultdict(lambda: defaultdict(list))
        self._event_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_stored_events)))
    
    def add_client(self, client_id: str, event_type: str) -> Queue:
        """
        Register a new client for receiving updates for a specific event type.
        
        Args:
            client_id: Unique identifier for the task (e.g., export task ID)
            event_type: Type of event to subscribe to (e.g., 'export_progress')
            
        Returns:
            Queue: A queue that will receive events for this client
        """
        queue = Queue()
        
        with self._lock:
            self._clients[client_id][event_type].append(queue)
            
            # Send all historical events for this client_id and event_type
            for event in self._event_history[client_id][event_type]:
                queue.put(event)
        
        return queue
    
    def remove_client(self, client_id: str, event_type: str, queue: Queue):
        """Remove a client subscription."""
        with self._lock:
            if client_id in self._clients and event_type in self._clients[client_id]:
                if queue in self._clients[client_id][event_type]:
                    self._clients[client_id][event_type].remove(queue)
                
                # Cleanup if no more clients for this event type
                if not self._clients[client_id][event_type]:
                    del self._clients[client_id][event_type]
                    
                    # Cleanup if no more event types for this client
                    if not self._clients[client_id]:
                        del self._clients[client_id]
    
    def publish_event(self, client_id: str, event_type: str, data: dict):
        """
        Publish an event to all clients subscribed to this client_id and event_type.
        
        Args:
            client_id: Unique identifier for the task
            event_type: Type of event (e.g., 'export_progress')
            data: Event data to publish
        """
        event = {
            'event': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        event_str = json.dumps(event)
        
        with self._lock:
            # Store in history
            self._event_history[client_id][event_type].append(event_str)
            
            # Send to all subscribed clients
            if client_id in self._clients and event_type in self._clients[client_id]:
                for queue in self._clients[client_id][event_type]:
                    queue.put(event_str)
    
    def get_client_count(self, client_id: Optional[str] = None, event_type: Optional[str] = None) -> int:
        """Get the number of clients subscribed to a specific client_id and/or event_type."""
        with self._lock:
            if client_id is None:
                # Count all clients
                return sum(len(queues) for client in self._clients.values() 
                          for queues in client.values())
            elif event_type is None:
                # Count clients for a specific client_id
                return sum(len(queues) for queues in self._clients.get(client_id, {}).values())
            else:
                # Count clients for a specific client_id and event_type
                return len(self._clients.get(client_id, {}).get(event_type, []))


# Create a global SSE manager instance
sse_manager = SSEManager()