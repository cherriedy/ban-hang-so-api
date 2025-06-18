"""
This module contains pytest fixtures and configuration for testing.
"""
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add the project's root directory to the system path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import the main app
from main import app


@pytest.fixture
def test_app():
    """
    Create a FastAPI test application.
    """
    return app


@pytest.fixture
def client(test_app):
    """
    Create a test client for the FastAPI application.
    """
    return TestClient(test_app)


@pytest.fixture
def mock_firestore():
    """
    Create a mock for the Firestore client.
    """
    with patch('firebase_admin.firestore.client') as mock:
        # Configure the mock to provide the necessary methods and return values
        firestore_mock = MagicMock()
        mock.return_value = firestore_mock
        yield firestore_mock


@pytest.fixture
def mock_auth():
    """
    Create a mock for Firebase Auth.
    """
    with patch('firebase_admin.auth') as mock:
        yield mock
