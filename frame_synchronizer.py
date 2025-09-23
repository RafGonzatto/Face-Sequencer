# frame_synchronizer.py - Precise frame-level synchronization system
"""
Advanced frame synchronization with sub-frame timing and interpolation.
Handles frame rate vs audio sample rate mismatch for smooth lip-sync.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import math

@dataclass
class FrameState:
    """State of animation at a specific frame"""
    frame_number: int
    timestamp: float
    active_word: Optional[str]
    word_progress: float  # 0.0 to 1.0 within current word
    opacity: float        # For fade in/out effects
    viseme: Optional[str] # Current mouth shape
    confidence: float     # Timing confidence

@dataclass  
class WordTiming:
    """Precise word timing with sub-frame resolution"""
    word: str
    start_time: float
    end_time: float
    start_frame_float: float  # Exact frame position (can be fractional)
    end_frame_float: float
    start_frame: int         # Floor of start_frame_float
    end_frame: int          # Ceil of end_frame_float
    start_offset: float     # Sub-frame offset (0.0 to 1.0)
    end_offset: float
    duration: float
    confidence: float

class PreciseFrameSynchronizer:
    """
    Advanced frame synchronizer that handles:
    - Sub-frame timing precision
    - Smooth interpolation between words
    - Frame rate vs audio sample rate alignment
    - Easing functions for natural transitions
    """
    
    def __init__(self, fps: float = 30.0, audio_sample_rate: int = 16000):
        self.fps = fps
        self.frame_duration = 1.0 / fps  # Duration of each frame in seconds
        self.audio_sample_rate = audio_sample_rate
        
        # Transition settings
        self.fade_duration = 0.1        # 100ms fade between words
        self.minimum_word_duration = 0.05  # 50ms minimum display time
        
        print(f"🎬 FrameSynchronizer initialized: {fps} FPS, {self.frame_duration*1000:.1f}ms per frame")
    
    def create_animation_timeline(self, 
                                word_timings: List[Tuple[str, float, float]], 
                                total_duration: float,
                                confidence_scores: Optional[List[float]] = None,
                                silence_segments: Optional[List] = None) -> List[WordTiming]:
        """
        Create precise animation timeline with sub-frame accuracy including silence segments
        
        Args:
            word_timings: List of (word, start_time, end_time) tuples
            total_duration: Total audio duration in seconds
            confidence_scores: Optional confidence scores for each word
            silence_segments: Optional silence segments to include as pauses
            
        Returns:
            List of WordTiming objects with precise frame mapping including pauses
        """
        timeline = []
        
        if not word_timings:
            return timeline
            
        print(f"🎯 Creating timeline for {len(word_timings)} words over {total_duration:.2f}s")
        
        # Create a combined list of all timing events (words + silences)
        all_events = []
        
        # Add word events
        for i, (word, start_time, end_time) in enumerate(word_timings):
            confidence = confidence_scores[i] if confidence_scores else 0.8
            all_events.append({
                'type': 'word',
                'text': word,
                'start_time': start_time,
                'end_time': end_time,
                'confidence': confidence
            })
        
        # Add silence events if provided
        if silence_segments:
            for seg in silence_segments:
                all_events.append({
                    'type': 'pause',
                    'text': '',  # Empty for pause
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'confidence': seg.confidence if hasattr(seg, 'confidence') else 0.9
                })
        
        # Sort all events by start time
        all_events.sort(key=lambda x: x['start_time'])
        
        # Fill gaps between events with pauses to maintain perfect timing
        complete_timeline = []
        last_end_time = 0.0
        
        for event in all_events:
            start_time = event['start_time']
            end_time = event['end_time']
            
            # Add pause if there's a gap before this event
            if start_time > last_end_time + 0.01:  # 10ms tolerance
                gap_duration = start_time - last_end_time
                if gap_duration > 0.05:  # Only add pauses longer than 50ms
                    complete_timeline.append({
                        'type': 'pause',
                        'text': '',
                        'start_time': last_end_time,
                        'end_time': start_time,
                        'confidence': 0.8
                    })
            
            # Add the event itself
            complete_timeline.append(event)
            last_end_time = max(last_end_time, end_time)
        
        # Add final pause if needed to reach total duration
        if last_end_time < total_duration - 0.01:
            complete_timeline.append({
                'type': 'pause',
                'text': '',
                'start_time': last_end_time,
                'end_time': total_duration,
                'confidence': 0.8
            })
        
        # Convert to WordTiming objects (including pauses)
        for event in complete_timeline:
            start_time = event['start_time']
            end_time = event['end_time']
            
            # Ensure minimum duration
            if end_time - start_time < self.minimum_word_duration:
                end_time = start_time + self.minimum_word_duration
            
            # Calculate exact frame positions (float precision)
            start_frame_float = start_time * self.fps
            end_frame_float = end_time * self.fps
            
            # Integer frame boundaries
            start_frame = int(math.floor(start_frame_float))
            end_frame = int(math.ceil(end_frame_float))
            
            # Sub-frame offsets (0.0 to 1.0)
            start_offset = start_frame_float - start_frame
            end_offset = end_frame_float - end_frame
            
            # Ensure end_offset is positive
            if end_offset <= 0.0:
                end_offset = 1.0
                end_frame -= 1
            
            word_timing = WordTiming(
                word=event['text'] if event['type'] == 'word' else 'PAUSE',
                start_time=start_time,
                end_time=end_time,
                start_frame_float=start_frame_float,
                end_frame_float=end_frame_float,
                start_frame=start_frame,
                end_frame=end_frame,
                start_offset=start_offset,
                end_offset=end_offset,
                duration=end_time - start_time,
                confidence=event['confidence']
            )
            
            timeline.append(word_timing)
        
        print(f"✅ Timeline created with sub-frame precision")
        print(f"📊 Timeline: {len([t for t in timeline if t.word != 'PAUSE'])} words, {len([t for t in timeline if t.word == 'PAUSE'])} pauses")
        return timeline
    
    def interpolate_frame_state(self, 
                              timeline: List[WordTiming], 
                              current_time: float) -> Optional[FrameState]:
        """
        Calculate precise animation state at given time with interpolation
        
        Args:
            timeline: Animation timeline
            current_time: Current time in seconds
            
        Returns:
            FrameState with interpolated values, or None if no active word
        """
        current_frame_float = current_time * self.fps
        current_frame = int(current_frame_float)
        
        # Find active word(s) at current time
        active_word = None
        word_progress = 0.0
        opacity = 0.0
        confidence = 0.0
        
        for word_timing in timeline:
            # Check if current time is within word boundaries
            if word_timing.start_time <= current_time <= word_timing.end_time:
                active_word = word_timing.word
                confidence = word_timing.confidence
                
                # Calculate progress within word (0.0 to 1.0)
                word_progress = (current_time - word_timing.start_time) / word_timing.duration
                word_progress = max(0.0, min(1.0, word_progress))
                
                # Calculate opacity with fade in/out
                opacity = self._calculate_opacity(
                    current_time, 
                    word_timing.start_time, 
                    word_timing.end_time
                )
                
                break
        
        # Handle periods between words - show pause frames instead of extending previous word
        if active_word is None:
            # First check if we're in an explicit pause period
            for word_timing in timeline:
                if (word_timing.word == 'PAUSE' and 
                    word_timing.start_time <= current_time <= word_timing.end_time):
                    # We're in a detected silence/pause period
                    return FrameState(
                        frame_number=current_frame,
                        timestamp=current_time,
                        active_word='PAUSE',
                        word_progress=0.0,
                        opacity=1.0,
                        viseme='REST',  # Rest position during silence
                        confidence=0.9
                    )
            
            # Check if we're between words (gap period) - show REST instead of extending last letter
            for i, word_timing in enumerate(timeline):
                if word_timing.word != 'PAUSE':  # Only check actual words, not pause segments
                    # Check if we're after this word but before next word
                    if current_time > word_timing.end_time:
                        # Find next actual word (not PAUSE)
                        next_word_start = None
                        for j in range(i + 1, len(timeline)):
                            if timeline[j].word != 'PAUSE':
                                next_word_start = timeline[j].start_time
                                break
                        
                        # If we're in the gap between words, show REST
                        if next_word_start is None or current_time < next_word_start:
                            return FrameState(
                                frame_number=current_frame,
                                timestamp=current_time,
                                active_word='REST',
                                word_progress=0.0,
                                opacity=1.0,
                                viseme='REST',  # Show rest position between words
                                confidence=0.8
                            )
            
            # Default rest state for any remaining gaps
            return FrameState(
                frame_number=current_frame,
                timestamp=current_time,
                active_word='REST',
                word_progress=0.0,
                opacity=1.0,
                viseme='REST',
                confidence=0.5
            )
        
        # Determine viseme (simplified mapping)
        viseme = self._word_to_viseme(active_word, word_progress)
        
        return FrameState(
            frame_number=current_frame,
            timestamp=current_time,
            active_word=active_word,
            word_progress=word_progress,
            opacity=opacity,
            viseme=viseme,
            confidence=confidence
        )
    
    def generate_frame_sequence(self, 
                              timeline: List[WordTiming], 
                              total_duration: float,
                              frame_step: int = 1) -> List[FrameState]:
        """
        Generate complete sequence of frame states with precise timing
        
        Args:
            timeline: Animation timeline
            total_duration: Total duration to generate
            frame_step: Frame increment (1 for every frame, 2 for every other frame, etc.)
            
        Returns:
            List of FrameState objects for animation
        """
        frame_states = []
        
        # Use precise calculation based on actual timeline end time if available
        if timeline:
            actual_end_time = max([t.end_time for t in timeline])
            # Use the maximum of provided total_duration and actual timeline end
            precise_duration = max(total_duration, actual_end_time)
        else:
            precise_duration = total_duration
        
        # Calculate frame count with precise timing to avoid accumulating errors
        frame_time = 1.0 / self.fps
        total_frames = int(math.ceil(precise_duration / frame_time))
        
        # Ensure the video duration exactly matches the audio/timeline duration
        calculated_video_duration = total_frames / self.fps
        
        print(f"🎬 Generating {total_frames} frames at {self.fps} FPS")
        print(f"📊 Precise timing - Audio: {precise_duration:.6f}s, Video: {calculated_video_duration:.6f}s")
        print(f"📊 Timing difference: {abs(calculated_video_duration - precise_duration)*1000:.1f}ms")
        
        for frame_num in range(0, total_frames, frame_step):
            # Use precise frame timing to avoid drift
            current_time = frame_num * frame_time
            
            # Ensure we don't exceed the intended duration
            if current_time <= precise_duration:
                frame_state = self.interpolate_frame_state(timeline, current_time)
                
                if frame_state is not None:
                    frame_states.append(frame_state)
        
        # Final verification of timing accuracy
        if frame_states:
            video_duration = len(frame_states) / self.fps
            timing_error = abs(video_duration - precise_duration) * 1000
            
            if timing_error > 50:  # More than 50ms error
                print(f"⚠️  Warning: Significant timing error: {timing_error:.1f}ms")
            else:
                print(f"✅ Timing accurate within {timing_error:.1f}ms")
        
        print(f"✅ Generated {len(frame_states)} frame states")
        return frame_states
    
    def _calculate_opacity(self, current_time: float, start_time: float, end_time: float) -> float:
        """Calculate opacity with smooth fade in/out"""
        duration = end_time - start_time
        fade_in_time = min(self.fade_duration, duration * 0.2)   # 20% of word or fade_duration
        fade_out_time = min(self.fade_duration, duration * 0.2)
        
        # Fade in
        if current_time < start_time + fade_in_time:
            progress = (current_time - start_time) / fade_in_time
            return self._ease_in_out(progress)
        
        # Fade out  
        elif current_time > end_time - fade_out_time:
            progress = (end_time - current_time) / fade_out_time
            return self._ease_in_out(progress)
        
        # Full opacity in middle
        else:
            return 1.0
    
    def _ease_in_out(self, t: float) -> float:
        """Smooth easing function for natural transitions"""
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        
        # Cubic ease-in-out
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def _word_to_viseme(self, word: str, progress: float) -> str:
        """
        Simple word-to-viseme mapping (to be enhanced with phoneme analysis)
        
        Args:
            word: Current word
            progress: Progress within word (0.0 to 1.0)
            
        Returns:
            Viseme code for mouth shape
        """
        if not word:
            return "REST"
        
        # Simplified mapping based on dominant sounds in Portuguese
        first_char = word[0].lower()
        
        # Vowel-heavy words
        if first_char in 'aeiouáéíóúãõ':
            if first_char in 'aá':
                return "A"
            elif first_char in 'eé':
                return "E" 
            elif first_char in 'iií':
                return "I"
            elif first_char in 'oóõ':
                return "O"
            elif first_char in 'uú':
                return "U"
            else:
                return "A"  # Default vowel
        
        # Consonant mapping
        elif first_char in 'pb':
            return "P"  # Bilabial
        elif first_char in 'fv':
            return "F"  # Labiodental
        elif first_char in 'td':
            return "T"  # Alveolar
        elif first_char in 'kg':
            return "K"  # Velar
        elif first_char in 'mn':
            return "M"  # Nasal
        elif first_char in 'lr':
            return "L"  # Liquid
        elif first_char in 'sz':
            return "S"  # Sibilant
        else:
            return "REST"  # Default/unknown
    
    def optimize_timeline(self, timeline: List[WordTiming]) -> List[WordTiming]:
        """
        Optimize timeline to reduce timing conflicts and improve smoothness
        
        Args:
            timeline: Original timeline
            
        Returns:
            Optimized timeline
        """
        if not timeline:
            return timeline
        
        optimized = timeline.copy()
        
        # Sort by start time
        optimized.sort(key=lambda x: x.start_time)
        
        # Fix overlaps
        for i in range(len(optimized) - 1):
            current = optimized[i]
            next_word = optimized[i + 1]
            
            # If words overlap, adjust boundary
            if current.end_time > next_word.start_time:
                # Split the difference
                boundary = (current.end_time + next_word.start_time) / 2
                
                # Update timings
                current.end_time = boundary
                current.duration = current.end_time - current.start_time
                
                next_word.start_time = boundary
                next_word.duration = next_word.end_time - next_word.start_time
                
                # Recalculate frame positions
                current.end_frame_float = current.end_time * self.fps
                current.end_frame = int(math.ceil(current.end_frame_float))
                
                next_word.start_frame_float = next_word.start_time * self.fps
                next_word.start_frame = int(math.floor(next_word.start_frame_float))
        
        # Ensure minimum durations
        for word_timing in optimized:
            if word_timing.duration < self.minimum_word_duration:
                # Extend duration
                extension = self.minimum_word_duration - word_timing.duration
                word_timing.end_time += extension
                word_timing.duration = self.minimum_word_duration
                
                # Recalculate frame positions
                word_timing.end_frame_float = word_timing.end_time * self.fps
                word_timing.end_frame = int(math.ceil(word_timing.end_frame_float))
        
        print(f"🔧 Timeline optimized: {len(optimized)} words")
        return optimized
    
    def export_timeline_json(self, timeline: List[WordTiming], output_path: str):
        """Export timeline to JSON for debugging/analysis"""
        import json
        
        data = {
            "fps": self.fps,
            "frame_duration": self.frame_duration,
            "timeline": []
        }
        
        for word_timing in timeline:
            data["timeline"].append({
                "word": word_timing.word,
                "start_time": word_timing.start_time,
                "end_time": word_timing.end_time,
                "start_frame": word_timing.start_frame,
                "end_frame": word_timing.end_frame,
                "start_frame_float": word_timing.start_frame_float,
                "end_frame_float": word_timing.end_frame_float,
                "start_offset": word_timing.start_offset,
                "end_offset": word_timing.end_offset,
                "duration": word_timing.duration,
                "confidence": word_timing.confidence
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Timeline exported to {output_path}")
    
    def analyze_timing_accuracy(self, timeline: List[WordTiming]) -> Dict[str, float]:
        """Analyze timing accuracy and potential issues"""
        if not timeline:
            return {}
        
        # Calculate statistics
        durations = [wt.duration for wt in timeline]
        confidences = [wt.confidence for wt in timeline]
        
        # Check for gaps
        gaps = []
        for i in range(len(timeline) - 1):
            gap = timeline[i + 1].start_time - timeline[i].end_time
            if gap > 0.01:  # 10ms threshold
                gaps.append(gap)
        
        analysis = {
            "total_words": len(timeline),
            "total_duration": timeline[-1].end_time - timeline[0].start_time if timeline else 0,
            "avg_word_duration": np.mean(durations),
            "min_word_duration": np.min(durations),
            "max_word_duration": np.max(durations),
            "avg_confidence": np.mean(confidences),
            "min_confidence": np.min(confidences),
            "gaps_count": len(gaps),
            "avg_gap_duration": np.mean(gaps) if gaps else 0,
            "words_per_second": len(timeline) / (timeline[-1].end_time - timeline[0].start_time) if timeline else 0
        }
        
        return analysis

# Example usage and testing
if __name__ == "__main__":
    # Test the frame synchronizer
    synchronizer = PreciseFrameSynchronizer(fps=30.0)
    
    # Sample word timings
    word_timings = [
        ("Olá", 0.0, 0.5),
        ("mundo", 0.6, 1.2),  
        ("este", 1.4, 1.8),
        ("é", 1.9, 2.1),
        ("um", 2.2, 2.5),
        ("teste", 2.6, 3.2)
    ]
    
    # Create timeline
    timeline = synchronizer.create_animation_timeline(word_timings, 3.5)
    
    # Optimize timeline
    timeline = synchronizer.optimize_timeline(timeline)
    
    # Generate sample frame states
    frame_states = synchronizer.generate_frame_sequence(timeline, 3.5)
    
    print(f"\n🎬 Generated {len(frame_states)} frame states")
    print("Sample frames:")
    for i in range(0, min(10, len(frame_states))):
        fs = frame_states[i]
        print(f"  Frame {fs.frame_number}: '{fs.active_word}' (progress: {fs.word_progress:.2f}, opacity: {fs.opacity:.2f})")
    
    # Analyze timing
    analysis = synchronizer.analyze_timing_accuracy(timeline)
    print(f"\n📊 Timing Analysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")