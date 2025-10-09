"""
Subtitle Engine for Face Sequencer Pro
Generates and manages subtitles for video content with social media optimization
"""

import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import timedelta
import tempfile
import subprocess
from pathlib import Path

from app.core.audio.audio_aligner import AudioAligner, AlignmentResult, AlignmentToken


@dataclass
class SubtitleSegment:
    """Represents a single subtitle segment with timing and styling"""
    id: int
    text: str
    start_ms: float
    end_ms: float
    confidence: float = 1.0
    style: Optional[Dict[str, Any]] = None


@dataclass
class SubtitleStyle:
    """Subtitle styling configuration"""
    font_family: str = "Arial, sans-serif"
    font_size: int = 24
    font_weight: str = "bold"
    text_color: str = "#ffffff"
    background_color: str = "#000000"
    background_opacity: float = 0.7
    outline_color: str = "#000000"
    outline_width: int = 2
    vertical_position: str = "bottom"  # top, center, bottom
    horizontal_align: str = "center"  # left, center, right
    max_width: int = 80  # percentage
    line_height: float = 1.2
    padding: int = 8


@dataclass 
class PlatformPreset:
    """Platform-specific subtitle optimization preset"""
    name: str
    aspect_ratio: str  # "16:9", "9:16", "1:1"
    resolution: Tuple[int, int]  # (width, height)
    max_duration: int  # seconds
    style: SubtitleStyle
    safe_area_margin: int = 20  # pixels from edges


