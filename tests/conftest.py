"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add repo root, src/, and framework/ to sys.path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "framework"))
