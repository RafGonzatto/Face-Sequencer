#!/usr/bin/env python3
"""
Debug script para investigar o problema de timing drift onde:
- Primeiros 20s: perfeito 
- 20-40s: acelerado (não bate com o audio)  
- 40-60s: muito lento (pouquíssimos frames)

Este script simula e analisa o problema para identificar a causa raiz.
"""

import math
from typing import List, Dict, Any

def simulate_frame_states_with_timing_issues(audio_duration_seconds: float = 60.0, fps: float = 30.0) -> List[Dict[str, Any]]:
    """
    Simula frame_states que reproduzem o problema reportado
    """
    frame_states = []
    current_time = 0.0
    frame_number = 0
    
    # Palavras simuladas distribuídas ao longo do áudio
    words = [
        "ESTE", "É", "UM", "TESTE", "DE", "ALINHAMENTO", "PERFEITO",  # 0-10s
        "PARA", "DEMONSTRAR", "O", "FUNCIONAMENTO", "CORRETO",       # 10-20s
        "DO", "SISTEMA", "DE", "SINCRONIZAÇÃO", "DE", "AUDIO",       # 20-30s - PROBLEMA AQUI
        "COM", "TEXTO", "E", "ANIMAÇÃO", "FACIAL", "PRECISA",        # 30-40s - PROBLEMA CONTINUA
        "USANDO", "TECNOLOGIA", "AVANÇADA", "DE", "ALINHAMENTO"      # 40-60s - MUITO LENTO
    ]
    
    # Simula timing baseado no problema reportado
    word_index = 0
    
    while current_time < audio_duration_seconds and word_index < len(words):
        word = words[word_index]
        
        # Determina durações baseado na faixa temporal (simula o problema)
        if current_time < 20.0:
            # Primeiros 20s: timing perfeito
            word_duration = 0.8  # 800ms por palavra
            pause_duration = 0.2  # 200ms de pausa
            frames_per_letter = 3  # 3 frames por letra (normal)
            
        elif current_time < 40.0:
            # 20-40s: acelerado - muito rápido
            word_duration = 0.4  # 400ms por palavra (METADE do tempo!)
            pause_duration = 0.1  # 100ms de pausa (muito rápido)
            frames_per_letter = 1  # apenas 1 frame por letra (acelerado)
            
        else:
            # 40-60s: muito lento - pouquíssimos frames
            word_duration = 2.0   # 2 segundos por palavra (muito lento)
            pause_duration = 0.5  # 500ms de pausa
            frames_per_letter = 8  # 8 frames por letra (muito lento)
        
        # Adiciona frames para a palavra
        letter_count = len(word)
        frame_duration_ms = (word_duration * 1000) / (letter_count * frames_per_letter)
        
        for letter in word:
            for _ in range(frames_per_letter):
                frame_states.append({
                    'frame_number': frame_number,
                    'timestamp': current_time,
                    'active_word': word,
                    'active_letter': letter,
                    'ms': frame_duration_ms,
                    'is_pause': False,
                    'time_segment': f"{current_time:.1f}s"
                })
                current_time += frame_duration_ms / 1000
                frame_number += 1
        
        # Pausa entre palavras  
        pause_frames = max(1, int(pause_duration * fps))
        for _ in range(pause_frames):
            frame_states.append({
                'frame_number': frame_number,
                'timestamp': current_time,
                'active_word': '',
                'ms': 33.33,  # Frame normal
                'is_pause': True,
                'time_segment': f"{current_time:.1f}s"
            })
            current_time += 33.33 / 1000
            frame_number += 1
            
        word_index += 1
    
    return frame_states

