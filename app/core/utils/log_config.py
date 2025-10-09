"""
Configuração simplificada de logging para o aplicativo
"""

import logging
import os
from datetime import datetime

def configure_logging():
    """
    Configura o sistema de logging para evitar mensagens duplicadas.
    Esta função deve ser chamada apenas uma vez no início da execução do programa.
    """
    # Limpa todos os handlers existentes para evitar duplicações
    root = logging.getLogger()
    
    # Remove qualquer handler existente
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
    
    # Configura o nível do root logger
    root.setLevel(logging.INFO)
    
    # Cria o diretório de logs se não existir
    os.makedirs('logs', exist_ok=True)
    
    # Formato consistente para todos os logs
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Adiciona um handler para arquivo
    log_file = f'logs/face_sequencer_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    
    # Configura o logger para o Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)  # Reduz o nível para diminuir mensagens
    
    return root