class SubtitleEngine:
    """Main subtitle generation and management engine"""
    
    def __init__(self, audio_aligner: Optional[AudioAligner] = None):
        self.audio_aligner = audio_aligner or AudioAligner()
        self.platform_presets = self._initialize_presets()
        
    def _initialize_presets(self) -> Dict[str, PlatformPreset]:
        """Initialize platform-specific presets"""
        return {
            'instagram-story': PlatformPreset(
                name="Instagram Story",
                aspect_ratio="9:16",
                resolution=(1080, 1920),
                max_duration=60,
                style=SubtitleStyle(
                    font_size=32,
                    font_weight="bold",
                    background_opacity=0.6,
                    outline_width=2,
                    max_width=85
                )
            ),
            'instagram-reel': PlatformPreset(
                name="Instagram Reel",
                aspect_ratio="9:16", 
                resolution=(1080, 1920),
                max_duration=90,
                style=SubtitleStyle(
                    font_size=28,
                    font_weight="600",
                    background_opacity=0.7,
                    outline_width=2,
                    max_width=90
                )
            ),
            'tiktok': PlatformPreset(
                name="TikTok",
                aspect_ratio="9:16",
                resolution=(1080, 1920),
                max_duration=60,
                style=SubtitleStyle(
                    font_size=36,
                    font_weight="bold", 
                    background_opacity=0.5,
                    outline_width=3,
                    max_width=80
                )
            ),
            'youtube-shorts': PlatformPreset(
                name="YouTube Shorts",
                aspect_ratio="9:16",
                resolution=(1080, 1920),
                max_duration=60,
                style=SubtitleStyle(
                    font_size=30,
                    font_weight="bold",
                    background_opacity=0.65,
                    outline_width=2,
                    max_width=85
                )
            ),
            'youtube-landscape': PlatformPreset(
                name="YouTube Landscape", 
                aspect_ratio="16:9",
                resolution=(1920, 1080),
                max_duration=0,  # no limit
                style=SubtitleStyle(
                    font_size=24,
                    font_weight="600",
                    background_opacity=0.8,
                    outline_width=1,
                    max_width=70,
                    vertical_position="bottom"
                )
            )
        }
    
    def generate_subtitles_from_alignment(
        self, 
        alignment_result: AlignmentResult,
        max_chars_per_line: int = 40,
        max_duration_ms: int = 3000,
        min_duration_ms: int = 500
    ) -> List[SubtitleSegment]:
        """Convert audio alignment result to subtitle segments"""
        
        if not alignment_result or not alignment_result.tokens:
            raise ValueError("Invalid alignment result provided")
            
        print(f"[CLAPPER] Converting {len(alignment_result.tokens)} tokens to subtitles")
        
        subtitles = []
        current_subtitle = None
        segment_id = 0
        
        for token in alignment_result.tokens:
            # Handle gap tokens as hard boundaries between phrases
            if getattr(token.type, 'value', '') == 'gap':
                # Finalize current subtitle if there is a meaningful pause
                gap_duration = max(0, token.end_ms - token.start_ms)
                if current_subtitle and gap_duration >= 80:
                    if (current_subtitle.end_ms - current_subtitle.start_ms) < min_duration_ms:
                        current_subtitle.end_ms = current_subtitle.start_ms + min_duration_ms
                    subtitles.append(current_subtitle)
                    current_subtitle = None
                continue

            if token.type.value == 'word' and token.text.strip():
                # If this token is only punctuation like '!' and we already have a current subtitle,
                # attach it to the current subtitle instead of starting a new one.
                if re.fullmatch(r"[!?.…]+", token.text.strip()):
                    if current_subtitle:
                        current_subtitle.text = (current_subtitle.text.rstrip() + token.text.strip())
                        current_subtitle.end_ms = token.end_ms
                        current_subtitle.confidence = min(
                            current_subtitle.confidence,
                            getattr(token, 'confidence', 1.0)
                        )
                        continue
                
                # Check if we should start a new subtitle
                should_start_new = (
                    current_subtitle is None or
                    (token.start_ms - current_subtitle.start_ms) > max_duration_ms or
                    (len(current_subtitle.text) + len(token.text) + 1) > max_chars_per_line or
                    self._is_sentence_boundary(current_subtitle.text, token.text)
                )
                
                if should_start_new:
                    # Finalize previous subtitle
                    if current_subtitle:
                        # Ensure minimum duration
                        if (current_subtitle.end_ms - current_subtitle.start_ms) < min_duration_ms:
                            current_subtitle.end_ms = current_subtitle.start_ms + min_duration_ms
                            
                        subtitles.append(current_subtitle)
                    
                    # Start new subtitle
                    current_subtitle = SubtitleSegment(
                        id=segment_id,
                        text=token.text.strip(),
                        start_ms=token.start_ms,
                        end_ms=token.end_ms,
                        confidence=getattr(token, 'confidence', 1.0)
                    )
                    segment_id += 1
                    
                else:
                    # Extend current subtitle
                    current_subtitle.text += ' ' + token.text.strip()
                    current_subtitle.end_ms = token.end_ms
                    current_subtitle.confidence = min(
                        current_subtitle.confidence,
                        getattr(token, 'confidence', 1.0)
                    )
        
        # Add final subtitle
        if current_subtitle:
            if (current_subtitle.end_ms - current_subtitle.start_ms) < min_duration_ms:
                current_subtitle.end_ms = current_subtitle.start_ms + min_duration_ms
            subtitles.append(current_subtitle)
        
        # POST-PROCESSING: AGGRESSIVELY eliminate ALL gaps
        # User reported: gaps are MINIMAL in audio, so extend ALL subtitles to meet next
        gaps_eliminated = 0
        gaps_split = 0
        
        for i in range(len(subtitles) - 1):
            current = subtitles[i]
            next_sub = subtitles[i + 1]
            gap = next_sub.start_ms - current.end_ms
            
            if gap > 0:
                # ANY gap less than 1 second = eliminate completely
                if gap < 1000:
                    # Extend current to meet next exactly
                    current.end_ms = next_sub.start_ms
                    gaps_eliminated += 1
                # Only very large gaps (1+ second) get split
                elif gap >= 1000:
                    midpoint = current.end_ms + (gap / 2)
                    current.end_ms = midpoint
                    next_sub.start_ms = midpoint
                    gaps_split += 1
        
        print(f"[CHECK] Generated {len(subtitles)} subtitle segments")
        print(f"[CHECK] Gaps eliminated: {gaps_eliminated}, Gaps split: {gaps_split}")
        
        # POST-PROCESSING 2: Merge subtitles that are too short or grammatically incomplete
        subtitles = self._merge_incomplete_subtitles(subtitles, max_chars_per_line, max_duration_ms)
        
        print(f"[CHECK] Final: {len(subtitles)} subtitle segments after merging")
        return subtitles
    
    def _merge_incomplete_subtitles(self, subtitles: List[SubtitleSegment], 
                                    max_chars_per_line: int, 
                                    max_duration_ms: int) -> List[SubtitleSegment]:
        """Merge subtitles that end with incomplete phrases"""
        if len(subtitles) <= 1:
            return subtitles
        
        merged = []
        i = 0
        merges_done = 0
        
        while i < len(subtitles):
            current = subtitles[i]
            
            # Check if we should merge with next subtitle
            if i < len(subtitles) - 1:
                next_sub = subtitles[i + 1]
                
                # Merge if:
                # 1. Current ends with incomplete phrase (article, preposition, etc.)
                # 2. Combined length still fits in max_chars_per_line
                # 3. Combined duration is reasonable
                should_merge = (
                    self._should_continue_phrase(current.text, next_sub.text) and
                    (len(current.text) + len(next_sub.text) + 1) <= max_chars_per_line and
                    (next_sub.end_ms - current.start_ms) <= max_duration_ms * 1.5
                )
                
                if should_merge:
                    # Merge current with next
                    merged_text = f"{current.text} {next_sub.text}"
                    merged_segment = SubtitleSegment(
                        id=current.id,
                        text=merged_text,
                        start_ms=current.start_ms,
                        end_ms=next_sub.end_ms,
                        confidence=min(current.confidence, next_sub.confidence),
                        style=current.style
                    )
                    merged.append(merged_segment)
                    merges_done += 1
                    i += 2  # Skip next since we merged it
                    continue
            
            # No merge, just add current
            merged.append(current)
            i += 1
        
        # Renumber IDs
        for idx, sub in enumerate(merged):
            sub.id = idx
        
        if merges_done > 0:
            print(f"[CHECK] Merged {merges_done} incomplete subtitles")
        
        return merged
    
    def _should_continue_phrase(self, current_text: str, next_word: str) -> bool:
        """Check if next word MUST be included with current phrase (grammatically incomplete)"""
        
        # Palavras que NUNCA devem terminar uma frase (artigos, preposições, pronomes, etc.)
        # Portuguese: articles, prepositions, pronouns that need continuation
        INCOMPLETE_ENDINGS = {
            # Artigos
            'O', 'A', 'OS', 'AS', 'UM', 'UMA', 'UNS', 'UMAS',
            # Preposições
            'DE', 'DO', 'DA', 'DOS', 'DAS', 'EM', 'NO', 'NA', 'NOS', 'NAS',
            'POR', 'PELO', 'PELA', 'PELOS', 'PELAS', 'PARA', 'PRO', 'PRA',
            'COM', 'SEM', 'SOB', 'SOBRE', 'ATÉ', 'DESDE', 'ENTRE',
            # Conjunções
            'E', 'OU', 'MAS', 'PORÉM', 'CONTUDO', 'ENTRETANTO', 'QUE', 'SE',
            # Pronomes
            'MEU', 'MIM', 'TUA', 'TEU', 'SEU', 'SUA', 'ESSE', 'ESSA', 'ESTE', 'ESTA',
            'AQUELE', 'AQUELA', 'DELE', 'DELA', 'DELES', 'DELAS',
            # Verbos auxiliares comuns
            'É', 'SÃO', 'ERA', 'ERAM', 'FOI', 'FORAM', 'SER', 'ESTAR',
            'TEM', 'TÊM', 'TINHA', 'TINHAM', 'VAI', 'VÃO', 'IA', 'QUER',
            # Determinantes
            'TODO', 'TODA', 'TODOS', 'TODAS', 'MUITO', 'MUITA', 'POUCO', 'POUCA',
            'ALGUM', 'ALGUMA', 'NENHUM', 'NENHUMA', 'CADA', 'OUTRO', 'OUTRA'
        }
        
        # Get last word(s) of current text
        words = current_text.upper().strip().split()
        if not words:
            return False
        
        last_word = words[-1].strip(',.!?;:')
        
        # Check if last word requires continuation
        if last_word in INCOMPLETE_ENDINGS:
            return True
        
        # Check for incomplete two-word phrases like "É UM", "FOI O", "TEM A"
        if len(words) >= 2:
            last_two = f"{words[-2].strip(',.!?;:')} {last_word}"
            if last_two in ['É UM', 'É UMA', 'É O', 'É A', 'SÃO OS', 'SÃO AS',
                           'FOI O', 'FOI A', 'ERAM OS', 'ERAM AS',
                           'TEM UM', 'TEM UMA', 'TEM O', 'TEM A',
                           'VAI SER', 'VAI TER', 'VÃO SER', 'VÃO TER']:
                return True
        
        return False
    
    def _is_sentence_boundary(self, current_text: str, next_word: str) -> bool:
        """Check if there should be a sentence boundary between current text and next word"""
        if not current_text:
            return False
        
        # NEVER break if current phrase is grammatically incomplete
        if self._should_continue_phrase(current_text, next_word):
            return False
            
        # Check for sentence ending punctuation
        sentence_endings = ['.', '!', '?', '...']
        for ending in sentence_endings:
            if current_text.rstrip().endswith(ending):
                return True
                
        # Check for paragraph breaks (double newlines)
        if '\n\n' in current_text or '\n\n' in next_word:
            return True
            
        return False
    
    def split_text_into_segments(
        self,
        text: str,
        total_duration_ms: float,
        max_chars_per_line: int = 40,
        max_duration_ms: int = 3000
    ) -> List[SubtitleSegment]:
        """Split plain text into subtitle segments with estimated timing"""
        
        # Clean and prepare text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # Calculate average time per character
        time_per_char = total_duration_ms / len(text)
        
        subtitles = []
        current_time = 0.0
        segment_id = 0
        
        for sentence in sentences:
            # Further split long sentences
            chunks = self._split_by_length(sentence, max_chars_per_line)
            
            for chunk in chunks:
                if not chunk.strip():
                    continue
                    
                # Calculate duration based on text length and reading speed
                estimated_duration = max(
                    len(chunk) * time_per_char,
                    1000  # minimum 1 second
                )
                estimated_duration = min(estimated_duration, max_duration_ms)
                
                subtitle = SubtitleSegment(
                    id=segment_id,
                    text=chunk.strip(),
                    start_ms=current_time,
                    end_ms=current_time + estimated_duration,
                    confidence=0.8  # Estimated timing
                )
                
                subtitles.append(subtitle)
                current_time += estimated_duration + 200  # Small gap between subtitles
                segment_id += 1
        
        print(f"[CHECK] Split text into {len(subtitles)} estimated segments")
        return subtitles
    
    def _split_by_length(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks by length, respecting word boundaries"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = ""
        
        for word in words:
            if len(current_chunk + " " + word) <= max_length:
                current_chunk += (" " + word) if current_chunk else word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def optimize_for_platform(
        self, 
        subtitles: List[SubtitleSegment], 
        platform_preset: str
    ) -> Tuple[List[SubtitleSegment], SubtitleStyle]:
        """Optimize subtitle segments for specific platform"""
        
        if platform_preset not in self.platform_presets:
            raise ValueError(f"Unknown platform preset: {platform_preset}")
        
        preset = self.platform_presets[platform_preset]
        
        # Apply platform-specific optimizations
        optimized_subtitles = []
        
        for subtitle in subtitles:
            # Adjust duration for platform limits
            duration_ms = subtitle.end_ms - subtitle.start_ms
            
            # Platform-specific text length limits
            if platform_preset == 'tiktok':
                max_chars = 30  # TikTok prefers shorter text
            elif platform_preset.startswith('instagram'):
                max_chars = 35  # Instagram optimal length
            else:
                max_chars = 40  # Default
            
            # Split if too long
            if len(subtitle.text) > max_chars:
                # Try to split at word boundaries
                words = subtitle.text.split()
                mid_point = len(words) // 2
                
                first_half = ' '.join(words[:mid_point])
                second_half = ' '.join(words[mid_point:])
                
                # Create two segments
                split_duration = duration_ms / 2
                
                optimized_subtitles.append(SubtitleSegment(
                    id=len(optimized_subtitles),
                    text=first_half,
                    start_ms=subtitle.start_ms,
                    end_ms=subtitle.start_ms + split_duration,
                    confidence=subtitle.confidence,
                    style=asdict(preset.style)
                ))
                
                optimized_subtitles.append(SubtitleSegment(
                    id=len(optimized_subtitles),
                    text=second_half,
                    start_ms=subtitle.start_ms + split_duration,
                    end_ms=subtitle.end_ms,
                    confidence=subtitle.confidence,
                    style=asdict(preset.style)
                ))
            else:
                # Keep original with platform style
                optimized_subtitle = SubtitleSegment(
                    id=len(optimized_subtitles),
                    text=subtitle.text,
                    start_ms=subtitle.start_ms,
                    end_ms=subtitle.end_ms,
                    confidence=subtitle.confidence,
                    style=asdict(preset.style)
                )
                optimized_subtitles.append(optimized_subtitle)
        
        print(f"[CHECK] Optimized subtitles for {preset.name}: {len(optimized_subtitles)} segments")
        return optimized_subtitles, preset.style
    
    def export_to_srt(self, subtitles: List[SubtitleSegment], output_path: str) -> str:
        """Export subtitles to SRT format"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, subtitle in enumerate(subtitles):
                # SRT format: 1-indexed
                f.write(f"{i + 1}\n")
                
                # Time format: HH:MM:SS,mmm --> HH:MM:SS,mmm
                start_time = self._ms_to_srt_time(subtitle.start_ms)
                end_time = self._ms_to_srt_time(subtitle.end_ms)
                f.write(f"{start_time} --> {end_time}\n")
                
                # Text content
                f.write(f"{subtitle.text}\n\n")
        
        print(f"[CHECK] Exported {len(subtitles)} subtitles to SRT: {output_path}")
        return output_path
    
    def export_to_vtt(self, subtitles: List[SubtitleSegment], output_path: str) -> str:
        """Export subtitles to WebVTT format"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for subtitle in subtitles:
                # VTT time format: HH:MM:SS.mmm --> HH:MM:SS.mmm
                start_time = self._ms_to_vtt_time(subtitle.start_ms)
                end_time = self._ms_to_vtt_time(subtitle.end_ms)
                f.write(f"{start_time} --> {end_time}\n")
                
                # Text with optional styling
                if subtitle.style:
                    # Add VTT styling cues if needed
                    f.write(f"{subtitle.text}\n\n")
                else:
                    f.write(f"{subtitle.text}\n\n")
        
        print(f"[CHECK] Exported {len(subtitles)} subtitles to VTT: {output_path}")
        return output_path
    
    def _ms_to_srt_time(self, ms: float) -> str:
        """Convert milliseconds to SRT time format (HH:MM:SS,mmm)"""
        total_seconds = int(ms // 1000)
        milliseconds = int(ms % 1000)
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _ms_to_vtt_time(self, ms: float) -> str:
        """Convert milliseconds to VTT time format (HH:MM:SS.mmm)"""
        srt_time = self._ms_to_srt_time(ms)
        return srt_time.replace(',', '.')
    
    def validate_subtitles(self, subtitles: List[SubtitleSegment]) -> Dict[str, Any]:
        """Validate subtitle segments for common issues"""
        
        issues = []
        warnings = []
        
        for i, subtitle in enumerate(subtitles):
            # Check duration
            duration_ms = subtitle.end_ms - subtitle.start_ms
            if duration_ms < 500:
                warnings.append(f"Segment {i+1}: Very short duration ({duration_ms:.0f}ms)")
            elif duration_ms > 5000:
                warnings.append(f"Segment {i+1}: Long duration ({duration_ms:.0f}ms)")
            
            # Check text length
            if len(subtitle.text) > 50:
                warnings.append(f"Segment {i+1}: Long text ({len(subtitle.text)} chars)")
            elif len(subtitle.text) < 3:
                issues.append(f"Segment {i+1}: Very short text")
            
            # Check timing overlaps
            if i > 0:
                prev_subtitle = subtitles[i-1]
                if subtitle.start_ms < prev_subtitle.end_ms:
                    issues.append(f"Segment {i+1}: Overlaps with previous segment")
            
            # Check confidence
            if subtitle.confidence < 0.5:
                warnings.append(f"Segment {i+1}: Low confidence ({subtitle.confidence:.2f})")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_segments': len(subtitles),
            'total_duration_ms': subtitles[-1].end_ms if subtitles else 0
        }


def test_subtitle_engine():
    """Test the subtitle engine with sample data"""
    
    # Create test alignment tokens
    from app.core.audio.audio_aligner import AlignmentToken, TokenType
    
    test_tokens = [
        AlignmentToken(
            type=TokenType.WORD,
            text="Hello",
            viseme="H",
            start_ms=0,
            end_ms=500,
            confidence=0.95,
            lang="en"
        ),
        AlignmentToken(
            type=TokenType.WORD,
            text="world",
            viseme="W",
            start_ms=600,
            end_ms=1000,
            confidence=0.92,
            lang="en"
        ),
        AlignmentToken(
            type=TokenType.WORD,
            text="this",
            viseme="TH",
            start_ms=1200,
            end_ms=1600,
            confidence=0.89,
            lang="en"
        ),
        AlignmentToken(
            type=TokenType.WORD,
            text="is",
            viseme="I",
            start_ms=1700,
            end_ms=1900,
            confidence=0.94,
            lang="en"
        ),
        AlignmentToken(
            type=TokenType.WORD,
            text="a",
            viseme="A",
            start_ms=2000,
            end_ms=2100,
            confidence=0.88,
            lang="en"
        ),
        AlignmentToken(
            type=TokenType.WORD,
            text="test",
            viseme="T",
            start_ms=2200,
            end_ms=2600,
            confidence=0.91,
            lang="en"
        )
    ]
    
    # Create test alignment result
    from app.core.audio.audio_aligner import AlignmentStats
    test_stats = AlignmentStats(
        total_tokens=len(test_tokens),
        word_tokens=len(test_tokens),
        gap_tokens=0,
        avg_confidence=0.9,
        total_duration=2.6,
        word_coverage=1.0
    )
    
    test_alignment = AlignmentResult(
        language="en",
        sample_rate=16000,
        tokens=test_tokens,
        stats=test_stats
    )
    
    # Test subtitle engine
    engine = SubtitleEngine()
    
    print("🧪 Testing Subtitle Engine...")
    
    # Test subtitle generation
    subtitles = engine.generate_subtitles_from_alignment(test_alignment)
    print(f"Generated {len(subtitles)} subtitles:")
    for sub in subtitles:
        print(f"  {sub.start_ms:.0f}-{sub.end_ms:.0f}ms: '{sub.text}'")
    
    # Test platform optimization
    optimized, style = engine.optimize_for_platform(subtitles, 'tiktok')
    print(f"Optimized for TikTok: {len(optimized)} segments")
    
    # Test validation
    validation = engine.validate_subtitles(subtitles)
    print(f"Validation: {'[CHECK] Valid' if validation['valid'] else '[X] Issues'}")
    if validation['warnings']:
        print(f"Warnings: {len(validation['warnings'])}")
    
    # Test export
    with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as f:
        srt_path = engine.export_to_srt(subtitles, f.name)
        print(f"SRT exported to: {srt_path}")
    
    print("[CHECK] Subtitle Engine test completed")


if __name__ == "__main__":
    test_subtitle_engine()