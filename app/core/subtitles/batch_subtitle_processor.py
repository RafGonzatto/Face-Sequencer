"""
Batch Subtitle Processing System - Phase 3 Implementation
Advanced batch processing with parallel execution, queue management, and progress tracking.
"""

import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
import logging
from pathlib import Path
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import queue
import threading
import time
import hashlib

from app.core.subtitles.enhanced_subtitle_engine import EnhancedSubtitleEngine
from app.core.subtitles.ai_subtitle_optimizer import AISubtitleOptimizer, AIOptimizationResult

logger = logging.getLogger(__name__)

@dataclass
class BatchJob:
    """Represents a single job in batch processing queue."""
    job_id: str
    job_type: str  # 'generate', 'optimize', 'export'
    input_data: Dict[str, Any]
    status: str = 'pending'  # pending, processing, completed, failed
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    priority: int = 5  # 1-10, lower numbers = higher priority
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None

@dataclass 
class BatchProcessingResult:
    """Result from batch processing operation."""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    processing_time: float
    results: List[Dict[str, Any]]
    errors: List[Dict[str, str]]
    performance_metrics: Dict[str, Any]

@dataclass
class ProcessingStats:
    """Real-time processing statistics."""
    jobs_queued: int = 0
    jobs_processing: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_processing_time: float = 0.0
    average_job_time: float = 0.0
    throughput_per_minute: float = 0.0
    queue_wait_time: float = 0.0

