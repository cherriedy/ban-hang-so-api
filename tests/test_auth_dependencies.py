"""
Unit tests for authentication and authorization dependencies.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from api.auth.dependencies import (
    get_current_user_id,
    verify_store_access,
    get_authorized_store_access
)


class TestAuthDependencies:
    """Test authentication and authorization dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_id_success(self):
        """Test successful user ID extraction from valid token."""
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {"uid": "user123"}

            user_id = await get_current_user_id("Bearer valid_token")

            assert user_id == "user123"
            mock_verify.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_header(self):
        """Test error when authorization header is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(None)

        assert exc_info.value.status_code == 401
        assert "Authorization header is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self):
        """Test error when token is invalid."""
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id("Bearer invalid_token")

            assert exc_info.value.status_code == 401
            assert "Invalid authentication token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_store_access_success(self, mock_firestore):
        """Test successful store access verification."""
        # Mock user document with store access
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {
            "stores": [
                {"id": "store123", "role": "ADMIN"},
                {"id": "store456", "role": "MEMBER"}
            ]
        }

        user_ref = MagicMock()
        user_ref.get.return_value = user_doc

        mock_firestore.collection.return_value.document.return_value = user_ref

        result = await verify_store_access("user123", "store123")

        assert result == {"id": "store123", "role": "ADMIN"}
        mock_firestore.collection.assert_called_with('users')

    @pytest.mark.asyncio
    async def test_verify_store_access_user_not_found(self, mock_firestore):
        """Test error when user doesn't exist."""
        user_doc = MagicMock()
        user_doc.exists = False

        user_ref = MagicMock()
        user_ref.get.return_value = user_doc

        mock_firestore.collection.return_value.document.return_value = user_ref

        with pytest.raises(HTTPException) as exc_info:
            await verify_store_access("nonexistent_user", "store123")

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_store_access_no_permission(self, mock_firestore):
        """Test error when user doesn't have access to store."""
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {
            "stores": [
                {"id": "store456", "role": "MEMBER"}
            ]
        }

        user_ref = MagicMock()
        user_ref.get.return_value = user_doc

        mock_firestore.collection.return_value.document.return_value = user_ref

        with pytest.raises(HTTPException) as exc_info:
            await verify_store_access("user123", "store123")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_authorized_store_access_success(self):
        """Test successful combined authentication and authorization."""
        with patch('api.auth.dependencies.verify_store_access') as mock_verify:
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            # Test the function by calling it with a mock user_id directly
            # since this is how it would be called by FastAPI after dependency injection
            from api.auth.dependencies import get_authorized_store_access

            result = await get_authorized_store_access("store123", "user123")

            assert result == ("user123", {"id": "store123", "role": "ADMIN"})
            mock_verify.assert_called_once_with("user123", "store123")

    @pytest.mark.asyncio
    async def test_get_authorized_store_access_with_dependency_injection(self):
        """Test the dependency injection aspect of get_authorized_store_access."""
        # This test verifies that the function signature is correct for FastAPI
        from api.auth.dependencies import get_authorized_store_access
        import inspect

        # Check that the function has the correct signature for dependency injection
        sig = inspect.signature(get_authorized_store_access)

        # Verify parameters
        assert 'store_id' in sig.parameters
        assert 'user_id' in sig.parameters

        # Verify that user_id has a default value (the Depends object)
        user_id_param = sig.parameters['user_id']
        assert user_id_param.default is not None

