"""
PyTorch 2.6 compatibility patch for WhisperX.
This module helps with the loading of WhisperX models in PyTorch 2.6
which has changed the default behavior of torch.load to use weights_only=True.
"""

import torch
from omegaconf import ListConfig
import sys
import warnings

def patch_torch_for_whisperx():
    """
    Apply patch for PyTorch 2.6 compatibility with WhisperX models.
    This adds necessary omegaconf classes to the safe globals for torch.load.
    """
    try:
        # Check PyTorch version
        torch_version = torch.__version__
        major, minor = map(int, torch_version.split('.')[:2])
        
        if major >= 2 and minor >= 6:
            print(f"🔧 Detected PyTorch {torch_version} - applying compatibility patch for WhisperX")
            
            # Import necessary classes from omegaconf
            from omegaconf import ListConfig, DictConfig, OmegaConf
            from omegaconf.base import ContainerMetadata, Node
            
            # Add all necessary omegaconf classes to safe globals
            torch.serialization.add_safe_globals([
                ListConfig, 
                DictConfig, 
                ContainerMetadata, 
                Node,
                OmegaConf
            ])
            
            # Set safer loading option - Use this if the above doesn't work
            torch._C._set_default_weights_only_false_is_allowed(True)
            
            print("✅ Successfully patched torch.load for WhisperX compatibility")
        else:
            print(f"ℹ️ PyTorch {torch_version} detected - no patch needed for WhisperX")
            
    except Exception as e:
        warnings.warn(f"Failed to apply PyTorch compatibility patch: {e}")
        print(f"⚠️ Warning: WhisperX may fail to load models with PyTorch 2.6+")

# Apply patch when module is imported
patch_torch_for_whisperx()