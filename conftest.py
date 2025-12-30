"""pytest configuration file."""

import sys
from pathlib import Path

# Add the project root to the Python path so imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