def analyze_timing_drift(frame_states: List[Dict[str, Any]], audio_duration: float = 60.0) -> Dict[str, Any]:
    """
    Analisa o timing drift nos frame_states
    """
    if not frame_states:
        return {"error": "No frame states to analyze"}
    
    # Divide em segmentos de 20 segundos
    segments = {
        "0-20s": {"frames": [], "word_frames": [], "pause_frames": []},
        "20-40s": {"frames": [], "word_frames": [], "pause_frames": []},
        "40-60s": {"frames": [], "word_frames": [], "pause_frames": []}
    }
    
    for frame in frame_states:
        timestamp = frame.get('timestamp', 0)
        
        if timestamp < 20.0:
            segment = "0-20s"
        elif timestamp < 40.0:
            segment = "20-40s"
        else:
            segment = "40-60s"
            
        segments[segment]["frames"].append(frame)
        
        if frame.get('is_pause'):
            segments[segment]["pause_frames"].append(frame)
        else:
            segments[segment]["word_frames"].append(frame)
    
    # Analisa cada segmento
    analysis = {
        "total_frames": len(frame_states),
        "total_duration": frame_states[-1]['timestamp'] if frame_states else 0,
        "segments": {}
    }
    
    for segment_name, segment_data in segments.items():
        if not segment_data["frames"]:
            continue
            
        frames = segment_data["frames"]
        first_timestamp = frames[0]['timestamp']
        last_timestamp = frames[-1]['timestamp']
        segment_duration = last_timestamp - first_timestamp
        
        # Calcula estatísticas
        avg_frame_duration = sum(f.get('ms', 33.33) for f in frames) / len(frames)
        fps_calculated = 1000 / avg_frame_duration if avg_frame_duration > 0 else 0
        
        # Conta palavras únicas no segmento
        unique_words = set()
        for f in segment_data["word_frames"]:
            word = f.get('active_word', '')
            if word:
                unique_words.add(word)
        
        analysis["segments"][segment_name] = {
            "total_frames": len(frames),
            "word_frames": len(segment_data["word_frames"]),
            "pause_frames": len(segment_data["pause_frames"]),
            "duration": segment_duration,
            "avg_frame_duration_ms": avg_frame_duration,
            "calculated_fps": fps_calculated,
            "unique_words": len(unique_words),
            "words": list(unique_words),
            "frames_per_second_actual": len(frames) / segment_duration if segment_duration > 0 else 0
        }
    
    return analysis

def identify_timing_problems(analysis: Dict[str, Any]) -> List[str]:
    """
    Identifica problemas específicos no timing baseado na análise
    """
    problems = []
    
    segments = analysis.get("segments", {})
    
    # Verifica cada segmento
    for segment_name, data in segments.items():
        fps_actual = data.get("frames_per_second_actual", 0)
        avg_duration = data.get("avg_frame_duration_ms", 0)
        
        # FPS esperado é 30
        expected_fps = 30.0
        fps_deviation = abs(fps_actual - expected_fps) / expected_fps * 100
        
        if fps_deviation > 20:  # Mais de 20% de desvio
            if fps_actual > expected_fps * 1.2:
                problems.append(f"❌ {segment_name}: FPS muito alto ({fps_actual:.1f} vs esperado {expected_fps}) - ACELERADO")
            elif fps_actual < expected_fps * 0.8:
                problems.append(f"❌ {segment_name}: FPS muito baixo ({fps_actual:.1f} vs esperado {expected_fps}) - MUITO LENTO")
        
        # Verifica frame duration inconsistente
        if avg_duration < 20:  # Frames muito rápidos
            problems.append(f"❌ {segment_name}: Frames muito rápidos (média {avg_duration:.1f}ms)")
        elif avg_duration > 50:  # Frames muito lentos
            problems.append(f"❌ {segment_name}: Frames muito lentos (média {avg_duration:.1f}ms)")
    
    return problems

def find_root_cause_in_cumulative_timing() -> List[str]:
    """
    Analisa o código atual para identificar possíveis causas do problema
    """
    potential_causes = []
    
    # 1. Problema no cálculo cumulativo de tempo
    potential_causes.append("""
🔍 CAUSA POTENCIAL #1: Erro de acumulação temporal
No código atual (app.py linha ~1747-1754):

```python
cumulative_time = 0.0
frame_timestamps = []

for i, state in enumerate(frame_states):
    frame_timestamps.append(cumulative_time)
    ms = state.get('ms', 33.33)
    cumulative_time += ms / 1000.0
```

PROBLEMA: Se os valores 'ms' nos frame_states estão inconsistentes ou incorretos,
o cumulative_time vai acumular erro ao longo do tempo, causando drift.
""")
    
    # 2. Problema na geração de frame_states
    potential_causes.append("""
🔍 CAUSA POTENCIAL #2: Inconsistência na geração de frame_states
No frame_synchronizer.py (linha ~323-335):

```python  
frame_time = 1.0 / self.fps
for frame_num in range(0, total_frames, frame_step):
    current_time = frame_num * frame_time
```

PROBLEMA: Se o 'fps' muda durante a execução ou há inconsistências
entre o FPS usado para gerar frame_states vs o FPS usado para processar,
isso pode causar timing drift.
""")
    
    # 3. Problema na distribuição de frames por palavra
    potential_causes.append("""
🔍 CAUSA POTENCIAL #3: Lógica de distribuição de frames inadequada
No código atual (app.py linha ~1901-1975):

A lógica complexa para calcular token_idx pode estar causando
distribuição desigual de frames, especialmente em palavras longas
ou quando frames_in_word != len(tokens).

PROBLEMA: Se a distribuição não é linear, frames podem ser 
"gastos" rapidamente no início e faltar no final.
""")
    
    # 4. Problema na fonte dos dados ms
    potential_causes.append("""
🔍 CAUSA POTENCIAL #4: Valores 'ms' inconsistentes nos frame_states
Se os frame_states vêm de diferentes fontes (enhanced alignment, 
fallback, cache), os valores 'ms' podem ser inconsistentes:

- Enhanced alignment: usa timing preciso baseado no áudio
- Fallback: usa 33.33ms padrão 
- Cache: pode ter valores antigos/inconsistentes

PROBLEMA: Mistura de diferentes estratégias de timing.
""")
    
    return potential_causes

