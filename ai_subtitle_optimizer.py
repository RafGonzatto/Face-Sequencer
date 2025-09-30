"""
AI-Powered Subtitle Optimizer - Phase 3 Implementation
Advanced AI-driven subtitle optimization with machine learning capabilities.
"""

import json
import re
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib

# ML/NLP imports for AI optimization
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from textstat import flesch_reading_ease, flesch_kincaid_grade
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from enhanced_subtitle_engine import EnhancedSubtitleEngine, SubtitleSegment

logger = logging.getLogger(__name__)

@dataclass
class AIOptimizationResult:
    """Result from AI optimization process."""
    optimized_segments: List[SubtitleSegment]
    optimization_score: float
    readability_improvement: float
    timing_adjustments: int
    text_modifications: int
    ai_confidence: float
    optimization_time: float
    suggestions: List[str] = field(default_factory=list)

class AISubtitleOptimizer:
    """
    Advanced AI-powered subtitle optimizer with machine learning capabilities.
    Provides intelligent text processing, readability optimization, and contextual improvements.
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.optimization_cache = {}
        self.initialize_nlp_models()
        
    def initialize_nlp_models(self):
        """Initialize NLP models and resources."""
        if NLTK_AVAILABLE:
            try:
                # Download required NLTK data
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                nltk.download('vader_lexicon', quiet=True)
                self.stopwords = set(stopwords.words('english'))
            except Exception as e:
                logger.warning(f"Failed to initialize NLTK: {e}")
                self.stopwords = set()
        else:
            logger.warning("NLTK not available. AI features will be limited.")
            self.stopwords = set()
    
    async def optimize_subtitles_ai(self, 
                                   segments: List[SubtitleSegment],
                                   optimization_level: str = "balanced",
                                   target_platform: str = "general",
                                   user_preferences: Dict[str, Any] = None) -> AIOptimizationResult:
        """
        Apply AI-powered optimization to subtitle segments.
        
        Args:
            segments: List of subtitle segments to optimize
            optimization_level: "conservative", "balanced", "aggressive"
            target_platform: Platform-specific optimization target
            user_preferences: User-defined optimization preferences
            
        Returns:
            AIOptimizationResult with optimized segments and metrics
        """
        start_time = datetime.now()
        
        if user_preferences is None:
            user_preferences = {}
            
        # Generate cache key for this optimization request
        cache_key = self._generate_cache_key(segments, optimization_level, target_platform, user_preferences)
        
        if cache_key in self.optimization_cache:
            logger.info("Returning cached AI optimization result")
            return self.optimization_cache[cache_key]
        
        try:
            # Run optimization asynchronously
            optimization_tasks = []
            
            # 1. Readability optimization
            optimization_tasks.append(
                asyncio.create_task(self._optimize_readability(segments, optimization_level))
            )
            
            # 2. Timing optimization
            optimization_tasks.append(
                asyncio.create_task(self._optimize_timing_ai(segments, target_platform))
            )
            
            # 3. Text coherence optimization
            optimization_tasks.append(
                asyncio.create_task(self._optimize_text_coherence(segments))
            )
            
            # 4. Platform-specific optimization
            optimization_tasks.append(
                asyncio.create_task(self._optimize_for_platform_ai(segments, target_platform))
            )
            
            # Wait for all optimizations to complete
            readability_result, timing_result, coherence_result, platform_result = await asyncio.gather(*optimization_tasks)
            
            # Combine optimization results
            optimized_segments = self._merge_optimization_results(
                segments, readability_result, timing_result, coherence_result, platform_result
            )
            
            # Calculate optimization metrics
            optimization_score = self._calculate_optimization_score(segments, optimized_segments)
            readability_improvement = self._calculate_readability_improvement(segments, optimized_segments)
            
            # Count modifications
            timing_adjustments = sum(1 for i, seg in enumerate(optimized_segments) 
                                   if abs(seg.start_time - segments[i].start_time) > 0.1 or 
                                      abs(seg.end_time - segments[i].end_time) > 0.1)
            
            text_modifications = sum(1 for i, seg in enumerate(optimized_segments) 
                                   if seg.text != segments[i].text)
            
            ai_confidence = min(readability_result.get('confidence', 0.8),
                               timing_result.get('confidence', 0.8),
                               coherence_result.get('confidence', 0.8),
                               platform_result.get('confidence', 0.8))
            
            # Generate suggestions
            suggestions = self._generate_optimization_suggestions(
                segments, optimized_segments, optimization_level, target_platform
            )
            
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = AIOptimizationResult(
                optimized_segments=optimized_segments,
                optimization_score=optimization_score,
                readability_improvement=readability_improvement,
                timing_adjustments=timing_adjustments,
                text_modifications=text_modifications,
                ai_confidence=ai_confidence,
                optimization_time=optimization_time,
                suggestions=suggestions
            )
            
            # Cache result
            self.optimization_cache[cache_key] = result
            
            logger.info(f"AI optimization completed in {optimization_time:.2f}s with {ai_confidence:.1%} confidence")
            return result
            
        except Exception as e:
            logger.error(f"AI optimization failed: {e}")
            # Return original segments with error information
            return AIOptimizationResult(
                optimized_segments=segments,
                optimization_score=0.0,
                readability_improvement=0.0,
                timing_adjustments=0,
                text_modifications=0,
                ai_confidence=0.0,
                optimization_time=(datetime.now() - start_time).total_seconds(),
                suggestions=[f"Optimization failed: {str(e)}"]
            )
    
    async def _optimize_readability(self, segments: List[SubtitleSegment], level: str) -> Dict[str, Any]:
        """Optimize subtitle readability using NLP analysis."""
        
        def analyze_readability(segment_batch):
            results = []
            for segment in segment_batch:
                if not NLTK_AVAILABLE:
                    # Fallback readability analysis
                    word_count = len(segment.text.split())
                    sentence_count = segment.text.count('.') + segment.text.count('!') + segment.text.count('?') + 1
                    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else word_count
                    
                    # Simple readability score (lower is better)
                    readability_score = max(0, 100 - (avg_sentence_length * 3))
                else:
                    try:
                        readability_score = flesch_reading_ease(segment.text)
                        grade_level = flesch_kincaid_grade(segment.text)
                    except:
                        readability_score = 60  # Default moderate readability
                        grade_level = 8
                
                # Apply readability improvements based on level
                improved_text = segment.text
                
                if level == "aggressive":
                    # More aggressive text simplification
                    improved_text = self._simplify_text_aggressive(segment.text)
                elif level == "balanced":
                    # Moderate text improvements
                    improved_text = self._simplify_text_balanced(segment.text)
                # Conservative level keeps original text mostly intact
                
                results.append({
                    'original_segment': segment,
                    'improved_text': improved_text,
                    'readability_score': readability_score,
                    'improvement_made': improved_text != segment.text
                })
            
            return results
        
        # Process segments in batches for better performance
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(self.executor, analyze_readability, segments)
        
        return {
            'results': results,
            'confidence': 0.85,
            'total_improvements': sum(1 for r in results if r['improvement_made'])
        }
    
    async def _optimize_timing_ai(self, segments: List[SubtitleSegment], platform: str) -> Dict[str, Any]:
        """AI-powered timing optimization based on reading patterns."""
        
        def optimize_timing_batch(segment_batch):
            results = []
            
            # Platform-specific timing preferences
            timing_preferences = {
                'instagram': {'min_duration': 0.8, 'max_duration': 4.0, 'reading_speed': 2.2},
                'tiktok': {'min_duration': 0.6, 'max_duration': 3.0, 'reading_speed': 2.8},
                'youtube': {'min_duration': 1.0, 'max_duration': 6.0, 'reading_speed': 2.5},
                'general': {'min_duration': 1.0, 'max_duration': 5.0, 'reading_speed': 2.3}
            }
            
            prefs = timing_preferences.get(platform, timing_preferences['general'])
            
            for i, segment in enumerate(segment_batch):
                # Calculate optimal timing based on text complexity and reading speed
                word_count = len(segment.text.split())
                char_count = len(segment.text)
                
                # AI-based duration calculation
                base_reading_time = word_count / prefs['reading_speed']
                
                # Adjust for text complexity
                complexity_factor = min(char_count / (word_count * 6), 2.0)  # Average 6 chars per word
                adjusted_reading_time = base_reading_time * complexity_factor
                
                # Apply platform constraints
                optimal_duration = max(prefs['min_duration'], 
                                     min(prefs['max_duration'], adjusted_reading_time))
                
                # Calculate new timing while preserving relative positioning
                current_duration = segment.end_time - segment.start_time
                timing_adjustment = optimal_duration - current_duration
                
                # Adjust timing while avoiding overlaps
                new_start = segment.start_time
                new_end = segment.start_time + optimal_duration
                
                # Check for overlap with next segment
                if i < len(segment_batch) - 1:
                    next_segment = segment_batch[i + 1]
                    if new_end > next_segment.start_time:
                        # Adjust to prevent overlap
                        new_end = next_segment.start_time - 0.1
                        optimal_duration = new_end - new_start
                
                results.append({
                    'original_segment': segment,
                    'new_start_time': new_start,
                    'new_end_time': new_end,
                    'duration_change': optimal_duration - current_duration,
                    'timing_improved': abs(timing_adjustment) > 0.2
                })
            
            return results
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(self.executor, optimize_timing_batch, segments)
        
        return {
            'results': results,
            'confidence': 0.90,
            'total_adjustments': sum(1 for r in results if r['timing_improved'])
        }
    
    async def _optimize_text_coherence(self, segments: List[SubtitleSegment]) -> Dict[str, Any]:
        """Optimize text coherence and flow across segments."""
        
        def analyze_coherence(segment_batch):
            results = []
            
            for i, segment in enumerate(segment_batch):
                improved_text = segment.text
                coherence_score = 0.8  # Default coherence
                
                # Check for sentence fragments and improve connectivity
                if i > 0:
                    prev_segment = segment_batch[i - 1]
                    # Check if current segment continues a sentence
                    if (not prev_segment.text.rstrip().endswith(('.', '!', '?')) and 
                        not segment.text.lstrip()[0].isupper()):
                        # This might be a continuation
                        coherence_score += 0.1
                
                # Improve text based on context
                if NLTK_AVAILABLE:
                    try:
                        sentences = sent_tokenize(segment.text)
                        if len(sentences) > 1:
                            # Multiple sentences in one segment - might need breaking
                            coherence_score -= 0.1
                    except:
                        pass
                
                # Apply text improvements for better flow
                improved_text = self._improve_text_flow(segment.text, i, segment_batch)
                
                results.append({
                    'original_segment': segment,
                    'improved_text': improved_text,
                    'coherence_score': coherence_score,
                    'coherence_improved': improved_text != segment.text
                })
            
            return results
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(self.executor, analyze_coherence, segments)
        
        return {
            'results': results,
            'confidence': 0.75,
            'total_improvements': sum(1 for r in results if r['coherence_improved'])
        }
    
    async def _optimize_for_platform_ai(self, segments: List[SubtitleSegment], platform: str) -> Dict[str, Any]:
        """AI-driven platform-specific optimization."""
        
        def platform_optimize(segment_batch):
            results = []
            
            # Platform-specific AI rules
            platform_rules = {
                'instagram': {
                    'max_chars_per_line': 35,
                    'max_lines': 2,
                    'prefer_short_words': True,
                    'emoji_friendly': True
                },
                'tiktok': {
                    'max_chars_per_line': 30,
                    'max_lines': 2,
                    'prefer_short_words': True,
                    'emoji_friendly': True,
                    'casual_tone': True
                },
                'youtube': {
                    'max_chars_per_line': 50,
                    'max_lines': 3,
                    'prefer_short_words': False,
                    'emoji_friendly': False
                },
                'general': {
                    'max_chars_per_line': 40,
                    'max_lines': 2,
                    'prefer_short_words': False,
                    'emoji_friendly': False
                }
            }
            
            rules = platform_rules.get(platform, platform_rules['general'])
            
            for segment in segment_batch:
                optimized_text = self._apply_platform_rules(segment.text, rules)
                
                results.append({
                    'original_segment': segment,
                    'platform_optimized_text': optimized_text,
                    'platform_score': self._calculate_platform_score(optimized_text, rules),
                    'platform_improved': optimized_text != segment.text
                })
            
            return results
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(self.executor, platform_optimize, segments)
        
        return {
            'results': results,
            'confidence': 0.88,
            'total_optimizations': sum(1 for r in results if r['platform_improved'])
        }
    
    def _simplify_text_aggressive(self, text: str) -> str:
        """Apply aggressive text simplification."""
        # Replace complex words with simpler alternatives
        simplifications = {
            'approximately': 'about',
            'consequently': 'so',
            'nevertheless': 'but',
            'furthermore': 'also',
            'therefore': 'so',
            'however': 'but',
            'additionally': 'also',
            'subsequently': 'then'
        }
        
        simplified = text
        for complex_word, simple_word in simplifications.items():
            simplified = re.sub(rf'\b{complex_word}\b', simple_word, simplified, flags=re.IGNORECASE)
        
        # Remove unnecessary words
        simplified = re.sub(r'\b(very|really|quite|rather|somewhat)\s+', '', simplified, flags=re.IGNORECASE)
        
        return simplified.strip()
    
    def _simplify_text_balanced(self, text: str) -> str:
        """Apply balanced text improvements."""
        # More conservative simplifications
        improved = text
        
        # Fix common readability issues
        improved = re.sub(r'\s+', ' ', improved)  # Multiple spaces
        improved = re.sub(r'([.!?])\s*([a-z])', r'\1 \2', improved)  # Space after punctuation
        
        # Capitalize properly
        improved = '. '.join(sentence.strip().capitalize() for sentence in improved.split('.') if sentence.strip())
        
        return improved
    
    def _improve_text_flow(self, text: str, position: int, all_segments: List[SubtitleSegment]) -> str:
        """Improve text flow and connectivity."""
        improved = text
        
        # Add transitional words where appropriate
        if position > 0:
            prev_text = all_segments[position - 1].text
            if not prev_text.rstrip().endswith(('.', '!', '?')) and text[0].islower():
                # This is likely a continuation
                if not text.startswith(('and', 'but', 'so', 'then', 'now')):
                    # Add a connector if appropriate
                    if 'but' not in text.lower() and 'however' not in text.lower():
                        improved = 'and ' + text
        
        return improved
    
    def _apply_platform_rules(self, text: str, rules: Dict[str, Any]) -> str:
        """Apply platform-specific optimization rules."""
        optimized = text
        
        # Handle line length limits
        max_chars = rules['max_chars_per_line']
        max_lines = rules['max_lines']
        
        words = optimized.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_line else 0)  # +1 for space
            
            if current_length + word_length <= max_chars:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Limit number of lines
        if len(lines) > max_lines:
            # Try to condense or truncate
            lines = lines[:max_lines]
            if len(lines) == max_lines:
                # Add ellipsis if truncated
                last_line = lines[-1]
                if len(last_line) > max_chars - 3:
                    lines[-1] = last_line[:max_chars-3] + '...'
        
        optimized = '\n'.join(lines)
        
        # Apply casual tone for TikTok
        if rules.get('casual_tone'):
            optimized = optimized.replace('you are', "you're")
            optimized = optimized.replace('it is', "it's")
            optimized = optimized.replace('we are', "we're")
        
        return optimized
    
    def _calculate_platform_score(self, text: str, rules: Dict[str, Any]) -> float:
        """Calculate how well text fits platform requirements."""
        score = 1.0
        
        lines = text.split('\n')
        
        # Check line count
        if len(lines) > rules['max_lines']:
            score -= 0.3
        
        # Check line lengths
        for line in lines:
            if len(line) > rules['max_chars_per_line']:
                score -= 0.2
        
        # Bonus for following best practices
        if all(len(line) <= rules['max_chars_per_line'] for line in lines):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _merge_optimization_results(self, 
                                  original_segments: List[SubtitleSegment],
                                  readability_result: Dict[str, Any],
                                  timing_result: Dict[str, Any],
                                  coherence_result: Dict[str, Any],
                                  platform_result: Dict[str, Any]) -> List[SubtitleSegment]:
        """Merge all optimization results into final segments."""
        
        optimized_segments = []
        
        for i, original_seg in enumerate(original_segments):
            # Start with original segment
            new_segment = SubtitleSegment(
                id=original_seg.id,
                text=original_seg.text,
                start_time=original_seg.start_time,
                end_time=original_seg.end_time,
                confidence=original_seg.confidence,
                word_count=original_seg.word_count,
                reading_speed=original_seg.reading_speed,
                platform_optimized=original_seg.platform_optimized.copy(),
                style_overrides=original_seg.style_overrides.copy()
            )
            
            # Apply readability improvements
            if i < len(readability_result['results']):
                readability = readability_result['results'][i]
                if readability['improvement_made']:
                    new_segment.text = readability['improved_text']
            
            # Apply timing optimizations
            if i < len(timing_result['results']):
                timing = timing_result['results'][i]
                if timing['timing_improved']:
                    new_segment.start_time = timing['new_start_time']
                    new_segment.end_time = timing['new_end_time']
            
            # Apply coherence improvements
            if i < len(coherence_result['results']):
                coherence = coherence_result['results'][i]
                if coherence['coherence_improved']:
                    new_segment.text = coherence['improved_text']
            
            # Apply platform optimizations
            if i < len(platform_result['results']):
                platform = platform_result['results'][i]
                if platform['platform_improved']:
                    new_segment.text = platform['platform_optimized_text']
                    new_segment.platform_optimized['score'] = platform['platform_score']
            
            # Recalculate derived properties
            new_segment.word_count = len(new_segment.text.split())
            duration = new_segment.end_time - new_segment.start_time
            new_segment.reading_speed = new_segment.word_count / duration if duration > 0 else 0
            
            optimized_segments.append(new_segment)
        
        return optimized_segments
    
    def _calculate_optimization_score(self, original: List[SubtitleSegment], optimized: List[SubtitleSegment]) -> float:
        """Calculate overall optimization improvement score."""
        if not original or not optimized:
            return 0.0
        
        improvements = 0
        total_checks = 0
        
        for orig, opt in zip(original, optimized):
            total_checks += 4  # 4 optimization categories
            
            # Text improvement (readability)
            if len(opt.text.split()) <= len(orig.text.split()) and opt.text != orig.text:
                improvements += 1
            
            # Timing improvement
            orig_duration = orig.end_time - orig.start_time
            opt_duration = opt.end_time - opt.start_time
            if abs(opt.reading_speed - 2.5) < abs(orig.reading_speed - 2.5):
                improvements += 1
            
            # Platform optimization
            if opt.platform_optimized.get('score', 0) > orig.platform_optimized.get('score', 0):
                improvements += 1
            
            # Overall quality
            if opt.confidence >= orig.confidence:
                improvements += 1
        
        return improvements / total_checks if total_checks > 0 else 0.0
    
    def _calculate_readability_improvement(self, original: List[SubtitleSegment], optimized: List[SubtitleSegment]) -> float:
        """Calculate readability improvement percentage."""
        if not NLTK_AVAILABLE:
            # Simple fallback calculation
            orig_avg_words = sum(len(seg.text.split()) for seg in original) / len(original)
            opt_avg_words = sum(len(seg.text.split()) for seg in optimized) / len(optimized)
            return max(0, (orig_avg_words - opt_avg_words) / orig_avg_words * 100)
        
        try:
            orig_scores = [flesch_reading_ease(seg.text) for seg in original if seg.text.strip()]
            opt_scores = [flesch_reading_ease(seg.text) for seg in optimized if seg.text.strip()]
            
            if orig_scores and opt_scores:
                orig_avg = sum(orig_scores) / len(orig_scores)
                opt_avg = sum(opt_scores) / len(opt_scores)
                return max(0, (opt_avg - orig_avg) / 100 * 100)  # Normalize to percentage
        except:
            pass
        
        return 0.0
    
    def _generate_optimization_suggestions(self, 
                                         original: List[SubtitleSegment],
                                         optimized: List[SubtitleSegment],
                                         level: str,
                                         platform: str) -> List[str]:
        """Generate human-readable optimization suggestions."""
        suggestions = []
        
        # Count improvements
        text_changes = sum(1 for orig, opt in zip(original, optimized) if orig.text != opt.text)
        timing_changes = sum(1 for orig, opt in zip(original, optimized) 
                           if abs(orig.start_time - opt.start_time) > 0.1 or abs(orig.end_time - opt.end_time) > 0.1)
        
        if text_changes > 0:
            suggestions.append(f"Improved readability in {text_changes} segments")
        
        if timing_changes > 0:
            suggestions.append(f"Optimized timing for {timing_changes} segments")
        
        # Platform-specific suggestions
        if platform == 'instagram':
            suggestions.append("Optimized for Instagram Stories/Reels viewing patterns")
        elif platform == 'tiktok':
            suggestions.append("Applied TikTok best practices for mobile viewing")
        elif platform == 'youtube':
            suggestions.append("Optimized for YouTube Shorts engagement")
        
        # Level-specific feedback
        if level == 'aggressive':
            suggestions.append("Applied advanced text simplification for maximum readability")
        elif level == 'balanced':
            suggestions.append("Balanced optimization preserving original meaning")
        else:
            suggestions.append("Conservative optimization maintaining text integrity")
        
        if not suggestions:
            suggestions.append("Content already well-optimized for target platform")
        
        return suggestions
    
    def _generate_cache_key(self, segments: List[SubtitleSegment], level: str, platform: str, preferences: Dict[str, Any]) -> str:
        """Generate unique cache key for optimization request."""
        # Create hash from segments content and parameters
        content_hash = hashlib.md5()
        
        for seg in segments:
            content_hash.update(f"{seg.text}:{seg.start_time}:{seg.end_time}".encode())
        
        content_hash.update(f"{level}:{platform}:{json.dumps(preferences, sort_keys=True)}".encode())
        
        return content_hash.hexdigest()
    
    def clear_optimization_cache(self):
        """Clear the optimization cache."""
        self.optimization_cache.clear()
        logger.info("AI optimization cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_optimizations': len(self.optimization_cache),
            'cache_size_mb': sum(len(str(result)) for result in self.optimization_cache.values()) / 1024 / 1024
        }