class BatchSubtitleProcessor:
    """
    Advanced batch processing system for subtitle operations.
    Supports parallel processing, queue management, and real-time progress tracking.
    """
    
    def __init__(self, max_workers: int = None, max_queue_size: int = 1000):
        self.max_workers = max_workers or min(8, multiprocessing.cpu_count())
        self.max_queue_size = max_queue_size
        
        # Processing components
        self.subtitle_engine = EnhancedSubtitleEngine()
        self.ai_optimizer = AISubtitleOptimizer()
        
        # Queue and job management
        self.job_queue = asyncio.Queue(maxsize=max_queue_size)
        self.active_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: Dict[str, BatchJob] = {}
        self.job_history = []
        
        # Processing control
        self.processing_active = False
        self.worker_tasks = []
        self.stats = ProcessingStats()
        
        # Thread pool for I/O operations
        self.thread_executor = ThreadPoolExecutor(max_workers=4)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        # Progress callbacks
        self.progress_callbacks: List[Callable] = []
        
        logger.info(f"Batch processor initialized with {self.max_workers} workers")
    
    async def start_processing(self):
        """Start the batch processing system."""
        if self.processing_active:
            logger.warning("Batch processing already active")
            return
        
        self.processing_active = True
        logger.info("Starting batch processing system")
        
        # Create worker tasks
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        # Start stats monitoring
        asyncio.create_task(self._monitor_stats())
    
    async def stop_processing(self, graceful: bool = True):
        """Stop the batch processing system."""
        logger.info("Stopping batch processing system")
        self.processing_active = False
        
        if graceful:
            # Wait for current jobs to complete
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        else:
            # Cancel all tasks immediately
            for task in self.worker_tasks:
                task.cancel()
        
        self.worker_tasks.clear()
        
        # Shutdown executors
        self.thread_executor.shutdown(wait=graceful)
        self.process_executor.shutdown(wait=graceful)
    
    async def submit_batch_job(self, 
                              job_type: str,
                              input_data: Dict[str, Any],
                              priority: int = 5) -> str:
        """
        Submit a new job to the batch processing queue.
        
        Args:
            job_type: Type of job ('generate', 'optimize', 'export', 'batch_generate')
            input_data: Job-specific input data
            priority: Job priority (1-10, lower = higher priority)
            
        Returns:
            job_id: Unique identifier for tracking the job
        """
        job_id = str(uuid.uuid4())
        
        # Estimate processing time
        estimated_duration = self._estimate_job_duration(job_type, input_data)
        
        job = BatchJob(
            job_id=job_id,
            job_type=job_type,
            input_data=input_data,
            priority=priority,
            estimated_duration=estimated_duration
        )
        
        try:
            await self.job_queue.put(job)
            self.active_jobs[job_id] = job
            self.stats.jobs_queued += 1
            
            logger.info(f"Job {job_id} submitted to queue (type: {job_type}, priority: {priority})")
            
            # Notify progress callbacks
            await self._notify_progress_callbacks('job_submitted', {
                'job_id': job_id,
                'job_type': job_type,
                'queue_size': self.job_queue.qsize()
            })
            
            return job_id
            
        except asyncio.QueueFull:
            logger.error(f"Job queue full, cannot submit job {job_id}")
            raise Exception("Batch processing queue is full")
    
    async def submit_multiple_jobs(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """Submit multiple jobs as a batch."""
        job_ids = []
        
        for job_spec in jobs:
            job_id = await self.submit_batch_job(
                job_spec['job_type'],
                job_spec['input_data'],
                job_spec.get('priority', 5)
            )
            job_ids.append(job_id)
        
        logger.info(f"Submitted batch of {len(jobs)} jobs")
        return job_ids
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific job."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
        elif job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
        else:
            return None
        
        return {
            'job_id': job.job_id,
            'job_type': job.job_type,
            'status': job.status,
            'progress': job.progress,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'estimated_duration': job.estimated_duration,
            'actual_duration': job.actual_duration,
            'error_message': job.error_message,
            'has_result': job.result is not None
        }
    
    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed job."""
        if job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            if job.status == 'completed' and job.result:
                return job.result
        return None
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue and processing status."""
        return {
            'queue_size': self.job_queue.qsize(),
            'active_jobs': len([j for j in self.active_jobs.values() if j.status == 'processing']),
            'pending_jobs': len([j for j in self.active_jobs.values() if j.status == 'pending']),
            'completed_jobs': len(self.completed_jobs),
            'processing_active': self.processing_active,
            'stats': {
                'jobs_queued': self.stats.jobs_queued,
                'jobs_processing': self.stats.jobs_processing,
                'jobs_completed': self.stats.jobs_completed,
                'jobs_failed': self.stats.jobs_failed,
                'average_job_time': self.stats.average_job_time,
                'throughput_per_minute': self.stats.throughput_per_minute
            }
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or processing job."""
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        
        if job.status == 'pending':
            # Remove from queue (this is approximate since we can't remove from asyncio.Queue directly)
            job.status = 'cancelled'
            job.error_message = 'Job cancelled by user'
            self._move_job_to_completed(job_id)
            return True
        
        elif job.status == 'processing':
            # Mark for cancellation (worker will handle it)
            job.status = 'cancelling'
            return True
        
        return False
    
    async def process_batch_generation(self, 
                                     video_files: List[str],
                                     transcripts: List[str],
                                     options: Dict[str, Any] = None) -> str:
        """
        Process multiple videos for subtitle generation.
        
        Args:
            video_files: List of video file paths
            transcripts: List of corresponding transcripts
            options: Generation options
            
        Returns:
            batch_job_id: ID for tracking the entire batch
        """
        if len(video_files) != len(transcripts):
            raise ValueError("Number of video files must match number of transcripts")
        
        batch_job_id = str(uuid.uuid4())
        
        # Create individual jobs for each video
        individual_jobs = []
        for i, (video_file, transcript) in enumerate(zip(video_files, transcripts)):
            job_data = {
                'job_type': 'generate',
                'input_data': {
                    'video_file': video_file,
                    'transcript': transcript,
                    'options': options or {},
                    'batch_id': batch_job_id,
                    'batch_index': i,
                    'batch_total': len(video_files)
                },
                'priority': 3  # Higher priority for batch jobs
            }
            individual_jobs.append(job_data)
        
        # Submit all jobs
        job_ids = await self.submit_multiple_jobs(individual_jobs)
        
        # Create a batch tracking job
        await self.submit_batch_job(
            'batch_tracker',
            {
                'batch_id': batch_job_id,
                'individual_job_ids': job_ids,
                'batch_type': 'generation'
            },
            priority=2
        )
        
        logger.info(f"Started batch generation for {len(video_files)} videos (batch ID: {batch_job_id})")
        return batch_job_id
    
    async def process_batch_optimization(self,
                                       subtitle_data: List[Dict[str, Any]],
                                       optimization_options: Dict[str, Any] = None) -> str:
        """Process multiple subtitle sets for AI optimization."""
        batch_job_id = str(uuid.uuid4())
        
        individual_jobs = []
        for i, data in enumerate(subtitle_data):
            job_data = {
                'job_type': 'optimize',
                'input_data': {
                    'subtitle_segments': data['segments'],
                    'options': optimization_options or {},
                    'batch_id': batch_job_id,
                    'batch_index': i,
                    'batch_total': len(subtitle_data)
                },
                'priority': 4
            }
            individual_jobs.append(job_data)
        
        job_ids = await self.submit_multiple_jobs(individual_jobs)
        
        await self.submit_batch_job(
            'batch_tracker',
            {
                'batch_id': batch_job_id,
                'individual_job_ids': job_ids,
                'batch_type': 'optimization'
            },
            priority=2
        )
        
        logger.info(f"Started batch optimization for {len(subtitle_data)} subtitle sets")
        return batch_job_id
    
    async def _worker(self, worker_name: str):
        """Worker coroutine that processes jobs from the queue."""
        logger.info(f"Worker {worker_name} started")
        
        while self.processing_active:
            try:
                # Get next job with timeout to allow for shutdown
                job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                
                if job.status == 'cancelled':
                    continue
                
                # Update job status
                job.status = 'processing'
                job.started_at = datetime.now()
                self.stats.jobs_processing += 1
                
                logger.info(f"Worker {worker_name} processing job {job.job_id} (type: {job.job_type})")
                
                # Notify progress callbacks
                await self._notify_progress_callbacks('job_started', {
                    'job_id': job.job_id,
                    'worker_name': worker_name
                })
                
                try:
                    # Process the job based on type
                    if job.job_type == 'generate':
                        result = await self._process_generate_job(job)
                    elif job.job_type == 'optimize':
                        result = await self._process_optimize_job(job)
                    elif job.job_type == 'export':
                        result = await self._process_export_job(job)
                    elif job.job_type == 'batch_tracker':
                        result = await self._process_batch_tracker_job(job)
                    else:
                        raise ValueError(f"Unknown job type: {job.job_type}")
                    
                    # Job completed successfully
                    job.status = 'completed'
                    job.result = result
                    job.completed_at = datetime.now()
                    job.actual_duration = (job.completed_at - job.started_at).total_seconds()
                    
                    logger.info(f"Job {job.job_id} completed successfully in {job.actual_duration:.2f}s")
                    
                except Exception as e:
                    # Job failed
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    
                    logger.error(f"Job {job.job_id} failed: {e}")
                
                # Update statistics
                self.stats.jobs_processing -= 1
                if job.status == 'completed':
                    self.stats.jobs_completed += 1
                else:
                    self.stats.jobs_failed += 1
                
                # Move to completed jobs
                self._move_job_to_completed(job.job_id)
                
                # Notify progress callbacks
                await self._notify_progress_callbacks('job_completed', {
                    'job_id': job.job_id,
                    'status': job.status,
                    'duration': job.actual_duration
                })
                
            except asyncio.TimeoutError:
                # No job available, continue loop
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                continue
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_generate_job(self, job: BatchJob) -> Dict[str, Any]:
        """Process subtitle generation job."""
        input_data = job.input_data
        
        # Update progress
        job.progress = 0.1
        
        # Extract audio and generate alignment
        video_file = input_data['video_file']
        transcript = input_data['transcript']
        options = input_data.get('options', {})
        
        # Use enhanced subtitle engine
        result = await asyncio.get_event_loop().run_in_executor(
            self.thread_executor,
            self._generate_subtitles_sync,
            video_file, transcript, options, job
        )
        
        return result
    
    async def _process_optimize_job(self, job: BatchJob) -> Dict[str, Any]:
        """Process AI optimization job."""
        input_data = job.input_data
        
        job.progress = 0.1
        
        segments = input_data['subtitle_segments']
        options = input_data.get('options', {})
        
        # Convert to SubtitleSegment objects
        from app.core.subtitles.enhanced_subtitle_engine import SubtitleSegment
        segment_objects = []
        for seg_data in segments:
            segment = SubtitleSegment(
                id=seg_data['id'],
                text=seg_data['text'],
                start_time=seg_data['start_time'],
                end_time=seg_data['end_time'],
                confidence=seg_data.get('confidence', 1.0)
            )
            segment_objects.append(segment)
        
        job.progress = 0.3
        
        # Apply AI optimization
        optimization_result = await self.ai_optimizer.optimize_subtitles_ai(
            segment_objects,
            optimization_level=options.get('level', 'balanced'),
            target_platform=options.get('platform', 'general'),
            user_preferences=options.get('preferences', {})
        )
        
        job.progress = 1.0
        
        # Convert back to serializable format
        return {
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
                for seg in optimization_result.optimized_segments
            ],
            'optimization_metrics': {
                'optimization_score': optimization_result.optimization_score,
                'readability_improvement': optimization_result.readability_improvement,
                'timing_adjustments': optimization_result.timing_adjustments,
                'text_modifications': optimization_result.text_modifications,
                'ai_confidence': optimization_result.ai_confidence,
                'optimization_time': optimization_result.optimization_time,
                'suggestions': optimization_result.suggestions
            }
        }
    
    async def _process_export_job(self, job: BatchJob) -> Dict[str, Any]:
        """Process video export job."""
        # Implementation for video export with subtitles
        job.progress = 0.1
        
        # This would integrate with the existing export system
        # For now, return a placeholder
        job.progress = 1.0
        
        return {
            'export_path': '/path/to/exported/video.mp4',
            'export_time': 5.2,
            'file_size_mb': 25.6
        }
    
    async def _process_batch_tracker_job(self, job: BatchJob) -> Dict[str, Any]:
        """Process batch tracking job that monitors individual jobs."""
        input_data = job.input_data
        individual_job_ids = input_data['individual_job_ids']
        batch_type = input_data['batch_type']
        
        # Monitor individual jobs until all complete
        while True:
            completed = 0
            failed = 0
            total_progress = 0.0
            
            for job_id in individual_job_ids:
                job_status = await self.get_job_status(job_id)
                if job_status:
                    if job_status['status'] == 'completed':
                        completed += 1
                        total_progress += 1.0
                    elif job_status['status'] == 'failed':
                        failed += 1
                        total_progress += 1.0
                    else:
                        total_progress += job_status['progress']
            
            # Update batch job progress
            job.progress = total_progress / len(individual_job_ids)
            
            # Check if all jobs are complete
            if completed + failed >= len(individual_job_ids):
                break
            
            # Wait before next check
            await asyncio.sleep(2.0)
        
        return {
            'batch_type': batch_type,
            'total_jobs': len(individual_job_ids),
            'completed_jobs': completed,
            'failed_jobs': failed,
            'success_rate': completed / len(individual_job_ids) if individual_job_ids else 0
        }
    
    def _generate_subtitles_sync(self, video_file: str, transcript: str, options: Dict[str, Any], job: BatchJob) -> Dict[str, Any]:
        """Synchronous subtitle generation for thread executor."""
        # This would call the actual subtitle generation
        # For now, return a placeholder result
        job.progress = 1.0
        
        return {
            'segments': [
                {
                    'id': '1',
                    'text': 'Generated subtitle text',
                    'start_time': 0.0,
                    'end_time': 2.5,
                    'confidence': 0.95
                }
            ],
            'generation_time': 3.2,
            'word_count': 100
        }
    
    def _estimate_job_duration(self, job_type: str, input_data: Dict[str, Any]) -> float:
        """Estimate how long a job will take to process."""
        base_times = {
            'generate': 30.0,  # Base time for subtitle generation
            'optimize': 5.0,   # Base time for AI optimization
            'export': 60.0,    # Base time for video export
            'batch_tracker': 1.0
        }
        
        base_time = base_times.get(job_type, 10.0)
        
        # Adjust based on input complexity
        if job_type == 'generate' and 'video_file' in input_data:
            # Estimate based on video length (would need actual implementation)
            base_time *= 1.5  # Placeholder adjustment
        
        return base_time
    
    def _move_job_to_completed(self, job_id: str):
        """Move job from active to completed."""
        if job_id in self.active_jobs:
            job = self.active_jobs.pop(job_id)
            self.completed_jobs[job_id] = job
            self.job_history.append(job)
            
            # Limit history size
            if len(self.job_history) > 1000:
                self.job_history = self.job_history[-500:]
    
    async def _monitor_stats(self):
        """Monitor and update processing statistics."""
        start_time = datetime.now()
        last_completed = self.stats.jobs_completed
        
        while self.processing_active:
            await asyncio.sleep(30)  # Update every 30 seconds
            
            # Calculate throughput
            current_time = datetime.now()
            elapsed_minutes = (current_time - start_time).total_seconds() / 60
            
            if elapsed_minutes > 0:
                completed_jobs = self.stats.jobs_completed
                self.stats.throughput_per_minute = completed_jobs / elapsed_minutes
                
                # Calculate average job time
                if completed_jobs > 0 and self.completed_jobs:
                    total_time = sum(
                        job.actual_duration for job in self.completed_jobs.values() 
                        if job.actual_duration and job.status == 'completed'
                    )
                    completed_with_time = sum(
                        1 for job in self.completed_jobs.values() 
                        if job.actual_duration and job.status == 'completed'
                    )
                    if completed_with_time > 0:
                        self.stats.average_job_time = total_time / completed_with_time
    
    async def _notify_progress_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify all registered progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """Remove a progress callback function."""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get detailed processing performance metrics."""
        return {
            'queue_metrics': {
                'current_queue_size': self.job_queue.qsize(),
                'max_queue_size': self.max_queue_size,
                'queue_utilization': self.job_queue.qsize() / self.max_queue_size
            },
            'processing_metrics': {
                'active_workers': len(self.worker_tasks),
                'max_workers': self.max_workers,
                'worker_utilization': self.stats.jobs_processing / self.max_workers if self.max_workers > 0 else 0
            },
            'performance_metrics': {
                'jobs_completed': self.stats.jobs_completed,
                'jobs_failed': self.stats.jobs_failed,
                'success_rate': self.stats.jobs_completed / (self.stats.jobs_completed + self.stats.jobs_failed) if (self.stats.jobs_completed + self.stats.jobs_failed) > 0 else 0,
                'average_job_time': self.stats.average_job_time,
                'throughput_per_minute': self.stats.throughput_per_minute
            },
            'resource_metrics': {
                'memory_usage_mb': self._get_memory_usage(),
                'active_job_count': len(self.active_jobs),
                'completed_job_count': len(self.completed_jobs)
            }
        }
    
    def _get_memory_usage(self) -> float:
        """Get approximate memory usage in MB."""
        import sys
        
        # Rough estimate of memory usage
        job_size = sum(len(str(job)) for job in self.active_jobs.values())
        job_size += sum(len(str(job)) for job in self.completed_jobs.values())
        
        return job_size / 1024 / 1024  # Convert to MB