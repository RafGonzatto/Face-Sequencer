"""
Face-Sequencer - Script de inicialização
Este é o único script para iniciar a aplicação Face-Sequencer.
"""

import os
import sys
import subprocess
import platform
import importlib
import logging
from pathlib import Path

# ============================================================================
# CRITICAL FIX: Register PyTorch 2.6+ safe globals BEFORE any imports
# ============================================================================
try:
    import torch
    if hasattr(torch, '__version__'):
        major, minor = map(int, torch.__version__.split(".")[:2])
        if (major > 2) or (major == 2 and minor >= 6):
            print(f"[PYTORCH] Detected PyTorch {torch.__version__} - registering safe globals")
            try:
                import omegaconf
                classes_to_register = []
                # Main classes
                for attr_name in ['ListConfig', 'DictConfig', 'OmegaConf']:
                    cls = getattr(omegaconf, attr_name, None)
                    if cls:
                        classes_to_register.append(cls)
                # Internal classes
                try:
                    from omegaconf.base import ContainerMetadata, Node
                    classes_to_register.extend([ContainerMetadata, Node])
                except:
                    pass
                if classes_to_register:
                    torch.serialization.add_safe_globals(classes_to_register)
                    print(f"[PYTORCH] ✅ Registered {len(classes_to_register)} OmegaConf classes as safe globals")
            except Exception as e:
                print(f"[WARNING] Failed to register safe globals: {e}")
except Exception as e:
    print(f"[INFO] PyTorch check skipped: {e}")
# ============================================================================

# Detecta se estamos sendo executados pelo reloader do Flask
# O Flask define esta variável de ambiente quando faz o reload
is_flask_reloading = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

# Define o diretório raiz do projeto como diretório atual
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Ajuste de PYTHONPATH: a versão anterior removia TUDO que começava com o diretório do projeto,
# incluindo o path do virtualenv (ex: <project>/.venv/Lib/site-packages), quebrando imports como flask.
# Agora apenas garantimos que o project_root está no início sem descartar site-packages.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# (Opcional) Poderíamos remover entradas claramente inválidas, mas não filtramos mais por prefixo
# para não excluir o ambiente virtual.

# Importa e configura o logger centralizado apenas uma vez
if not is_flask_reloading:
    from app.core.utils.logger import setup_logging
    # Configura o logging centralizado
    setup_logging()
else:
    # Em modo de recarregamento, importa sem configurar
    from app.core.utils.logger import setup_logging

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("[X] Python 3.8 ou superior é necessário")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"[CHECK] Versão do Python: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Verifica se as dependências principais estão instaladas"""
    # Define as dependências e seus módulos de importação (alguns pacotes têm nomes diferentes)
    dependencies = {
        'flask': 'flask',
        'numpy': 'numpy',
        'pillow': 'PIL'  # Pillow é importado como PIL
    }
    missing = []
    
    for package_name, import_name in dependencies.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print(f"[X] Dependências ausentes: {', '.join(missing)}")
        print("   Execute 'pip install -r requirements.txt' para instalar as dependências")
        return False
    
    print("[CHECK] Dependências principais verificadas")
    return True

# Somente executar as verificações quando não estiver em modo de recarregamento
if not is_flask_reloading:
    # Informações de inicialização
    print("\n" + "="*50)
    print("Face-Sequencer - Sistema de Animação Facial".center(50))
    print("="*50)
    print(f"\nDiretório do projeto: {project_root}")

    # Verifica versão do Python
    if not check_python_version():
        sys.exit(1)

    # Verifica dependências
    if not check_dependencies():
        print("\nVocê deseja instalar as dependências agora? (s/n)")
        choice = input().strip().lower()
        if choice == 's':
            try:
                print("Instalando dependências...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                print("[CHECK] Dependências instaladas com sucesso")
            except Exception as e:
                print(f"[X] Erro ao instalar dependências: {e}")
                sys.exit(1)
        else:
            print("Inicialização cancelada.")
            sys.exit(1)

# Importa módulo app diretamente sem usar estrutura de pacotes
if not is_flask_reloading:
    print("\nImportando módulos...")
try:
    from app.app import create_app
except ModuleNotFoundError as e:
    # Tentativa final: se for falha de flask (ou dependência chave) tentar instalar requirements e reimportar
    missing_mod = str(e)
    if 'flask' in missing_mod.lower():
        print("[AUTO] Flask não encontrado após ajuste de PATH. Tentando reinstalar dependências...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            from app.app import create_app
        except Exception as inst_err:
            print(f"[AUTO] Falha ao reinstalar dependências: {inst_err}")
            raise
    else:
        raise

if __name__ == "__main__":
    try:
        # Cria e executa a aplicação
        app = create_app()
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 5000))
        
        # Determina se deve executar em modo debug com base na variável de ambiente
        debug_mode = os.environ.get('DEBUG', '1').lower() not in ('0', 'false', 'no')
        
        # Exibe mensagem de sucesso apenas na primeira execução, não no reload
        if not is_flask_reloading:
            print("\n" + "-"*50)
            print(f"Servidor iniciado {'em modo debug' if debug_mode else 'em modo produção'}!")
            print(f"Acesse: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
            print("-"*50 + "\n")
        
        # Use_reloader precisa estar desabilitado se estamos em ambiente que não suporta fork
        # ou se queremos evitar problemas com processos duplicados
        app.run(debug=debug_mode, host=host, port=port, use_reloader=debug_mode)
    except Exception as e:
        print(f"Erro ao iniciar o servidor: {e}")
        import traceback
        traceback.print_exc()
        
        # Informações de diagnóstico em caso de erro
        print("\n=== Informações de diagnóstico ===")
        print("Caminhos Python:")
        for i, path in enumerate(sys.path[:5]):
            print(f"  {i}: {path}")
        
        # Verifica se os arquivos principais existem
        print("\nVerificando arquivos principais:")
        files_to_check = [
            os.path.join(project_root, 'app', 'app.py'),
            os.path.join(project_root, 'app', 'core', 'utils', 'config.py'),
            os.path.join(project_root, 'app', 'services', 'lipanim_core_demo.py')
        ]
        for file_path in files_to_check:
            status = "[CHECK] Existe" if os.path.exists(file_path) else "[X] Não encontrado"
            print(f"  {file_path}: {status}")
            
        sys.exit(1)