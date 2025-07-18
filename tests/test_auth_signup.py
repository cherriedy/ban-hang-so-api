"""
Unit tests for authentication signup functionality with store support.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from api.auth.services import create_user_service
from api.auth.schemas import UserSignup, StoreInfo, UserResponse


class TestAuthSignup:
    """Test authentication signup service with store functionality."""

    @pytest.fixture
    def valid_owner_signup_data(self):
        """Valid signup data for store owner."""
        return UserSignup(
            email="owner@example.com",
            password="password123",
            displayName="Store Owner",
            phone="1234567890",
            imageUrl="https://example.com/image.jpg",
            role="owner",
            storeInfo=StoreInfo(
                name="My Test Store",
                description="A test store for unit testing",
                imageUrl="https://example.com/store.jpg"
            ),
            storeId=None
        )

    @pytest.fixture
    def valid_staff_signup_data(self):
        """Valid signup data for staffs member."""
        return UserSignup(
            email="staffs@example.com",
            password="password123",
            displayName="Staff Member",
            phone="0987654321",
            role="staffs",
            storeId="existing_store_id",
            storeInfo=None
        )

    @pytest.fixture
    def mock_user_record(self):
        """Mock Firebase user record."""
        user_record = MagicMock()
        user_record.uid = "test_user_id"
        return user_record

    @pytest.fixture
    def mock_user_doc_data(self):
        """Mock user document data from Firestore."""
        return {
            "email": "owner@example.com",
            "contactName": "Store Owner",
            "phone": "1234567890",
            "imageUrl": "https://example.com/image.jpg",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            "stores": [{"id": "store_123", "role": "ADMIN"}]
        }

    @pytest.mark.asyncio
    async def test_owner_signup_success(self, valid_owner_signup_data, mock_user_record, mock_user_doc_data):
        """Test successful signup for store owner - creates new store."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock store document creation
            mock_store_ref = MagicMock()
            mock_store_ref.id = "store_123"
            mock_db.collection.return_value.document.return_value = mock_store_ref
            
            # Mock user document creation and retrieval
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = mock_user_doc_data
            mock_user_ref.get.return_value = mock_user_doc
            
            # Configure db collection calls
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

            # Call the service
            result = await create_user_service(valid_owner_signup_data)

            # Assertions
            assert isinstance(result, UserResponse)
            assert result.status == "success"
            assert result.data.id == "test_user_id"  # Check user ID is included
            assert result.data.email == "owner@example.com"
            assert result.data.contactName == "Store Owner"
            assert len(result.data.stores) == 1
            assert result.data.stores[0].id == "store_123"
            assert result.data.stores[0].role == "ADMIN"

            # Verify Firebase Auth was called correctly
            mock_auth.create_user.assert_called_once_with(
                email="owner@example.com",
                password="password123",
                display_name="Store Owner",
                photo_url="https://example.com/image.jpg"
            )

            # Verify store was created
            mock_store_ref.set.assert_called_once()
            store_data = mock_store_ref.set.call_args[0][0]
            assert store_data["name"] == "My Test Store"
            assert store_data["description"] == "A test store for unit testing"
            assert store_data["imageUrl"] == "https://example.com/store.jpg"

            # Verify user document was created
            mock_user_ref.set.assert_called_once()
            user_data = mock_user_ref.set.call_args[0][0]
            assert user_data["email"] == "owner@example.com"
            assert user_data["stores"] == [{"id": "store_123", "role": "ADMIN"}]

    @pytest.mark.asyncio
    async def test_staff_signup_success(self, valid_staff_signup_data, mock_user_record, mock_user_doc_data):
        """Test successful signup for staffs member - joins existing store."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock existing store document
            mock_store_ref = MagicMock()
            mock_store_doc = MagicMock()
            mock_store_doc.exists = True
            mock_store_ref.get.return_value = mock_store_doc
            
            # Mock user document creation and retrieval
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            
            # Update mock data for staffs
            staff_doc_data = mock_user_doc_data.copy()
            staff_doc_data["email"] = "staffs@example.com"
            staff_doc_data["contactName"] = "Staff Member"
            staff_doc_data["stores"] = [{"id": "existing_store_id", "role": "STAFF"}]
            mock_user_doc.to_dict.return_value = staff_doc_data
            mock_user_ref.get.return_value = mock_user_doc
            
            # Configure db collection calls
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

            # Call the service
            result = await create_user_service(valid_staff_signup_data)

            # Assertions
            assert isinstance(result, UserResponse)
            assert result.status == "success"
            assert result.data.id == "test_user_id"  # Check user ID is included
            assert result.data.email == "staffs@example.com"
            assert result.data.contactName == "Staff Member"
            assert len(result.data.stores) == 1
            assert result.data.stores[0].id == "existing_store_id"
            assert result.data.stores[0].role == "STAFF"

            # Verify Firebase Auth was called correctly
            mock_auth.create_user.assert_called_once_with(
                email="staffs@example.com",
                password="password123",
                display_name="Staff Member",
                photo_url=None
            )

            # Verify store existence was checked
            mock_store_ref.get.assert_called_once()

            # Verify no new store was created (only set should be for user)
            mock_store_ref.set.assert_not_called()

            # Verify user document was created
            mock_user_ref.set.assert_called_once()
            user_data = mock_user_ref.set.call_args[0][0]
            assert user_data["stores"] == [{"id": "existing_store_id", "role": "STAFF"}]

    @pytest.mark.asyncio
    async def test_owner_signup_missing_store_info(self):
        """Test owner signup fails when store info is missing."""
        signup_data = UserSignup(
            email="owner@example.com",
            password="password123",
            role="owner"
            # Missing storeInfo
        )

        with pytest.raises(ValueError) as exc_info:
            await create_user_service(signup_data)

        assert "Store information is required for owner role" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_staff_signup_missing_store_id(self):
        """Test staffs signup fails when store ID is missing."""
        signup_data = UserSignup(
            email="staffs@example.com",
            password="password123",
            role="staffs"
            # Missing storeId
        )

        with pytest.raises(ValueError) as exc_info:
            await create_user_service(signup_data)

        assert "Store ID is required for staffs role" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_role(self):
        """Test signup fails with invalid role."""
        signup_data = UserSignup(
            email="user@example.com",
            password="password123",
            role="invalid_role"
        )

        with pytest.raises(ValueError) as exc_info:
            await create_user_service(signup_data)

        assert "Role must be either 'owner' or 'staffs'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_staff_signup_nonexistent_store(self, valid_staff_signup_data):
        """Test staffs signup fails when store doesn't exist."""
        with patch('api.auth.services.db') as mock_db:
            # Mock nonexistent store
            mock_store_ref = MagicMock()
            mock_store_doc = MagicMock()
            mock_store_doc.exists = False
            mock_store_ref.get.return_value = mock_store_doc
            
            mock_db.collection.return_value.document.return_value = mock_store_ref

            with pytest.raises(ValueError) as exc_info:
                await create_user_service(valid_staff_signup_data)

            assert "Store with ID existing_store_id does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_on_firestore_failure(self, valid_owner_signup_data, mock_user_record):
        """Test rollback when Firestore operations fail."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_auth.create_user.return_value = mock_user_record
            mock_auth.delete_user = MagicMock()
            
            # Mock store creation success
            mock_store_ref = MagicMock()
            mock_store_ref.id = "store_123"
            mock_store_ref.delete = MagicMock()
            
            # Mock user document creation failure
            mock_user_ref = MagicMock()
            mock_user_ref.set.side_effect = Exception("Firestore error")
            
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

            with pytest.raises(Exception) as exc_info:
                await create_user_service(valid_owner_signup_data)

            assert "Firestore error" in str(exc_info.value)

            # Verify rollback was attempted
            mock_auth.delete_user.assert_called_once_with("test_user_id")
            mock_store_ref.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_staff_signup_no_store_rollback(self, valid_staff_signup_data, mock_user_record):
        """Test that store rollback is not attempted for staffs signup failures."""
        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            # Setup mocks
            mock_auth.create_user.return_value = mock_user_record
            mock_auth.delete_user = MagicMock()
            
            # Mock existing store
            mock_store_ref = MagicMock()
            mock_store_doc = MagicMock()
            mock_store_doc.exists = True
            mock_store_ref.get.return_value = mock_store_doc
            mock_store_ref.delete = MagicMock()
            
            # Mock user document creation failure
            mock_user_ref = MagicMock()
            mock_user_ref.set.side_effect = Exception("Firestore error")
            
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

            with pytest.raises(Exception):
                await create_user_service(valid_staff_signup_data)

            # Verify user rollback was attempted
            mock_auth.delete_user.assert_called_once_with("test_user_id")
            # Verify store rollback was NOT attempted (staffs doesn't create stores)
            mock_store_ref.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_owner_store_creation_without_image(self):
        """Test owner signup with store info but no store image."""
        signup_data = UserSignup(
            email="owner@example.com",
            password="password123",
            displayName="Store Owner",
            role="owner",
            storeInfo=StoreInfo(
                name="My Store",
                description="A store without image"
                # No imageUrl
            )
        )

        with patch('api.auth.services.auth') as mock_auth, \
             patch('api.auth.services.db') as mock_db:
            
            mock_user_record = MagicMock()
            mock_user_record.uid = "test_user_id"
            mock_auth.create_user.return_value = mock_user_record
            
            # Mock store and user creation
            mock_store_ref = MagicMock()
            mock_store_ref.id = "store_123"
            mock_user_ref = MagicMock()
            mock_user_doc = MagicMock()
            mock_user_doc.exists = True
            mock_user_doc.to_dict.return_value = {
                "email": "owner@example.com",
                "contactName": "Store Owner",
                "stores": [{"id": "store_123", "role": "ADMIN"}],
                "createdAt": datetime.now(),
                "updatedAt": datetime.now()
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

            result = await create_user_service(signup_data)

            # Verify store was created without imageUrl
            mock_store_ref.set.assert_called_once()
            store_data = mock_store_ref.set.call_args[0][0]
            assert "imageUrl" not in store_data
            assert store_data["name"] == "My Store"
            assert store_data["description"] == "A store without image"

            assert result.status == "success"

