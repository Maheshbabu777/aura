"""
PyTest configuration and fixtures for AURA tests.
"""

import os
import sys
import pytest
import certifi

# Fix SSL certificate path for Windows
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Add backend to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
