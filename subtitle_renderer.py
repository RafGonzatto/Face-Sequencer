"""
Subtitle Renderer for Face Sequencer Pro
Handles video subtitle overlay rendering and export using FFmpeg
"""

import os
import json
import subprocess
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re

from subtitle_engine import SubtitleSegment, SubtitleStyle, PlatformPreset


class SubtitleRenderer:
    """Handles rendering subtitles onto video using FFmpeg"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.temp_dir = tempfile.mkdtemp(prefix="subtitle_render_")
        
        # Verify FFmpeg is available
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self):
        """Verify FFmpeg is available and get version info"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"✅ FFmpeg available: {self.ffmpeg_path}")
            else:
                raise RuntimeError("FFmpeg not responding correctly")
        except Exception as e:
            print(f"❌ FFmpeg not found at {self.ffmpeg_path}: {e}")
            raise RuntimeError(f"FFmpeg required for subtitle rendering: {e}")
    
    def render_subtitles_on_video(
        self,
        input_video_path: str,
        subtitles: List[SubtitleSegment],
        style: SubtitleStyle,
        output_video_path: str,
        preset: Optional[PlatformPreset] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """Render subtitles onto video using FFmpeg"""
        
        print(f"🎬 Rendering {len(subtitles)} subtitles onto video...")
        print(f"   Input: {input_video_path}")
        print(f"   Output: {output_video_path}")
        
        try:
            # Generate ASS subtitle file for advanced styling
            ass_file = self._generate_ass_subtitles(subtitles, style, preset)
            
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(
                input_video_path, 
                ass_file, 
                output_video_path,
                preset
            )
            
            print(f"🔧 FFmpeg command: {' '.join(cmd[:3])} ... (truncated)")
            
            # Execute FFmpeg with progress tracking
            success = self._execute_ffmpeg_with_progress(cmd, progress_callback)
            
            if success and os.path.exists(output_video_path):
                file_size = os.path.getsize(output_video_path) / (1024 * 1024)  # MB
                print(f"✅ Video with subtitles rendered successfully ({file_size:.1f} MB)")
                return output_video_path
            else:
                raise RuntimeError("FFmpeg rendering failed or output file not created")
                
        except Exception as e:
            print(f"❌ Subtitle rendering failed: {e}")
            raise
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files()
    
    def _generate_ass_subtitles(
        self, 
        subtitles: List[SubtitleSegment], 
        style: SubtitleStyle,
        preset: Optional[PlatformPreset] = None
    ) -> str:
        """Generate ASS (Advanced SSA) subtitle file for precise styling"""
        
        ass_file = os.path.join(self.temp_dir, "subtitles.ass")
        
        # ASS header with style definitions
        ass_content = self._generate_ass_header(style, preset)
        
        # Add subtitle events
        ass_content += "\n[Events]\n"
        ass_content += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        
        for subtitle in subtitles:
            start_time = self._ms_to_ass_time(subtitle.start_ms)
            end_time = self._ms_to_ass_time(subtitle.end_ms)
            
            # Clean and escape text for ASS format
            text = self._escape_ass_text(subtitle.text)
            
            # Apply any segment-specific styling
            if subtitle.style:
                # Override default style with segment-specific style
                text = self._apply_ass_overrides(text, subtitle.style)
            
            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
        
        # Write ASS file
        with open(ass_file, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        print(f"📝 Generated ASS subtitle file: {ass_file}")
        return ass_file
    
    def _generate_ass_header(self, style: SubtitleStyle, preset: Optional[PlatformPreset]) -> str:
        """Generate ASS file header with style definitions"""
        
        # Determine video resolution for positioning
        if preset:
            video_width, video_height = preset.resolution
        else:
            video_width, video_height = 1920, 1080  # Default HD
        
        # Convert style to ASS format
        font_size = int(style.font_size * (video_height / 1080))  # Scale font for resolution
        
        # Parse colors (ASS uses BGR format)
        primary_color = self._hex_to_ass_color(style.text_color)
        outline_color = self._hex_to_ass_color(style.outline_color)
        back_color = self._hex_to_ass_color(style.background_color)
        
        # Calculate positioning
        if style.vertical_position == "top":
            alignment = 8  # Top center
            margin_v = 20
        elif style.vertical_position == "center":
            alignment = 5  # Middle center
            margin_v = 0
        else:  # bottom
            alignment = 2  # Bottom center
            margin_v = 20
        
        if style.horizontal_align == "left":
            alignment = alignment - 1 if alignment > 1 else alignment
        elif style.horizontal_align == "right":
            alignment = alignment + 1 if alignment < 9 else alignment
        
        # Calculate alpha for background
        bg_alpha = int((1.0 - style.background_opacity) * 255)
        
        ass_header = f"""[Script Info]
Title: Face Sequencer Pro Subtitles
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_family.split(',')[0]},{font_size},{primary_color},{primary_color},{outline_color},{back_color}{bg_alpha:02X},{"1" if "bold" in style.font_weight.lower() else "0"},0,0,0,100,100,0,0,1,{style.outline_width},1,{alignment},10,10,{margin_v},1
"""
        
        return ass_header
    
    def _hex_to_ass_color(self, hex_color: str) -> str:
        """Convert hex color to ASS BGR format"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # ASS uses BGR format with &H prefix
        return f"&H00{b:02X}{g:02X}{r:02X}"
    
    def _ms_to_ass_time(self, ms: float) -> str:
        """Convert milliseconds to ASS time format (H:MM:SS.CC)"""
        total_seconds = ms / 1000.0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        
        return f"{hours}:{minutes:02d}:{seconds:05.2f}"
    
    def _escape_ass_text(self, text: str) -> str:
        """Escape text for ASS format"""
        # Replace newlines with ASS line breaks
        text = text.replace('\n', '\\N')
        # Escape ASS special characters
        text = text.replace('{', '\\{').replace('}', '\\}')
        return text
    
    def _apply_ass_overrides(self, text: str, style_overrides: Dict[str, Any]) -> str:
        """Apply ASS style overrides to text"""
        # This could be extended to handle per-segment style overrides
        # For now, return text as-is since we handle styling in the header
        return text
    
    def _build_ffmpeg_command(
        self,
        input_video: str,
        ass_file: str,
        output_video: str,
        preset: Optional[PlatformPreset] = None
    ) -> List[str]:
        """Build FFmpeg command for subtitle rendering"""
        
        cmd = [
            self.ffmpeg_path,
            "-i", input_video,
            "-vf", f"ass={ass_file}",
            "-c:v", "libx264",
            "-c:a", "copy",  # Copy audio without re-encoding
            "-preset", "medium",
            "-crf", "23",
        ]
        
        # Apply platform-specific encoding settings
        if preset:
            if preset.aspect_ratio == "9:16":
                # Vertical video optimizations
                cmd.extend(["-profile:v", "high", "-level:v", "4.0"])
            
            # Add resolution scaling if needed
            width, height = preset.resolution
            cmd.extend(["-s", f"{width}x{height}"])
        
        # Output settings
        cmd.extend([
            "-movflags", "+faststart",  # Optimize for streaming
            "-y",  # Overwrite output file
            output_video
        ])
        
        return cmd
    
    def _execute_ffmpeg_with_progress(
        self, 
        cmd: List[str], 
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Execute FFmpeg command with progress tracking"""
        
        try:
            # Run FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Track progress if callback provided
            if progress_callback:
                self._track_ffmpeg_progress(process, progress_callback)
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                print("✅ FFmpeg rendering completed successfully")
                return True
            else:
                print(f"❌ FFmpeg failed with return code {process.returncode}")
                print(f"   stderr: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing FFmpeg: {e}")
            return False
    
    def _track_ffmpeg_progress(self, process: subprocess.Popen, callback: callable):
        """Track FFmpeg progress by parsing stderr output"""
        
        duration_pattern = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        progress_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        
        total_duration = None
        
        try:
            for line in iter(process.stderr.readline, ''):
                line = line.strip()
                
                # Extract total duration
                if not total_duration:
                    duration_match = duration_pattern.search(line)
                    if duration_match:
                        h, m, s, cs = duration_match.groups()
                        total_duration = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
                
                # Extract current progress
                if total_duration:
                    progress_match = progress_pattern.search(line)
                    if progress_match:
                        h, m, s, cs = progress_match.groups()
                        current_time = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
                        
                        progress_percent = min(100.0, (current_time / total_duration) * 100)
                        callback(progress_percent, f"Rendering: {progress_percent:.1f}%")
                        
        except Exception as e:
            print(f"⚠️ Progress tracking error: {e}")
    
    def create_subtitle_preview(
        self,
        subtitles: List[SubtitleSegment],
        style: SubtitleStyle,
        video_resolution: Tuple[int, int] = (1920, 1080),
        output_path: Optional[str] = None
    ) -> str:
        """Create a preview image showing subtitle styling"""
        
        if not output_path:
            output_path = os.path.join(self.temp_dir, "subtitle_preview.png")
        
        width, height = video_resolution
        
        # Create a simple preview using FFmpeg
        preview_cmd = [
            self.ffmpeg_path,
            "-f", "lavfi",
            "-i", f"color=c=black:size={width}x{height}:duration=1",
            "-vf", f"drawtext=text='Sample Subtitle Text':fontfile={self._get_system_font()}:fontsize={style.font_size}:fontcolor={style.text_color}:x=(w-text_w)/2:y=h-th-50",
            "-frames:v", "1",
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(preview_cmd, capture_output=True, check=True)
            print(f"✅ Subtitle preview created: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"❌ Preview generation failed: {e}")
            raise
    
    def _get_system_font(self) -> str:
        """Get path to a system font file"""
        # Common font paths across different systems
        font_paths = [
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
            "arial.ttf"  # Fallback (if in PATH)
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        
        return ""  # Let FFmpeg use default
    
    def extract_audio_from_video(self, video_path: str, output_audio_path: str) -> str:
        """Extract audio from video file for alignment processing"""
        
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "16000",  # 16kHz for audio alignment
            "-ac", "1",  # Mono
            "-y",
            output_audio_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"✅ Audio extracted: {output_audio_path}")
            return output_audio_path
        except subprocess.CalledProcessError as e:
            print(f"❌ Audio extraction failed: {e}")
            raise
    
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up temporary files: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self._cleanup_temp_files()


def test_subtitle_renderer():
    """Test the subtitle renderer"""
    
    print("🧪 Testing Subtitle Renderer...")
    
    try:
        renderer = SubtitleRenderer()
        
        # Test with sample subtitles
        from subtitle_engine import SubtitleSegment, SubtitleStyle
        
        sample_subtitles = [
            SubtitleSegment(
                id=0,
                text="Hello, this is a test subtitle",
                start_ms=0,
                end_ms=2000,
                confidence=1.0
            ),
            SubtitleSegment(
                id=1,
                text="This is the second subtitle",
                start_ms=2500,
                end_ms=4500,
                confidence=1.0
            )
        ]
        
        sample_style = SubtitleStyle(
            font_size=32,
            font_weight="bold",
            text_color="#ffffff",
            background_color="#000000",
            background_opacity=0.7,
            outline_width=2
        )
        
        # Test ASS generation
        ass_file = renderer._generate_ass_subtitles(sample_subtitles, sample_style)
        print(f"✅ ASS file generated: {ass_file}")
        
        # Test preview creation
        preview_path = renderer.create_subtitle_preview(
            sample_subtitles, 
            sample_style,
            (1920, 1080)
        )
        print(f"✅ Preview created: {preview_path}")
        
        print("✅ Subtitle Renderer test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_subtitle_renderer()