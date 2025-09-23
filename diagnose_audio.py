"""
Diagnóstico do sistema de processamento de áudio
Verifica a instalação do Python, dependências e sistema de alinhamento de áudio
"""
import os
import sys
import platform
import importlib.util

def check_python():
    """Verifica a instalação do Python"""
    print(f"Python versão: {platform.python_version()}")
    print(f"Executável: {sys.executable}")
    print(f"Plataforma: {platform.platform()}")
    print("-" * 50)

def check_dependency(package_name):
    """Verifica se um pacote está instalado e sua versão"""
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        print(f"❌ {package_name}: Não instalado")
        return False
    
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", "Desconhecida")
        print(f"✅ {package_name}: Instalado (versão {version})")
        return True
    except Exception as e:
        print(f"⚠️ {package_name}: Erro ao verificar versão - {str(e)}")
        return False

def check_audio_system():
    """Verifica o sistema de processamento de áudio"""
    print("Verificando dependências para processamento de áudio:")
    
    # Dependências principais
    core_deps = ["numpy", "torch", "librosa", "json", "scipy"]
    for dep in core_deps:
        check_dependency(dep)
    
    # Dependências específicas para WhisperX
    print("\nVerificando dependências para WhisperX:")
    whisperx_deps = ["whisperx"]
    for dep in whisperx_deps:
        check_dependency(dep)
    
    # Verifica arquivos de áudio
    print("\nVerificando diretório de áudio:")
    audio_dir = os.path.join("uploads", "audio")
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
        print(f"✅ Diretório {audio_dir} criado")
    else:
        print(f"✅ Diretório {audio_dir} existe")
        files = os.listdir(audio_dir)
        print(f"   {len(files)} arquivos encontrados")
    
    # Verifica arquivo de áudio ElevenLabs
    print("\nVerificando arquivos de áudio ElevenLabs:")
    elevenlabs_files = [f for f in os.listdir() if "ElevenLabs" in f]
    if elevenlabs_files:
        print(f"✅ {len(elevenlabs_files)} arquivos ElevenLabs encontrados:")
        for f in elevenlabs_files:
            print(f"   - {f}")
    else:
        print("❌ Nenhum arquivo ElevenLabs encontrado")

def check_audio_aligner():
    """Verifica o alinhador de áudio"""
    print("\nVerificando sistema de alinhamento de áudio:")
    
    try:
        from audio_aligner import AudioAligner
        print("✅ Módulo de alinhamento importado com sucesso")
        
        try:
            aligner = AudioAligner()
            print("✅ Alinhador de áudio inicializado com sucesso")
        except Exception as e:
            print(f"❌ Erro ao inicializar alinhador: {str(e)}")
    except ImportError as e:
        print(f"❌ Erro ao importar módulo de alinhamento: {str(e)}")
    
    # Verifica patch do PyTorch
    print("\nVerificando patch de compatibilidade do PyTorch:")
    try:
        import torch
        print(f"✅ PyTorch versão {torch.__version__}")
        
        # Verifica se a função load foi modificada
        if torch.load.__name__ == "patched_torch_load":
            print("✅ Patch do PyTorch aplicado")
        else:
            print("❌ Patch do PyTorch não aplicado")
    except Exception as e:
        print(f"❌ Erro ao verificar PyTorch: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("DIAGNÓSTICO DO SISTEMA DE PROCESSAMENTO DE ÁUDIO")
    print("=" * 50)
    
    check_python()
    check_audio_system()
    check_audio_aligner()
    
    print("\nDiagnóstico concluído!")
    print("=" * 50)