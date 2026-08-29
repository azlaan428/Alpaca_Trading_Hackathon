import sys
import os
from pathlib import Path

# Add src directory to sys.path so investment_agent package is importable
_src_path = str(Path(__file__).parent.parent / 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
