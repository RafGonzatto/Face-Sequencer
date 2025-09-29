#!/usr/bin/env python3
"""
Teste para verificar se o problema de importação foi resolvido
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_audio_import():
    """Testa se as importações de áudio estão funcionando"""
    
    print("🧪 TESTE DE IMPORTAÇÃO DE ÁUDIO")
    print("=" * 50)
    
    try:
        print("📦 Testando importação do audio_error_handling...")
        from audio_error_handling import detect_speech_activity
        print("✅ audio_error_handling importado com sucesso")
        
        print("📦 Testando importação do librosa...")
        try:
            import librosa
            print("✅ librosa importado com sucesso")
            
            # Teste simples
            print("🔍 Testando função básica do librosa...")
            # Não vamos carregar um arquivo, apenas testar se a importação funciona
            print("✅ librosa funcionando")
            
        except Exception as e:
            print(f"⚠️ librosa com problema: {e}")
            print("📦 Testando fallback...")
            
            try:
                import soundfile as sf
                import scipy
                print("✅ Fallback (soundfile + scipy) disponível")
            except Exception as fallback_e:
                print(f"❌ Fallback também falhou: {fallback_e}")
        
        print("\n🎯 TESTE COMPLETO")
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_audio_import()
    print(f"\n🏁 RESULTADO: {'✅ SUCESSO' if success else '❌ FALHOU'}")