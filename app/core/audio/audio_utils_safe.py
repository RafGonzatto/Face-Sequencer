"""
Utilidades para importação segura de librosa e outras bibliotecas de áudio.
Resolve conflitos entre coverage/numba e outras incompatibilidades.
"""

import os
import sys
from typing import Optional, Any, Dict

def safe_librosa_import():
    """
    Importa librosa de forma segura, resolvendo conflitos de dependências.
    
    Returns:
        tuple: (librosa_module, numpy_module) ou (None, None) se falhar
    """
    try:
        # Store coverage environment variables that may conflict
        coverage_vars = ['COVERAGE_PROCESS_START', 'COV_CORE_SOURCE', 'COV_CORE_CONFIG', 'COVERAGE_FILE']
        stored_vars = {}
        
        for var in coverage_vars:
            if var in os.environ:
                stored_vars[var] = os.environ[var]
                del os.environ[var]
        
        # Try importing librosa
        import librosa
        import numpy as np
        
        # Restore coverage variables
        for var, value in stored_vars.items():
            os.environ[var] = value
        
        return librosa, np
        
    except ImportError as e:
        print(f"[WARNING]  Warning: librosa import failed: {e}")
        return None, None
    except Exception as e:
        print(f"[WARNING]  Warning: librosa import error: {e}")
        # Try restoring environment
        try:
            for var, value in stored_vars.items():
                os.environ[var] = value
        except:
            pass
        return None, None

def safe_audio_imports():
    """
    Importa todas as bibliotecas de áudio necessárias de forma segura.
    
    Returns:
        dict: Dicionário com os módulos importados (ou None se falharam)
    """
    modules = {}
    
    # Try librosa
    librosa, numpy = safe_librosa_import()
    modules['librosa'] = librosa
    modules['numpy'] = numpy
    
    # Try other audio libraries
    try:
        import soundfile as sf
        modules['soundfile'] = sf
    except ImportError:
        modules['soundfile'] = None
    
    try:
        import scipy
        modules['scipy'] = scipy
    except ImportError:
        modules['scipy'] = None
    
    try:
        import torch
        modules['torch'] = torch
    except ImportError:
        modules['torch'] = None
        
    return modules

def get_audio_loader():
    """
    Retorna uma função para carregar arquivos de áudio, usando a melhor biblioteca disponível.
    
    Returns:
        callable: Função que aceita (file_path, sr=None) e retorna (y, sr)
    """
    modules = safe_audio_imports()
    
    if modules['librosa'] is not None:
        # Use librosa if available
        def load_with_librosa(file_path, sr=None):
            try:
                return modules['librosa'].load(file_path, sr=sr)
            except Exception as e:
                # Runtime import error (numba/coverage) or other issue – fallback
                print(f"[WARNING]  librosa runtime load failed, falling back to soundfile: {e}")
                if modules.get('soundfile') is not None:
                    import soundfile as sf
                    y, original_sr = sf.read(file_path)
                    if len(y.shape) > 1:
                        y = y.mean(axis=1)
                    if sr is not None and sr != original_sr:
                        try:
                            from scipy import signal
                            num_samples = int(len(y) * sr / original_sr)
                            y = signal.resample(y, num_samples)
                            return y, sr
                        except Exception:
                            pass
                    return y, original_sr
                raise
        return load_with_librosa
    
    elif modules['soundfile'] is not None:
        # Use soundfile as fallback
        def load_with_soundfile(file_path, sr=None):
            import soundfile as sf
            y, original_sr = sf.read(file_path)
            
            # Convert stereo to mono if needed
            if len(y.shape) > 1:
                y = y.mean(axis=1)
            
            # Resample if needed (basic resampling)
            if sr is not None and sr != original_sr:
                # Simple resampling - not as good as librosa but works
                from scipy import signal
                num_samples = int(len(y) * sr / original_sr)
                y = signal.resample(y, num_samples)
                return y, sr
            
            return y, original_sr
            
        return load_with_soundfile
    
    else:
        # No audio loading available
        def no_loader(file_path, sr=None):
            raise ImportError("No audio loading library available. Install librosa or soundfile.")
        return no_loader

def get_feature_extractor():
    """
    Retorna funções para extração de features de áudio.
    
    Returns:
        dict: Dicionário com funções de extração de features
    """
    modules = safe_audio_imports()
    features = {}
    
    if modules['librosa'] is not None:
        # Use librosa features
        features['rms'] = lambda y: modules['librosa'].feature.rms(y=y)[0]
        features['mfcc'] = lambda y, sr: modules['librosa'].feature.mfcc(y=y, sr=sr)
        features['duration'] = lambda y, sr: modules['librosa'].get_duration(y=y, sr=sr)
        features['frames_to_time'] = lambda frames, sr: modules['librosa'].frames_to_time(frames, sr=sr)
        
    else:
        # Fallback implementations
        import numpy as np
        
        def simple_rms(y):
            # Simple RMS calculation
            window_size = 2048
            hop_size = 512
            rms = []
            for i in range(0, len(y) - window_size, hop_size):
                window = y[i:i + window_size]
                rms.append(np.sqrt(np.mean(window ** 2)))
            return np.array(rms)
        
        features['rms'] = simple_rms
        features['mfcc'] = None  # Not implemented in fallback
        features['duration'] = lambda y, sr: len(y) / sr
        features['frames_to_time'] = lambda frames, sr: frames / (sr / 512)  # Approximate
    
    return features

# Pre-load modules once
_cached_modules = None

def get_cached_audio_modules():
    """Retorna módulos de áudio já carregados (cache)"""
    global _cached_modules
    if _cached_modules is None:
        _cached_modules = safe_audio_imports()
    return _cached_modules

# Conveniência para importar no código existente
def import_librosa():
    """
    Importa librosa de forma segura, para substituição direta no código existente.
    
    Returns:
        tuple: (librosa, numpy) ou lança ImportError se não disponível
    """
    librosa, numpy = safe_librosa_import()
    if librosa is None:
        raise ImportError("librosa not available or failed to import")
    return librosa, numpy