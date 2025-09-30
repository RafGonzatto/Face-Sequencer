"""
Phase 3 Video Editor Demo Script
Demonstrates AI optimization, batch processing, and collaborative editing features.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any

# Import Phase 3 components
from ai_subtitle_optimizer import AISubtitleOptimizer, AIOptimizationResult
from batch_subtitle_processor import BatchSubtitleProcessor, BatchJob
from collaborative_editor import CollaborativeSubtitleEditor, EditOperation
from enhanced_subtitle_engine import SubtitleSegment

async def demo_ai_optimization():
    """Demonstrate AI-powered subtitle optimization."""
    print("🧠 AI Optimization Demo")
    print("=" * 50)
    
    # Initialize AI optimizer
    optimizer = AISubtitleOptimizer()
    
    # Create sample subtitle segments
    segments = [
        SubtitleSegment(
            id="1",
            text="This is a very long and complicated sentence that might be difficult to read quickly on mobile devices.",
            start_time=0.0,
            end_time=4.0
        ),
        SubtitleSegment(
            id="2", 
            text="Furthermore, we need to consider the readability implications.",
            start_time=4.0,
            end_time=7.0
        ),
        SubtitleSegment(
            id="3",
            text="Additionally, the timing should be optimized for the target platform.",
            start_time=7.0,
            end_time=11.0
        )
    ]
    
    print(f"Original segments: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"  {i+1}. \"{seg.text}\" ({seg.end_time - seg.start_time:.1f}s)")
    
    # Apply AI optimization
    print("\nApplying AI optimization...")
    start_time = time.time()
    
    result = await optimizer.optimize_subtitles_ai(
        segments=segments,
        optimization_level="balanced",
        target_platform="instagram",
        user_preferences={
            "improve_readability": True,
            "optimize_timing": True,
            "enhance_coherence": True
        }
    )
    
    optimization_time = time.time() - start_time
    
    print(f"✅ Optimization completed in {optimization_time:.2f}s")
    print(f"   AI Confidence: {result.ai_confidence:.1%}")
    print(f"   Optimization Score: {result.optimization_score:.1%}")
    print(f"   Readability Improvement: {result.readability_improvement:.1f}%")
    print(f"   Timing Adjustments: {result.timing_adjustments}")
    print(f"   Text Modifications: {result.text_modifications}")
    
    print("\nOptimized segments:")
    for i, seg in enumerate(result.optimized_segments):
        print(f"  {i+1}. \"{seg.text}\" ({seg.end_time - seg.start_time:.1f}s)")
    
    if result.suggestions:
        print("\nAI Suggestions:")
        for suggestion in result.suggestions:
            print(f"  • {suggestion}")
    
    # Cache stats
    cache_stats = optimizer.get_cache_stats()
    print(f"\nCache Stats: {cache_stats['cached_optimizations']} cached, "
          f"{cache_stats['cache_size_mb']:.2f} MB")
    
    print("\n" + "=" * 50 + "\n")

async def demo_batch_processing():
    """Demonstrate batch processing capabilities."""
    print("⚡ Batch Processing Demo")
    print("=" * 50)
    
    # Initialize batch processor
    processor = BatchSubtitleProcessor(max_workers=2)
    
    # Start the processor
    await processor.start_processing()
    print("✅ Batch processor started")
    
    # Submit multiple jobs
    jobs_data = [
        {
            "job_type": "generate",
            "input_data": {
                "video_file": "demo_video_1.mp4",
                "transcript": "Hello, this is the first demo video.",
                "options": {"platform": "instagram"}
            },
            "priority": 3
        },
        {
            "job_type": "optimize", 
            "input_data": {
                "subtitle_segments": [
                    {"id": "1", "text": "Sample text for optimization", "start_time": 0.0, "end_time": 3.0}
                ],
                "options": {"level": "balanced", "platform": "tiktok"}
            },
            "priority": 5
        },
        {
            "job_type": "generate",
            "input_data": {
                "video_file": "demo_video_2.mp4", 
                "transcript": "This is another demo video for batch processing.",
                "options": {"platform": "youtube"}
            },
            "priority": 4
        }
    ]
    
    job_ids = await processor.submit_multiple_jobs(jobs_data)
    print(f"✅ Submitted {len(job_ids)} jobs")
    
    # Monitor job progress
    print("\nMonitoring job progress...")
    all_completed = False
    
    while not all_completed:
        queue_status = await processor.get_queue_status()
        print(f"\rQueue: {queue_status['pending_jobs']} pending, "
              f"{queue_status['active_jobs']} processing, "
              f"{queue_status['completed_jobs']} completed", end="")
        
        # Check if all jobs are complete
        completed_count = 0
        for job_id in job_ids:
            status = await processor.get_job_status(job_id)
            if status and status['status'] in ['completed', 'failed']:
                completed_count += 1
        
        if completed_count >= len(job_ids):
            all_completed = True
        else:
            await asyncio.sleep(1)
    
    print("\n✅ All jobs completed!")
    
    # Get results
    print("\nJob Results:")
    for job_id in job_ids:
        status = await processor.get_job_status(job_id)
        if status:
            print(f"  Job {job_id[:8]}... - Status: {status['status']}")
            if status['status'] == 'completed':
                result = await processor.get_job_result(job_id)
                print(f"    Duration: {status['actual_duration']:.2f}s")
    
    # Get processing metrics
    metrics = await processor.get_processing_metrics()
    print(f"\nProcessing Metrics:")
    print(f"  Success Rate: {metrics['performance_metrics']['success_rate']:.1%}")
    print(f"  Average Job Time: {metrics['performance_metrics']['average_job_time']:.2f}s")
    print(f"  Throughput: {metrics['performance_metrics']['throughput_per_minute']:.1f} jobs/min")
    
    # Stop the processor
    await processor.stop_processing(graceful=True)
    print("✅ Batch processor stopped")
    
    print("\n" + "=" * 50 + "\n")

async def demo_collaborative_editing():
    """Demonstrate collaborative editing features."""
    print("👥 Collaborative Editing Demo")
    print("=" * 50)
    
    # Create collaborative session
    project_id = "demo_project_001"
    editor = CollaborativeSubtitleEditor(project_id)
    
    # Connect users
    users = [
        {"id": "user_1", "name": "Alice", "role": "admin"},
        {"id": "user_2", "name": "Bob", "role": "editor"}, 
        {"id": "user_3", "name": "Charlie", "role": "reviewer"}
    ]
    
    print("Connecting users...")
    for user in users:
        connected = await editor.connect_user(user["id"], user["name"], user["role"])
        print(f"  ✅ {user['name']} connected as {user['role']}")
    
    # Initialize project with sample data
    editor.current_subtitle_data = {
        "segments": {
            "seg_1": {
                "id": "seg_1",
                "text": "Welcome to our collaborative demo",
                "start_time": 0.0,
                "end_time": 3.0
            },
            "seg_2": {
                "id": "seg_2", 
                "text": "This segment will be edited collaboratively",
                "start_time": 3.0,
                "end_time": 6.0
            }
        }
    }
    
    # Simulate collaborative edits
    print("\nSimulating collaborative edits...")
    
    # User 1 locks and edits segment 1
    await editor.lock_segment("user_1", "seg_1")
    result1 = await editor.apply_edit(
        "user_1", 
        EditOperation.MODIFY,
        "seg_1",
        {"text": "Welcome to our AMAZING collaborative demo!"}
    )
    print(f"  Alice edited segment 1: {result1['success']}")
    await editor.unlock_segment("user_1", "seg_1")
    
    # User 2 tries to edit the same segment (should work now)
    result2 = await editor.apply_edit(
        "user_2",
        EditOperation.MODIFY, 
        "seg_2",
        {"text": "This segment is now being edited by Bob"}
    )
    print(f"  Bob edited segment 2: {result2['success']}")
    
    # User 3 adds a new segment
    result3 = await editor.apply_edit(
        "user_3",
        EditOperation.INSERT,
        "seg_3", 
        {
            "id": "seg_3",
            "text": "Charlie added this new segment",
            "start_time": 6.0,
            "end_time": 9.0
        }
    )
    print(f"  Charlie added segment 3: {result3['success']}")
    
    # Create a version
    version_id = await editor.create_version("user_1", "First collaborative version")
    print(f"  ✅ Version created: {version_id}")
    
    # Get project state
    project_state = await editor.get_project_state("user_1")
    print(f"\nProject State:")
    print(f"  Connected Users: {len(project_state['connected_users'])}")
    print(f"  Total Segments: {len(project_state['subtitle_data']['segments'])}")
    print(f"  Versions: {len(project_state['version_history'])}")
    print(f"  Edit History: {project_state['edit_history_count']} actions")
    
    # Show final segments
    print("\nFinal Segments:")
    for seg_id, segment in project_state['subtitle_data']['segments'].items():
        print(f"  {seg_id}: \"{segment['text']}\"")
    
    print("\n" + "=" * 50 + "\n")

async def run_comprehensive_demo():
    """Run all Phase 3 demos."""
    print("🚀 Phase 3 Video Editor - Comprehensive Demo")
    print("Advanced AI, Batch Processing & Collaborative Editing")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    try:
        # Run all demos
        await demo_ai_optimization()
        await demo_batch_processing()
        await demo_collaborative_editing()
        
        total_time = time.time() - start_time
        
        print("🎉 All Phase 3 Demos Completed Successfully!")
        print("=" * 70)
        print(f"Total Demo Time: {total_time:.2f} seconds")
        print()
        print("Phase 3 Features Demonstrated:")
        print("  ✅ AI-powered subtitle optimization")
        print("  ✅ Enterprise batch processing")
        print("  ✅ Real-time collaborative editing")
        print()
        print("Ready for production use! 🚀")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(run_comprehensive_demo())