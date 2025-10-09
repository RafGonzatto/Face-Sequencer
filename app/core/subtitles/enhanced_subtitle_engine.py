"""
Enhanced Subtitle Engine - Phase 2 Implementation
Provides advanced subtitle generation, intelligent text processing, and platform optimization.
"""

import json
import re
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from app.core.subtitles.subtitle_engine import SubtitleEngine  # Reuse base implementation

logger = logging.getLogger(__name__)

@dataclass
class SubtitleSegment:
    """Enhanced subtitle segment with intelligence features."""
    id: str
    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0
    word_count: int = 0
    reading_speed: float = 0.0
    platform_optimized: Dict[str, Any] = None
    style_overrides: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.platform_optimized is None:
            self.platform_optimized = {}
        if self.style_overrides is None:
            self.style_overrides = {}
        self.word_count = len(self.text.split())
        duration = self.end_time - self.start_time
        self.reading_speed = self.word_count / duration if duration > 0 else 0
    
    @property
    def duration(self) -> float:
        """Get the duration of this subtitle segment."""
        return self.end_time - self.start_time

class EnhancedSubtitleEngine(SubtitleEngine):
    """
    Enhanced subtitle engine with AI-powered optimizations and platform intelligence.
    Extends the base SubtitleEngine with Phase 2 features.
    """
    
    # Reading speed constants (words per second)
    OPTIMAL_READING_SPEED = 2.5  # Words per second for comfortable reading
    MIN_READING_SPEED = 1.5      # Minimum readable speed
    MAX_READING_SPEED = 4.0      # Maximum before becoming difficult
    
    # Platform-specific constraints
    PLATFORM_CONSTRAINTS = {
        'instagram_story': {
            'max_chars_per_line': 35,
            'max_lines': 2,
            'max_duration': 15.0,
            'font_size_ratio': 0.06,  # Relative to video height
            'safe_area': {'top': 0.15, 'bottom': 0.25, 'left': 0.1, 'right': 0.1}
        },
        'instagram_reel': {
            'max_chars_per_line': 40,
            'max_lines': 2,
            'max_duration': 90.0,
            'font_size_ratio': 0.055,
            'safe_area': {'top': 0.12, 'bottom': 0.2, 'left': 0.08, 'right': 0.08}
        },
        'tiktok': {
            'max_chars_per_line': 38,
            'max_lines': 2,
            'max_duration': 60.0,
            'font_size_ratio': 0.058,
            'safe_area': {'top': 0.15, 'bottom': 0.22, 'left': 0.06, 'right': 0.06}
        },
        'youtube_shorts': {
            'max_chars_per_line': 42,
            'max_lines': 2,
            'max_duration': 60.0,
            'font_size_ratio': 0.052,
            'safe_area': {'top': 0.1, 'bottom': 0.18, 'left': 0.05, 'right': 0.05}
        },
        'custom': {
            'max_chars_per_line': 50,
            'max_lines': 3,
            'max_duration': 300.0,
            'font_size_ratio': 0.05,
            'safe_area': {'top': 0.1, 'bottom': 0.15, 'left': 0.05, 'right': 0.05}
        }
    }
    
    def __init__(self):
        super().__init__()
        self.segments = []
        self.platform_preset = 'custom'
        
    def generate_intelligent_subtitles(
        self, 
        alignment_result: Dict[str, Any], 
        platform: str = 'custom',
        custom_options: Optional[Dict[str, Any]] = None
    ) -> List[SubtitleSegment]:
        """
        Generate subtitles with intelligent text processing and platform optimization.
        
        Args:
            alignment_result: Audio alignment data from the existing alignment system
            platform: Target platform (instagram_story, tiktok, etc.)
            custom_options: Override default platform settings
            
        Returns:
            List of optimized subtitle segments
        """
        try:
            # Get platform constraints
            constraints = self._get_platform_constraints(platform, custom_options)
            
            # Extract alignment tokens
            tokens = alignment_result.get('tokens', [])
            if not tokens:
                logger.warning("No alignment tokens found")
                return []
            
            # Generate base segments from alignment
            base_segments = self._create_base_segments_from_alignment(tokens)
            
            # Apply intelligent text processing
            optimized_segments = self._apply_intelligent_processing(base_segments, constraints)
            
            # Platform-specific optimizations
            platform_segments = self._optimize_for_platform(optimized_segments, platform, constraints)
            
            # Validate and adjust timing
            final_segments = self._validate_and_adjust_timing(platform_segments, constraints)
            
            self.segments = final_segments
            logger.info(f"Generated {len(final_segments)} intelligent subtitle segments for {platform}")
            
            return final_segments
            
        except Exception as e:
            logger.error(f"Intelligent subtitle generation failed: {e}")
            raise
    
    def _get_platform_constraints(self, platform: str, custom_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get platform constraints with custom overrides."""
        base_constraints = self.PLATFORM_CONSTRAINTS.get(platform, self.PLATFORM_CONSTRAINTS['custom']).copy()
        
        if custom_options:
            base_constraints.update(custom_options)
            
        return base_constraints
    
    def _create_base_segments_from_alignment(self, tokens: List[Dict[str, Any]]) -> List[SubtitleSegment]:
        """Create initial segments from alignment tokens."""
        segments = []
        
        for i, token in enumerate(tokens):
            segment = SubtitleSegment(
                id=f"seg_{i:03d}",
                text=token.get('word', '').strip(),
                start_time=token.get('start', 0.0),
                end_time=token.get('end', 0.0),
                confidence=token.get('confidence', 1.0)
            )
            
            if segment.text and segment.end_time > segment.start_time:
                segments.append(segment)
        
        return segments
    
    def _apply_intelligent_processing(
        self, 
        segments: List[SubtitleSegment], 
        constraints: Dict[str, Any]
    ) -> List[SubtitleSegment]:
        """Apply intelligent text processing for optimal readability."""
        
        # Group segments into readable chunks
        grouped_segments = self._group_segments_intelligently(segments, constraints)
        
        # Apply smart line breaking
        processed_segments = []
        for group in grouped_segments:
            processed_group = self._apply_smart_line_breaking(group, constraints)
            processed_segments.extend(processed_group)
        
        return processed_segments
    
    def _group_segments_intelligently(
        self, 
        segments: List[SubtitleSegment], 
        constraints: Dict[str, Any]
    ) -> List[List[SubtitleSegment]]:
        """Group segments based on reading speed and character limits."""
        groups = []
        current_group = []
        current_chars = 0
        current_duration = 0.0
        
        max_chars = constraints['max_chars_per_line'] * constraints['max_lines']
        
        for segment in segments:
            segment_chars = len(segment.text)
            segment_duration = segment.end_time - segment.start_time
            
            # Calculate reading speed if we add this segment
            total_chars = current_chars + segment_chars
            total_duration = current_duration + segment_duration
            reading_speed = (len(' '.join(s.text for s in current_group + [segment]).split()) / 
                           total_duration if total_duration > 0 else 0)
            
            # Check if we should start a new group
            should_group = (
                len(current_group) == 0 or  # First segment
                (total_chars <= max_chars and  # Within character limit
                 reading_speed <= self.MAX_READING_SPEED and  # Readable speed
                 reading_speed >= self.MIN_READING_SPEED and  # Not too slow
                 self._segments_are_contextually_related(current_group, segment))  # Contextual relation
            )
            
            if should_group:
                current_group.append(segment)
                current_chars = total_chars
                current_duration = total_duration
            else:
                # Finalize current group and start new one
                if current_group:
                    groups.append(current_group)
                current_group = [segment]
                current_chars = segment_chars
                current_duration = segment_duration
        
        # Add the last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _segments_are_contextually_related(
        self, 
        current_group: List[SubtitleSegment], 
        new_segment: SubtitleSegment
    ) -> bool:
        """Check if segments are contextually related and should be grouped."""
        if not current_group:
            return True
        
        # Check time gap between segments
        last_segment = current_group[-1]
        time_gap = new_segment.start_time - last_segment.end_time
        
        # If there's a significant pause, start new group
        if time_gap > 0.5:  # 500ms pause threshold
            return False
        
        # Check for sentence boundaries
        last_text = last_segment.text.strip()
        if last_text.endswith(('.', '!', '?', ':')):
            return False
        
        # Check for natural phrase boundaries
        if new_segment.text.lower() in ['and', 'but', 'or', 'so', 'then', 'now', 'well']:
            return False
        
        return True
    
    def _apply_smart_line_breaking(
        self, 
        group: List[SubtitleSegment], 
        constraints: Dict[str, Any]
    ) -> List[SubtitleSegment]:
        """Apply intelligent line breaking within a group."""
        if not group:
            return []
        
        # Combine text from group
        combined_text = ' '.join(segment.text for segment in group)
        start_time = group[0].start_time
        end_time = group[-1].end_time
        
        # Apply smart line breaking
        lines = self._break_text_intelligently(combined_text, constraints)
        
        # Create new segment with properly formatted text
        formatted_text = '\n'.join(lines)
        
        # Calculate confidence as average
        avg_confidence = sum(s.confidence for s in group) / len(group)
        
        new_segment = SubtitleSegment(
            id=f"group_{group[0].id}_{group[-1].id}",
            text=formatted_text,
            start_time=start_time,
            end_time=end_time,
            confidence=avg_confidence
        )
        
        return [new_segment]
    
    def _break_text_intelligently(self, text: str, constraints: Dict[str, Any]) -> List[str]:
        """Break text into lines using intelligent algorithms."""
        max_chars = constraints['max_chars_per_line']
        max_lines = constraints['max_lines']
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Check if adding this word would exceed line limit
            word_length = len(word) + (1 if current_line else 0)  # +1 for space
            
            if current_length + word_length <= max_chars:
                current_line.append(word)
                current_length += word_length
            else:
                # Finalize current line and start new one
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Check if we've reached max lines
                if len(lines) >= max_lines:
                    break
                
                current_line = [word]
                current_length = len(word)
        
        # Add the last line
        if current_line and len(lines) < max_lines:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _optimize_for_platform(
        self, 
        segments: List[SubtitleSegment], 
        platform: str, 
        constraints: Dict[str, Any]
    ) -> List[SubtitleSegment]:
        """Apply platform-specific optimizations."""
        optimized_segments = []
        
        for segment in segments:
            # Create platform-specific optimizations
            platform_data = {
                'font_size_ratio': constraints['font_size_ratio'],
                'safe_area': constraints['safe_area'],
                'max_duration': constraints.get('max_duration', 300.0),
                'style_preset': self._get_platform_style_preset(platform)
            }
            
            segment.platform_optimized[platform] = platform_data
            optimized_segments.append(segment)
        
        return optimized_segments
    
    def _get_platform_style_preset(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific styling presets."""
        presets = {
            'instagram_story': {
                'font_family': 'Inter',
                'font_weight': 'bold',
                'color': '#FFFFFF',
                'background_color': '#000000',
                'background_opacity': 0.7,
                'border_radius': 8,
                'padding': 12,
                'text_align': 'center',
                'position': 'bottom'
            },
            'instagram_reel': {
                'font_family': 'Inter',
                'font_weight': 'bold',
                'color': '#FFFFFF',
                'background_color': '#000000',
                'background_opacity': 0.6,
                'border_radius': 6,
                'padding': 10,
                'text_align': 'center',
                'position': 'bottom'
            },
            'tiktok': {
                'font_family': 'Inter',
                'font_weight': 'bold',
                'color': '#FFFFFF',
                'background_color': '#000000',
                'background_opacity': 0.8,
                'border_radius': 4,
                'padding': 8,
                'text_align': 'center',
                'position': 'bottom'
            },
            'youtube_shorts': {
                'font_family': 'Inter',
                'font_weight': 'bold',
                'color': '#FFFFFF',
                'background_color': '#000000',
                'background_opacity': 0.75,
                'border_radius': 6,
                'padding': 10,
                'text_align': 'center',
                'position': 'bottom'
            },
            'custom': {
                'font_family': 'Inter',
                'font_weight': 'normal',
                'color': '#FFFFFF',
                'background_color': '#000000',
                'background_opacity': 0.8,
                'border_radius': 4,
                'padding': 8,
                'text_align': 'center',
                'position': 'bottom'
            }
        }
        
        return presets.get(platform, presets['custom'])
    
    def _validate_and_adjust_timing(
        self, 
        segments: List[SubtitleSegment], 
        constraints: Dict[str, Any]
    ) -> List[SubtitleSegment]:
        """Validate timing and adjust for optimal readability."""
        adjusted_segments = []
        
        for segment in segments:
            # Calculate optimal duration based on reading speed
            word_count = len(segment.text.replace('\n', ' ').split())
            optimal_duration = word_count / self.OPTIMAL_READING_SPEED
            current_duration = segment.end_time - segment.start_time
            
            # Adjust duration if needed
            if current_duration < optimal_duration * 0.8:  # Too fast
                # Extend duration but respect next segment
                segment.end_time = min(
                    segment.start_time + optimal_duration,
                    segment.end_time + 0.5  # Max 500ms extension
                )
            elif current_duration > optimal_duration * 1.5:  # Too slow
                # Reduce duration but maintain minimum
                min_duration = word_count / self.MAX_READING_SPEED
                segment.end_time = max(
                    segment.start_time + min_duration,
                    segment.end_time - 0.3  # Max 300ms reduction
                )
            
            adjusted_segments.append(segment)
        
        # Resolve overlaps
        return self._resolve_timing_overlaps(adjusted_segments)
    
    def _resolve_timing_overlaps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Resolve timing overlaps between segments."""
        if len(segments) <= 1:
            return segments
        
        resolved_segments = []
        
        for i, segment in enumerate(segments):
            if i == 0:
                resolved_segments.append(segment)
                continue
            
            prev_segment = resolved_segments[-1]
            
            # Check for overlap
            if segment.start_time < prev_segment.end_time:
                # Resolve by adjusting the boundary
                midpoint = (prev_segment.end_time + segment.start_time) / 2
                prev_segment.end_time = midpoint
                segment.start_time = midpoint
            
            resolved_segments.append(segment)
        
        return resolved_segments
    
    def export_enhanced_subtitles(
        self, 
        format: str = 'srt',
        platform_optimized: bool = True
    ) -> str:
        """Export subtitles with enhanced features."""
        if format.lower() == 'srt':
            return self._export_srt_enhanced()
        elif format.lower() == 'vtt':
            return self._export_vtt_enhanced()
        elif format.lower() == 'ass':
            return self._export_ass_enhanced(platform_optimized)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_srt_enhanced(self) -> str:
        """Export enhanced SRT with reading speed optimization."""
        srt_content = []
        
        for i, segment in enumerate(self.segments, 1):
            start_time = self._format_srt_time(segment.start_time)
            end_time = self._format_srt_time(segment.end_time)
            
            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(segment.text)
            srt_content.append("")  # Empty line separator
        
        return '\n'.join(srt_content)
    
    def _export_ass_enhanced(self, platform_optimized: bool = True) -> str:
        """Export enhanced ASS with platform-specific styling."""
        # ASS header
        ass_content = [
            "[Script Info]",
            "Title: Enhanced Subtitles",
            f"ScriptType: v4.00+",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ]
        
        # Add platform-specific styles
        if platform_optimized and self.segments:
            platform_data = self.segments[0].platform_optimized.get(self.platform_preset, {})
            style_preset = platform_data.get('style_preset', {})
            
            # Convert colors to ASS format (BGR)
            primary_color = self._hex_to_ass_color(style_preset.get('color', '#FFFFFF'))
            back_color = self._hex_to_ass_color(style_preset.get('background_color', '#000000'))
            
            ass_content.append(
                f"Style: Default,{style_preset.get('font_family', 'Inter')},20,{primary_color},"
                f"&Hffffff,&H0,{back_color},0,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1"
            )
        else:
            ass_content.append("Style: Default,Inter,20,&Hffffff,&Hffffff,&H0,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1")
        
        ass_content.extend([
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ])
        
        # Add subtitle events
        for segment in self.segments:
            start_time = self._format_ass_time(segment.start_time)
            end_time = self._format_ass_time(segment.end_time)
            text = segment.text.replace('\n', '\\N')
            
            ass_content.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")
        
        return '\n'.join(ass_content)
    
    def _hex_to_ass_color(self, hex_color: str) -> str:
        """Convert hex color to ASS BGR format."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            hex_color = 'FFFFFF'
        
        # Convert RGB to BGR for ASS
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        
        return f"&H{b}{g}{r}"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the generated subtitles."""
        if not self.segments:
            return {}
        
        total_duration = sum(s.end_time - s.start_time for s in self.segments)
        total_words = sum(len(s.text.replace('\n', ' ').split()) for s in self.segments)
        avg_reading_speed = total_words / total_duration if total_duration > 0 else 0
        avg_confidence = sum(s.confidence for s in self.segments) / len(self.segments)
        
        return {
            'total_segments': len(self.segments),
            'total_duration': total_duration,
            'total_words': total_words,
            'average_reading_speed_wps': avg_reading_speed,
            'average_confidence': avg_confidence,
            'optimal_reading_speed': self.OPTIMAL_READING_SPEED,
            'readability_score': min(100, (self.OPTIMAL_READING_SPEED / max(avg_reading_speed, 0.1)) * 100),
            'platform_preset': self.platform_preset
        }