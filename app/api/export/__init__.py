"""Export package initialization module."""
from pathlib import Path
import sys

# Ensure this directory is in the path
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Make lipanim_core_demo available for import directly from this package
try:
    from . import lipanim_core_demo
except ImportError:
    # If that fails, try to import from the services directory
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services"))
    try:
        import lipanim_core_demo
    except ImportError:
        # Last resort - import from root directory
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        import lipanim_core_demo
