"""
pytest config — ensures the app modules are importable when running from repo root.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP  = os.path.dirname(HERE)
if APP not in sys.path:
    sys.path.insert(0, APP)
