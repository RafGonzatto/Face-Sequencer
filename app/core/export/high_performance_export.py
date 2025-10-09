#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
High Performance Video Export Module

Provides optimized video export with parallelism, caching, and FFmpeg optimization.
Designed to dramatically improve video export performance through:
- Parallel frame processing with ThreadPoolExecutor
- Intelligent image caching and memory management  
- Optimized FFmpeg encoding with hardware detection
- Batch processing for better throughput
- Comprehensive error handling with fallback options
"""

import os
import sys
import time
import tempfile
import shutil
import subprocess
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Tuple
import traceback

# Optional imports with fallback
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class ExportConfig:
    """Configuration for high-performance export"""
    max_workers: int = 8
    batch_size: int = 32
    memory_limit_gb: float = 4.0
    cache_frames: bool = True
    use_hardware_encoding: bool = True
    ffmpeg_threads: int = 0  # 0 = auto-detect
    temp_dir: Optional[str] = None


class HighPerformanceVideoExporter:
    """High-performance video exporter with parallel processing"""
    
    def __init__(self, config: Optional[ExportConfig] = None):
        self.config = config or ExportConfig()
        self.max_workers = min(self.config.max_workers, os.cpu_count() or 4)
        self.batch_size = self.config.batch_size
        self.frame_cache = {}
        self.temp_dir = None
        self.stats = {
            'frames_processed': 0,
            'cache_hits': 0,
            'processing_time': 0,
            'encoding_time': 0
        }
        
    def __enter__(self):
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix='high_perf_export_')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print("WARNING: Could not clean temp directory: {}".format(e))
        self.frame_cache.clear()
        
    def _load_image_safe(self, img_path: str, target_size: Tuple[int, int]) -> Optional[Image.Image]:
        """Load image with error handling and caching"""
        if not HAS_PIL:
            return None
            
        # Check cache first
        cache_key = (img_path, target_size)
        if cache_key in self.frame_cache:
            self.stats['cache_hits'] += 1
            return self.frame_cache[cache_key].copy()
            
        try:
            if not img_path or not os.path.exists(img_path):
                return None
                
            img = Image.open(img_path).convert('RGBA')
            
            # Resize if needed
            if img.size != target_size:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
                
            # Cache if memory allows
            if self.config.cache_frames and len(self.frame_cache) < 1000:
                self.frame_cache[cache_key] = img.copy()
                
            return img
            
        except Exception as e:
            print("ERROR: Error loading image {}: {}".format(img_path, e))
            return None
    
    def _create_fallback_image(self, char: str, size: Tuple[int, int]) -> Image.Image:
        """Create fallback image for missing/invalid images"""
        if not HAS_PIL:
            # Create minimal fallback without PIL
            return None
            
        width, height = size
        img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
        
        try:
            draw = ImageDraw.Draw(img)
            
            # Try to load default font
            try:
                font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), char, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except:
                # Fallback font size
                font = None
                text_width = width // 8
                text_height = height // 8
            
            # Center text
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Draw character
            draw.text((x, y), char, fill=(255, 255, 255, 255), font=font)
            
        except Exception:
            # Minimal fallback - just a colored rectangle
            draw = ImageDraw.Draw(img)
            draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], 
                         fill=(128, 128, 128, 255))
        
        return img
    
    def _process_frame_batch(self, batch: List[Tuple[int, Dict]], target_size: Tuple[int, int]) -> List[Tuple[int, str]]:
        """Process a batch of frames in parallel"""
        results = []
        
        for frame_idx, frame_data in batch:
            try:
                # Get image path
                img_path = frame_data.get('img') or frame_data.get('fallback_img')
                char = frame_data.get('char', '?')
                
                # Load or create image
                img = self._load_image_safe(img_path, target_size)
                if img is None:
                    img = self._create_fallback_image(char, target_size)
                
                if img is None:
                    # Ultimate fallback - skip this frame
                    print("WARNING: Could not create image for frame {}".format(frame_idx))
                    continue
                
                # Save frame
                frame_path = os.path.join(self.temp_dir, "frame_{:06d}.png".format(frame_idx))
                img.save(frame_path, 'PNG')
                
                results.append((frame_idx, frame_path))
                self.stats['frames_processed'] += 1
                
            except Exception as e:
                print("ERROR: Error in batch {}: {}".format(frame_idx, e))
                continue
                
        return results
    
    def _prepare_frames_parallel(self, sequence: List[Dict], progress_callback: Optional[Callable] = None) -> List[str]:
        """Prepare frames using parallel processing"""
        if not sequence:
            return []
            
        # Determine target size (use standard size if no images available)
        target_size = (640, 480)  # Default
        
        # Try to get size from first valid image
        for frame in sequence[:10]:  # Check first 10 frames
            img_path = frame.get('img') or frame.get('fallback_img')
            if img_path and os.path.exists(img_path) and HAS_PIL:
                try:
                    with Image.open(img_path) as img:
                        target_size = img.size
                        break
                except:
                    continue
        
        print("PROCESSING: Processing {} frames with {} workers".format(len(sequence), self.max_workers))
        
        # Create batches
        batches = []
        for i in range(0, len(sequence), self.batch_size):
            batch = [(j, sequence[j]) for j in range(i, min(i + self.batch_size, len(sequence)))]
            batches.append(batch)
        
        # Process batches in parallel
        frame_paths = [None] * len(sequence)
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_frame_batch, batch, target_size): batch_idx 
                for batch_idx, batch in enumerate(batches)
            }
            
            # Collect results
            for future in as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    for frame_idx, frame_path in batch_results:
                        frame_paths[frame_idx] = frame_path
                    
                    processed_count += len(batch_results)
                    
                    # Report progress
                    if progress_callback:
                        progress = int((processed_count / len(sequence)) * 50) + 5  # 5-55%
                        progress_callback(progress, 
                            "Preparing frames: {}% ({}/{})".format(
                                int((processed_count / len(sequence)) * 100), 
                                processed_count, len(sequence)
                            )
                        )
                        
                except Exception as e:
                    batch_idx = future_to_batch[future]
                    print("ERROR: Batch {} failed: {}".format(batch_idx, e))
        
        # Filter out None values and ensure we have valid paths
        valid_paths = []
        for i, path in enumerate(frame_paths):
            if path and os.path.exists(path):
                valid_paths.append(path)
            else:
                print("WARNING: Frame {} was not processed, creating fallback".format(i))
                # Create minimal fallback
                fallback_path = os.path.join(self.temp_dir, "frame_{:06d}.png".format(i))
                if HAS_PIL:
                    fallback_img = self._create_fallback_image('?', target_size)
                    if fallback_img:
                        fallback_img.save(fallback_path, 'PNG')
                        valid_paths.append(fallback_path)
        
        return valid_paths
    
    def _detect_ffmpeg_capabilities(self) -> Dict[str, Any]:
        """Detect FFmpeg capabilities and optimal settings"""
        capabilities = {
            'has_ffmpeg': False,
            'has_libx264': False,
            'has_hardware': False,
            'optimal_threads': os.cpu_count() or 4,
            'optimal_preset': 'medium'
        }
        
        try:
            # Check if FFmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            capabilities['has_ffmpeg'] = result.returncode == 0
            
            if capabilities['has_ffmpeg']:
                # Check for libx264
                capabilities['has_libx264'] = 'libx264' in result.stdout
                
                # Check for hardware encoding (basic check)
                for hw_codec in ['nvenc', 'qsv', 'vaapi']:
                    if hw_codec in result.stdout:
                        capabilities['has_hardware'] = True
                        break
                        
        except Exception:
            pass
            
        return capabilities
    
    def _encode_with_ffmpeg_optimized(self, frame_paths: List[str], sequence: List[Dict],
                                     output_path: str, fps: int, crf: int, preset: str,
                                     progress_callback: Optional[Callable] = None) -> bool:
        """Encode video with optimized FFmpeg settings"""
        
        capabilities = self._detect_ffmpeg_capabilities()
        
        if not capabilities['has_ffmpeg']:
            print("ERROR: FFmpeg not found. Trying fallback...")
            return self._encode_with_moviepy_fallback(frame_paths, sequence, output_path, fps, crf, preset, progress_callback)
            
        try:
            print("STATS: Frames: {}".format(len(frame_paths)))
            
            if progress_callback:
                progress_callback(60, "Creating FFmpeg input list...")
            
            # Create frame list with durations
            list_file = os.path.join(self.temp_dir, 'frame_list.txt')
            with open(list_file, 'w', encoding='utf-8') as f:
                for i, frame_path in enumerate(frame_paths):
                    # Normalize path for FFmpeg
                    normalized_path = frame_path.replace('\\', '/')
                    f.write("file '{}'\n".format(normalized_path))
                    
                    # Add duration for this frame
                    if i < len(sequence):
                        try:
                            frame_ms = max(1, int(sequence[i].get('ms', 1000 // fps)))
                        except:
                            frame_ms = 1000 // fps
                        f.write("duration {:.3f}\n".format(frame_ms / 1000.0))
                
                # Duplicate last frame for FFmpeg concat demuxer
                if frame_paths:
                    normalized_path = frame_paths[-1].replace('\\', '/')
                    f.write("file '{}'\n".format(normalized_path))
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Build FFmpeg command with optimizations
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat', '-safe', '0',
                '-i', list_file,
                '-c:v', 'libx264',
                '-preset', preset,
                '-crf', str(crf),
                '-pix_fmt', 'yuv420p',
                '-an'  # No audio
            ]
            
            # Add thread optimization
            optimal_threads = min(capabilities['optimal_threads'], 16)  # Cap at 16
            cmd.extend(['-threads', str(optimal_threads)])
            
            # Add output path
            cmd.append(output_path)
            
            if progress_callback:
                progress_callback(70, "Starting FFmpeg encoding...")
            
            # Run FFmpeg with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress
            last_progress = 70
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line and 'time=' in line and progress_callback:
                    # Basic progress estimation
                    if last_progress < 95:
                        last_progress += 1
                        progress_callback(last_progress, "Encoding video...")
            
            return_code = process.wait()
            
            if return_code == 0:
                print("SUCCESS: FFmpeg encoding completed successfully")
                return True
            else:
                print("ERROR: FFmpeg failed with code {}".format(return_code))
                return False
                
        except FileNotFoundError:
            print("ERROR: FFmpeg not found. Trying fallback...")
            return self._encode_with_moviepy_fallback(frame_paths, sequence, output_path, fps, crf, preset, progress_callback)
        except Exception as e:
            print("ERROR: FFmpeg encoding error: {}".format(e))
            return False
    
    def _encode_with_moviepy_fallback(self, frame_paths: List[str], sequence: List[Dict],
                                     output_path: str, fps: int, crf: int, preset: str,
                                     progress_callback: Optional[Callable] = None) -> bool:
        """Fallback encoding using MoviePy (if available)"""
        try:
            from moviepy.editor import ImageSequenceClip
            
            if progress_callback:
                progress_callback(80, "Using MoviePy fallback...")
            
            # Create clip
            clip = ImageSequenceClip(frame_paths, fps=fps)
            
            # Write video
            clip.write_videofile(
                output_path,
                codec='libx264',
                preset=preset,
                ffmpeg_params=['-crf', str(crf)],
                verbose=False,
                logger=None
            )
            
            return True
            
        except ImportError:
            print("ERROR: MoviePy not available for fallback")
            return False
        except Exception as e:
            print("ERROR: MoviePy fallback also failed: {}".format(e))
            return False
    
    def export(self, sequence: List[Dict], output_path: str, fps: int = 24, 
              crf: int = 23, preset: str = 'fast', 
              progress_callback: Optional[Callable] = None) -> bool:
        """
        Export video with high performance
        
        Args:
            sequence: List of frame dictionaries
            output_path: Output video path
            fps: Frames per second
            crf: Video quality (0-51, lower is better)
            preset: Encoding speed preset
            progress_callback: Optional progress callback
            
        Returns:
            bool: Success status
        """
        
        if not sequence:
            print("ERROR: Empty sequence provided")
            return False
            
        try:
            start_time = time.time()
            
            if progress_callback:
                progress_callback(1, "Initializing optimized export...")
                
            print("OPTIMIZED EXPORT STARTED")
            print("STATS: Frames: {}".format(len(sequence)))
            
            # Prepare frames in parallel
            frame_paths = self._prepare_frames_parallel(sequence, progress_callback)
            
            if not frame_paths:
                print("ERROR: No frames were processed successfully")
                return False
                
            if progress_callback:
                progress_callback(60, "Frames prepared, starting encoding...")
            
            # Encode video
            encoding_start = time.time()
            success = self._encode_with_ffmpeg_optimized(
                frame_paths, sequence, output_path, fps, crf, preset, progress_callback
            )
            encoding_time = time.time() - encoding_start
            
            # Update statistics
            total_time = time.time() - start_time
            self.stats['processing_time'] = total_time - encoding_time
            self.stats['encoding_time'] = encoding_time
            
            if success and progress_callback:
                progress_callback(100, "Export completed successfully!")
                
            # Print performance statistics
            if success:
                print("\nSTATS: PERFORMANCE STATISTICS:")
                print("Total frames: {}".format(len(sequence)))
                print("Frames processed: {}".format(self.stats['frames_processed']))
                print("Cache hits: {}".format(self.stats['cache_hits']))
                print("Processing time: {:.2f}s".format(self.stats['processing_time']))
                print("Encoding time: {:.2f}s".format(self.stats['encoding_time']))
                print("Total time: {:.2f}s".format(total_time))
                print("Frames/second: {:.1f}".format(len(sequence) / total_time))
                
            return success
            
        except Exception as e:
            print("ERROR: Error in optimized export: {}".format(e))
            if progress_callback:
                progress_callback(-1, "Error: {}".format(e))
                
            # Cleanup on error
            try:
                if self.temp_dir and os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
            except Exception as cleanup_e:
                print("WARNING: Error cleaning temp directory: {}".format(cleanup_e))
                
            return False


def export_mp4_optimized(seq: List[Dict], path: str, fps: int = 24, crf: int = 23, 
                        preset: str = 'fast', progress_callback: Optional[Callable] = None) -> bool:
    """
    High-performance MP4 export function
    
    This is the main entry point for optimized video export.
    
    Args:
        seq: List of frame dictionaries with 'char', 'img', 'ms' keys
        path: Output video file path
        fps: Frames per second
        crf: Video quality (0-51, lower is better quality)
        preset: FFmpeg preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        progress_callback: Optional callback function(percent, message)
        
    Returns:
        bool: True if export succeeded, False otherwise
    """
    
    # Create optimized configuration
    config = ExportConfig(
        max_workers=min(8, os.cpu_count() or 4),
        batch_size=32,
        memory_limit_gb=4.0,
        cache_frames=True,
        use_hardware_encoding=True
    )
    
    # Export with high-performance exporter
    with HighPerformanceVideoExporter(config) as exporter:
        return exporter.export(seq, path, fps, crf, preset, progress_callback)


if __name__ == "__main__":
    # Example usage and testing
    print("High Performance Video Export Module")
    print("Usage: from app.core.export.high_performance_export import export_mp4_optimized")
    
    # Create test sequence
    test_seq = []
    for i in range(10):
        test_seq.append({
            'char': chr(ord('A') + i),
            'img': None,
            'ms': 100
        })
    
    # Test export
    success = export_mp4_optimized(
        test_seq, 
        'test_output.mp4', 
        fps=10, 
        crf=23, 
        preset='fast',
        progress_callback=lambda p, m: print("[{}%] {}".format(p, m))
    )
    
    print("Test export result: {}".format(success))