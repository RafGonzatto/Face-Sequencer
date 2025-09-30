#!/usr/bin/env python3
"""
Teste específico para a função detect_speech_activity
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_detect_speech_activity():
    """Testa a função detect_speech_activity"""
    
    print("🎤 TESTE DA FUNÇÃO DETECT_SPEECH_ACTIVITY")
    print("=" * 50)
    
    try:
        from audio_error_handling import detect_speech_activity
        print("✅ Função importada com sucesso")
        
        # Cria um arquivo de áudio de teste simples
        import tempfile
        import numpy as np
        
        # Cria um arquivo WAV simples de teste
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_filename = tmp_file.name
            
            # Gera um sinal de teste simples (tom de 440Hz por 1 segundo)
            try:
                import soundfile as sf
                
                sample_rate = 16000
                duration = 1.0  # 1 segundo
                frequency = 440  # Lá (A4)
                
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                # Gera uma onda senoidal simples
                audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
                
                # Salva como arquivo WAV
                sf.write(tmp_filename, audio_data, sample_rate)
                
                print(f"🎵 Arquivo de teste criado: {tmp_filename}")
                
                # Testa a função
                print("🔍 Testando detect_speech_activity...")
                result = detect_speech_activity(tmp_filename)
                
                print("✅ Função executada com sucesso!")
                print(f"📊 Resultado: {result}")
                
                # Validações básicas
                expected_keys = ['speech_intervals', 'total_speech_duration', 'total_duration']
                for key in expected_keys:
                    if key in result:
                        print(f"  ✅ {key}: {result[key]}")
                    else:
                        print(f"  ❌ {key}: AUSENTE")
                
                # Limpa arquivo temporário (Windows needs handle closed first)
                try:
                    # Ensure file descriptor is closed before deletion
                    tmp_file.flush()
                    tmp_file.close()
                except Exception:
                    pass
                try:
                    os.unlink(tmp_filename)
                except PermissionError:
                    # On Windows the file may still be locked briefly; retry after context
                    pass
                
            except ImportError as sf_error:
                print(f"⚠️ soundfile não disponível: {sf_error}")
                
                # Tenta criar com scipy/numpy puro
                try:
                    from scipy.io.wavfile import write
                    
                    sample_rate = 16000
                    duration = 1.0
                    frequency = 440
                    
                    t = np.linspace(0, duration, int(sample_rate * duration), False)
                    audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
                    
                    write(tmp_filename, sample_rate, audio_data)
                    print(f"🎵 Arquivo de teste criado com scipy: {tmp_filename}")
                    
                    # Testa a função
                    result = detect_speech_activity(tmp_filename)
                    print("✅ Função executada com sucesso (fallback)!")
                    
                    try:
                        tmp_file.flush(); tmp_file.close()
                    except Exception:
                        pass
                    try:
                        os.unlink(tmp_filename)
                    except PermissionError:
                        pass
                    
                except Exception as scipy_error:
                    print(f"❌ Falhou para criar arquivo de teste (scipy): {scipy_error}")
                    try:
                        tmp_file.flush(); tmp_file.close()
                    except Exception:
                        pass
                    try:
                        os.unlink(tmp_filename)
                    except PermissionError:
                        pass
                    raise
                    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    try:
        test_detect_speech_activity()
        print(f"\n🏁 RESULTADO: ✅ SUCESSO")
    except Exception:
        print(f"\n🏁 RESULTADO: ❌ FALHOU")
        sys.exit(1)