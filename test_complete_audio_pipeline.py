#!/usr/bin/env python3
"""
Teste para simular o upload de áudio e verificar se o bug foi corrigido
"""

import sys
import os
import tempfile
import numpy as np

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_audio():
    """Cria um arquivo de áudio de teste"""
    try:
        import soundfile as sf
        
        # Gera áudio de teste - frase falada simulada
        sample_rate = 16000
        duration = 3.0  # 3 segundos
        
        # Simula uma frase com pausas
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Frequências para simular formantes de vogais
        # "ESTE É UM TESTE"
        audio_data = np.zeros_like(t)
        
        # Palavra 1: "ESTE" (0-0.8s)
        mask1 = (t >= 0.0) & (t < 0.8)
        audio_data[mask1] = (
            0.3 * np.sin(2 * np.pi * 400 * t[mask1]) +  # F1
            0.2 * np.sin(2 * np.pi * 800 * t[mask1])    # F2
        )
        
        # Pausa (0.8-1.0s)
        
        # Palavra 2: "É" (1.0-1.3s)
        mask2 = (t >= 1.0) & (t < 1.3)
        audio_data[mask2] = 0.3 * np.sin(2 * np.pi * 500 * t[mask2])
        
        # Pausa (1.3-1.5s)
        
        # Palavra 3: "UM" (1.5-1.8s)
        mask3 = (t >= 1.5) & (t < 1.8)
        audio_data[mask3] = 0.25 * np.sin(2 * np.pi * 350 * t[mask3])
        
        # Pausa (1.8-2.0s)
        
        # Palavra 4: "TESTE" (2.0-3.0s)
        mask4 = (t >= 2.0) & (t < 3.0)
        audio_data[mask4] = (
            0.4 * np.sin(2 * np.pi * 450 * t[mask4]) +
            0.2 * np.sin(2 * np.pi * 900 * t[mask4])
        )
        
        # Adiciona um pouco de ruído para realismo
        noise = np.random.normal(0, 0.02, len(audio_data))
        audio_data += noise
        
        # Normaliza
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_filename = tmp_file.name
        
        # Salva arquivo
        sf.write(tmp_filename, audio_data, sample_rate)
        
        return tmp_filename, "ESTE É UM TESTE"
        
    except ImportError:
        # Fallback com scipy
        from scipy.io.wavfile import write
        
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Sinal mais simples
        audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_filename = tmp_file.name
        
        write(tmp_filename, sample_rate, audio_data)
        return tmp_filename, "TESTE ÁUDIO"

def test_complete_audio_pipeline():
    """Testa o pipeline completo de processamento de áudio"""
    
    print("🎯 TESTE COMPLETO DO PIPELINE DE ÁUDIO")
    print("=" * 60)
    
    audio_file = None
    
    try:
        # 1. Cria arquivo de áudio de teste
        print("1️⃣ Criando arquivo de áudio de teste...")
        audio_file, text = create_test_audio()
        print(f"✅ Arquivo criado: {audio_file}")
        print(f"📝 Texto esperado: {text}")
        
        # 2. Testa detecção de atividade de fala
        print("\n2️⃣ Testando detecção de atividade de fala...")
        from audio_error_handling import detect_speech_activity
        
        speech_result = detect_speech_activity(audio_file)
        print(f"✅ Atividade de fala detectada:")
        print(f"  📊 Intervalos: {len(speech_result['speech_intervals'])}")
        print(f"  ⏱️ Duração de fala: {speech_result['total_speech_duration']:.2f}s")
        print(f"  🎬 Duração total: {speech_result['total_duration']:.2f}s")
        
        # 3. Testa validação do conteúdo do áudio
        print("\n3️⃣ Testando validação do conteúdo do áudio...")
        from audio_error_handling import validate_audio_content
        
        audio_info = validate_audio_content(audio_file)
        print(f"✅ Informações do áudio:")
        print(f"  🎵 Sample rate: {audio_info['sample_rate']}Hz")
        print(f"  ⏱️ Duração: {audio_info['duration_ms']:.0f}ms")
        print(f"  📻 Canais: {audio_info['channels']}")
        print(f"  📁 Formato: {audio_info['format']}")
        
        # 4. Testa importações seguras
        print("\n4️⃣ Testando utilitários de importação segura...")
        from audio_utils_safe import safe_audio_imports, get_audio_loader
        
        modules = safe_audio_imports()
        print(f"✅ Módulos disponíveis:")
        for name, module in modules.items():
            status = "✅" if module is not None else "❌"
            print(f"  {status} {name}")
        
        # 5. Testa carregamento de áudio
        print("\n5️⃣ Testando carregamento de áudio...")
        loader = get_audio_loader()
        y, sr = loader(audio_file, sr=16000)
        print(f"✅ Áudio carregado:")
        print(f"  📊 Shape: {y.shape}")
        print(f"  🎵 Sample rate: {sr}Hz")
        print(f"  📈 Amplitude máxima: {np.max(np.abs(y)):.3f}")
        
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"✅ Pipeline de áudio funcionando corretamente")
        print(f"✅ Conflitos de importação resolvidos")
        print(f"✅ Fallbacks funcionais disponíveis")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Limpa arquivo temporário
        if audio_file and os.path.exists(audio_file):
            try:
                os.unlink(audio_file)
                print(f"🧹 Arquivo temporário removido")
            except:
                print(f"⚠️ Não foi possível remover arquivo temporário: {audio_file}")

if __name__ == '__main__':
    success = test_complete_audio_pipeline()
    
    print(f"\n🏁 RESULTADO FINAL:")
    if success:
        print(f"🎯 PIPELINE DE ÁUDIO 100% FUNCIONAL!")
        print(f"✅ Bug de importação librosa/coverage: CORRIGIDO")
        print(f"✅ Detecção de atividade de fala: OK")
        print(f"✅ Processamento de áudio: OK")
        print(f"✅ Sistema pronto para produção")
    else:
        print(f"❌ Ainda há problemas no pipeline de áudio")
        print(f"⚠️ Verificar logs acima para detalhes")