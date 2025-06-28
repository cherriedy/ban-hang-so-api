"""
Integration tests for the signup endpoint with store functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import json


class TestSignupEndpoint:
    """Test the signup endpoint integration."""

    @pytest.fixture
    def owner_signup_payload(self):
        """Valid owner signup payload."""
        return {
            "email": "owner@example.com",
            "password": "password123",
            "displayName": "Store Owner",
            "phone": "1234567890",
            "imageUrl": "https://example.com/image.jpg",
            "role": "owner",
            "storeInfo": {
                "name": "Integration Test Store",
                "description": "A store created during integration testing",
                "imageUrl": "https://example.com/store.jpg"
            }
        }

    @pytest.fixture
    def staff_signup_payload(self):
        """Valid staff signup payload."""
        return {
            "email": "staff@example.com",
            "password": "password123",
            "displayName": "Staff Member",
            "phone": "0987654321",
            "role": "staff",
            "storeId": "existing_store_id"
        }

    def test_owner_signup_endpoint_success(self, client, owner_signup_payload):
        """Test successful owner signup through the API endpoint."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_user_record = MagicMock()
            mock_user_record.uid = "test_user_id"
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock store creation
            mock_store_ref = MagicMock()
            mock_store_ref.id = "store_123"
            
            # Mock user document
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = {
                "email": "owner@example.com",
                "contactName": "Store Owner",
                "phone": "1234567890",
                "imageUrl": "https://example.com/image.jpg",
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
                "stores": [{"id": "store_123", "role": "ADMIN"}]
            }
            mock_user_ref.get.return_value = mock_user_doc
            
            def collection_side_effect(collection_name):
                if collection_name == 'stores':
                    stores_collection = MagicMock()
                    stores_collection.document.return_value = mock_store_ref
                    return stores_collection
                elif collection_name == 'users':
                    users_collection = MagicMock()
                    users_collection.document.return_value = mock_user_ref
                    return users_collection
            
            mock_db.collection.side_effect = collection_side_effect

            # Make API call
            response = client.post("/auth/signup", json=owner_signup_payload)

            # Assertions
            assert response.status_code == 201
            data = response.json()
            
            assert data["status"] == "success"
            assert data["data"]["email"] == "owner@example.com"
            assert data["data"]["contactName"] == "Store Owner"
            assert len(data["data"]["stores"]) == 1
            assert data["data"]["stores"][0]["id"] == "store_123"
            assert data["data"]["stores"][0]["role"] == "ADMIN"

    def test_staff_signup_endpoint_success(self, client, staff_signup_payload):
        """Test successful staff signup through the API endpoint."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_user_record = MagicMock()
            mock_user_record.uid = "test_user_id"
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock existing store check
            mock_store_ref = MagicMock()
            mock_store_doc = MagicMock()
            mock_store_doc.exists = True
            mock_store_ref.get.return_value = mock_store_doc
            
            # Mock user document
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = {
                "email": "staff@example.com",
                "contactName": "Staff Member",
                "phone": "0987654321",
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
                "stores": [{"id": "existing_store_id", "role": "STAFF"}]
            }
            mock_user_ref.get.return_value = mock_user_doc
            
            def collection_side_effect(collection_name):
                if collection_name == 'stores':
                    stores_collection = MagicMock()
                    stores_collection.document.return_value = mock_store_ref
                    return stores_collection
                elif collection_name == 'users':
                    users_collection = MagicMock()
                    users_collection.document.return_value = mock_user_ref
                    return users_collection
            
            mock_db.collection.side_effect = collection_side_effect

            # Make API call
            response = client.post("/auth/signup", json=staff_signup_payload)

            # Assertions
            assert response.status_code == 201
            data = response.json()
            
            assert data["status"] == "success"
            assert data["data"]["email"] == "staff@example.com"
            assert data["data"]["contactName"] == "Staff Member"
            assert len(data["data"]["stores"]) == 1
            assert data["data"]["stores"][0]["id"] == "existing_store_id"
            assert data["data"]["stores"][0]["role"] == "STAFF"

    def test_signup_invalid_role_400(self, client):
        """Test signup with invalid role returns 400."""
        payload = {
            "email": "user@example.com",
            "password": "password123",
            "role": "invalid_role"
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Role must be either 'owner' or 'staff'" in data["message"]

    def test_signup_owner_missing_store_info_400(self, client):
        """Test owner signup without store info returns 400."""
        payload = {
            "email": "owner@example.com",
            "password": "password123",
            "role": "owner"
            # Missing storeInfo
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Store information is required for owner role" in data["message"]

    def test_signup_staff_missing_store_id_400(self, client):
        """Test staff signup without store ID returns 400."""
        payload = {
            "email": "staff@example.com",
            "password": "password123",
            "role": "staff"
            # Missing storeId
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Store ID is required for staff role" in data["message"]

    def test_signup_staff_nonexistent_store_400(self, client, staff_signup_payload):
        """Test staff signup with nonexistent store returns 400."""
        with patch('api.auth.services.db') as mock_db:
            # Mock nonexistent store
            mock_store_ref = MagicMock()
            mock_store_doc = MagicMock()
            mock_store_doc.exists = False
            mock_store_ref.get.return_value = mock_store_doc
            
            mock_db.collection.return_value.document.return_value = mock_store_ref

            response = client.post("/auth/signup", json=staff_signup_payload)
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "does not exist" in data["message"]

    def test_signup_invalid_email_422(self, client):
        """Test signup with invalid email returns 422."""
        payload = {
            "email": "invalid-email",
            "password": "password123",
            "role": "owner",
            "storeInfo": {
                "name": "Test Store",
                "description": "Test Description"
            }
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422

    def test_signup_short_password_422(self, client):
        """Test signup with short password returns 422."""
        payload = {
            "email": "user@example.com",
            "password": "123",  # Too short
            "role": "owner",
            "storeInfo": {
                "name": "Test Store",
                "description": "Test Description"
            }
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422

    def test_signup_missing_required_fields_422(self, client):
        """Test signup with missing required fields returns 422."""
        payload = {
            "email": "user@example.com"
            # Missing password and role
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422

    def test_signup_firebase_auth_error_400(self, client, owner_signup_payload):
        """Test signup when Firebase Auth fails returns 400."""
        with patch('api.auth.services.auth') as mock_auth:
            mock_auth.create_user.side_effect = Exception("Firebase Auth error")

            response = client.post("/auth/signup", json=owner_signup_payload)
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "Firebase Auth error" in data["message"]

    def test_signup_firestore_error_400(self, client, owner_signup_payload):
        """Test signup when Firestore fails returns 400."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            mock_user_record = MagicMock()
            mock_user_record.uid = "test_user_id"
            mock_auth.create_user.return_value = mock_user_record
            mock_auth.delete_user = MagicMock()  # For rollback
            
            # Mock Firestore error
            mock_db.collection.side_effect = Exception("Firestore error")

            response = client.post("/auth/signup", json=owner_signup_payload)
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "Firestore error" in data["message"]

            # Verify rollback was attempted
            mock_auth.delete_user.assert_called_once_with("test_user_id")

    def test_signup_store_info_validation(self, client):
        """Test store info validation for owner signup."""
        # Test missing store name
        payload = {
            "email": "owner@example.com",
            "password": "password123",
            "role": "owner",
            "storeInfo": {
                "description": "Missing name"
                # Missing required name field
            }
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422

        # Test missing store description
        payload = {
            "email": "owner@example.com",
            "password": "password123",
            "role": "owner",
            "storeInfo": {
                "name": "Test Store"
                # Missing required description field
            }
        }

        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422

    def test_signup_optional_fields(self, client):
        """Test signup with minimal required fields works."""
        payload = {
            "email": "minimal@example.com",
            "password": "password123",
            "role": "owner",
            "storeInfo": {
                "name": "Minimal Store",
                "description": "Basic store"
                # No optional fields like imageUrl, displayName, phone
            }
        }

        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            mock_user_record = MagicMock()
            mock_user_record.uid = "test_user_id"
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock successful store and user creation
            mock_store_ref = MagicMock()
            mock_store_ref.id = "store_123"
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = {
                "email": "minimal@example.com",
                "contactName": None,
                "phone": None,
                "imageUrl": None,
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
                "stores": [{"id": "store_123", "role": "ADMIN"}]
            }
            mock_user_ref.get.return_value = mock_user_doc
            
            def collection_side_effect(collection_name):
                if collection_name == 'stores':
                    stores_collection = MagicMock()
                    stores_collection.document.return_value = mock_store_ref
                    return stores_collection
                elif collection_name == 'users':
                    users_collection = MagicMock()
                    users_collection.document.return_value = mock_user_ref
                    return users_collection
            
            mock_db.collection.side_effect = collection_side_effect

            response = client.post("/auth/signup", json=payload)
            assert response.status_code == 201
            
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["email"] == "minimal@example.com"
            assert data["data"]["contactName"] is None
            assert data["data"]["phone"] is None
            assert data["data"]["imageUrl"] is None