def suggest_robust_solution() -> str:
    """
    Propõe uma solução robusta que não perde features
    """
    return """
🎯 SOLUÇÃO ROBUSTA PROPOSTA:

1. **TIMING MASTER SOURCE**: Usar sempre o áudio como fonte autoritativa
   - Calcular timestamps baseados puramente no tempo de áudio
   - Ignorar valores 'ms' individuais dos frames para timing global
   - Usar 'ms' apenas para duração individual do frame

2. **VALIDAÇÃO E CORREÇÃO TEMPORAL**:
   ```python
   def validate_and_correct_frame_timing(frame_states, audio_duration_ms, fps=30.0):
       # Recalcula todos os timestamps baseado no áudio
       frame_time_ms = 1000.0 / fps
       corrected_frames = []
       
       for i, frame in enumerate(frame_states):
           correct_timestamp = i * frame_time_ms
           corrected_frame = frame.copy()
           corrected_frame['timestamp_corrected'] = correct_timestamp
           corrected_frame['ms'] = frame_time_ms  # Padroniza duração
           corrected_frames.append(corrected_frame)
           
       return corrected_frames
   ```

3. **WORD BOUNDARY VALIDATION**: 
   - Validar que word boundaries são consistentes com timing do áudio
   - Corrigir automaticamente discrepâncias
   - Logging detalhado para debug

4. **PROGRESSIVE TIMING CORRECTION**:
   - Detectar drift em tempo real
   - Aplicar correção gradual para evitar "jumps" abruptos
   - Manter sincronia com áudio como prioridade #1

5. **FALLBACK SEGURO**:
   - Se timing está muito inconsistente, usar distribuição linear
   - Preservar todas as features de tokenização avançada
   - Aplicar timing correto sobre a tokenização existente
"""

def main():
    """
    Executa análise completa do problema de timing drift
    """
    print("🔬 ANÁLISE DO PROBLEMA DE TIMING DRIFT")
    print("=" * 60)
    
    # Simula o problema
    print("\n1. Simulando frame_states com timing drift...")
    problematic_frames = simulate_frame_states_with_timing_issues(60.0, 30.0)
    
    # Analisa o problema
    print(f"✅ Gerados {len(problematic_frames)} frame_states simulados")
    
    print("\n2. Analisando timing por segmento...")
    analysis = analyze_timing_drift(problematic_frames, 60.0)
    
    print(f"\n📊 ANÁLISE DETALHADA:")
    print(f"Total frames: {analysis['total_frames']}")
    print(f"Duração total: {analysis['total_duration']:.2f}s")
    
    for segment, data in analysis['segments'].items():
        print(f"\n🎯 {segment}:")
        print(f"   Frames totais: {data['total_frames']}")
        print(f"   Frames de palavra: {data['word_frames']}")  
        print(f"   Frames de pausa: {data['pause_frames']}")
        print(f"   Duração: {data['duration']:.2f}s")
        print(f"   FPS real: {data['frames_per_second_actual']:.1f}")
        print(f"   Frame duration média: {data['avg_frame_duration_ms']:.1f}ms")
        print(f"   Palavras: {data['words']}")
    
    # Identifica problemas
    print("\n3. Identificando problemas específicos...")
    problems = identify_timing_problems(analysis)
    
    if problems:
        print(f"\n❌ PROBLEMAS IDENTIFICADOS:")
        for problem in problems:
            print(f"   {problem}")
    else:
        print(f"\n✅ Nenhum problema de timing detectado")
    
    # Analisa possíveis causas
    print("\n4. Analisando possíveis causas no código...")
    potential_causes = find_root_cause_in_cumulative_timing()
    
    for i, cause in enumerate(potential_causes, 1):
        print(cause)
    
    # Propõe solução
    print("\n5. Proposta de solução robusta...")
    solution = suggest_robust_solution()
    print(solution)
    
    print("\n" + "=" * 60)
    print("✅ ANÁLISE COMPLETA CONCLUÍDA")

if __name__ == "__main__":
    main()