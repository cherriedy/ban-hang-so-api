"""
Integration tests for product API endpoints with multi-store support.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException


class TestProductEndpoints:
    """Test product API endpoints with store authentication."""

    def test_list_products_success(self, client, mock_firestore):
        """Test successful product listing with valid store access."""
        # Mock authentication
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify:

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            # Mock firestore data
            count_result = MagicMock()
            count_result.value = 1
            mock_count_query = MagicMock()
            mock_count_query.get.return_value = [[count_result]]

            product_doc = MagicMock()
            product_doc.id = "product1"
            product_doc.to_dict.return_value = {
                "name": "Test Product",
                "store_id": "store123",
                "sellingPrice": 100,
                "stockQuantity": 10,
                "status": True,
                "description": "",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "avatarUrl": None
            }

            mock_collection = MagicMock()
            mock_where = MagicMock()
            mock_order_by = MagicMock()
            mock_limit = MagicMock()

            mock_collection.where.return_value = mock_where
            mock_where.count.return_value = mock_count_query
            mock_where.order_by.return_value = mock_order_by
            mock_order_by.limit.return_value = mock_limit
            mock_limit.get.return_value = [product_doc]

            mock_firestore.collection.return_value = mock_collection

            response = client.get(
                "/products?store_id=store123&page=1&size=10",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["data"]["items"]) == 1
            assert data["data"]["items"][0]["name"] == "Test Product"

    def test_list_products_unauthorized(self, client):
        """Test product listing without authentication."""
        response = client.get("/products?store_id=store123")

        # The dependency will fail before reaching the endpoint logic
        assert response.status_code == 422  # Unprocessable Entity due to missing dependency
        # OR we can expect a 500 if the dependency fails differently
        assert response.status_code in [422, 500]

    def test_list_products_no_store_access(self, client, mock_firestore):
        """Test product listing when user has no access to store."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify:

            mock_get_user.return_value = "user123"
            # Make verify_store_access raise an HTTPException instead of a generic Exception
            mock_verify.side_effect = HTTPException(status_code=403, detail="Access denied")

            response = client.get(
                "/products?store_id=store123",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200  # JSendResponse wraps errors
            data = response.json()
            assert data["status"] == "error"
            assert "Access denied" in data["message"]

    def test_get_product_success(self, client, mock_firestore):
        """Test successful product retrieval by ID."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify:

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            product_doc = MagicMock()
            product_doc.exists = True
            product_doc.to_dict.return_value = {
                "name": "Test Product",
                "store_id": "store123",
                "sellingPrice": 100,
                "stockQuantity": 10,
                "status": True,
                "description": "",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "avatarUrl": None
            }

            doc_ref = MagicMock()
            doc_ref.get.return_value = product_doc
            doc_ref.id = "product123"  # Set the id property properly

            collection_ref = MagicMock()
            collection_ref.document.return_value = doc_ref

            mock_firestore.collection.return_value = collection_ref

            response = client.get(
                "/products/product123?store_id=store123",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["item"]["name"] == "Test Product"
            assert data["data"]["item"]["id"] == "product123"

    def test_create_product_success(self, client, mock_firestore):
        """Test successful product creation."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify, \
             patch('api.common.storage.mark_image_permanent'):

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            # Mock store validation
            store_doc = MagicMock()
            store_doc.exists = True
            store_ref = MagicMock()
            store_ref.get.return_value = store_doc

            # Mock product creation
            new_product_doc = MagicMock()
            new_product_doc.to_dict.return_value = {
                "name": "New Product",
                "store_id": "store123",
                "sellingPrice": 100,
                "stockQuantity": 10,
                "status": True,
                "description": "",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "avatarUrl": None
            }

            new_product_ref = MagicMock()
            new_product_ref.id = "new_product_id"
            new_product_ref.get.return_value = new_product_doc

            def mock_collection(name):
                if name == 'stores':
                    mock_stores = MagicMock()
                    mock_stores.document.return_value = store_ref
                    return mock_stores
                elif name == 'products':
                    products_collection = MagicMock()
                    products_collection.document.return_value = new_product_ref
                    return products_collection

            mock_firestore.collection.side_effect = mock_collection

            product_data = {
                "name": "New Product",
                "sellingPrice": 100,
                "stockQuantity": 10,
                "store_id": "store123",
                "description": "",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "status": True
            }

            response = client.post(
                "/products",
                json=product_data,
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "New Product"
            assert data["data"]["store_id"] == "store123"

    def test_create_product_missing_store_id(self, client):
        """Test product creation without store_id."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user:
            mock_get_user.return_value = "user123"

            product_data = {
                "name": "New Product",
                "sellingPrice": 100,
                "stockQuantity": 10
                # Missing store_id
            }

            response = client.post(
                "/products",
                json=product_data,
                headers={"Authorization": "Bearer valid_token"}
            )

            # This should fail at the schema validation level
            assert response.status_code in [422, 200]  # Either validation error or JSend error
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "error"

    def test_update_product_success(self, client, mock_firestore):
        """Test successful product update."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify, \
             patch('api.common.storage.mark_image_permanent'):

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            # Mock existing product
            existing_product_doc = MagicMock()
            existing_product_doc.exists = True
            existing_product_doc.to_dict.return_value = {
                "name": "Old Product",
                "store_id": "store123",
                "sellingPrice": 100
            }

            # Mock updated product
            updated_product_doc = MagicMock()
            updated_product_doc.to_dict.return_value = {
                "name": "Updated Product",
                "store_id": "store123",
                "sellingPrice": 150,
                "stockQuantity": 10,
                "status": True,
                "description": "",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "avatarUrl": None
            }

            product_ref = MagicMock()
            product_ref.get.side_effect = [existing_product_doc, updated_product_doc]

            products_collection = MagicMock()
            products_collection.document.return_value = product_ref

            mock_firestore.collection.return_value = products_collection

            update_data = {
                "name": "Updated Product",
                "sellingPrice": 150
            }

            response = client.put(
                "/products/product123?store_id=store123",
                json=update_data,
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "Updated Product"
            assert data["data"]["sellingPrice"] == 150

    def test_delete_product_success(self, client, mock_firestore):
        """Test successful product deletion."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify:

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            product_doc = MagicMock()
            product_doc.exists = True
            product_doc.to_dict.return_value = {
                "name": "Product to Delete",
                "store_id": "store123"
            }

            product_ref = MagicMock()
            product_ref.get.return_value = product_doc

            products_collection = MagicMock()
            products_collection.document.return_value = product_ref

            mock_firestore.collection.return_value = products_collection

            response = client.delete(
                "/products/product123?store_id=store123",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "deleted successfully" in data["data"]["message"]

    def test_search_products_success(self, client, mock_firestore):
        """Test successful product search."""
        with patch('api.auth.dependencies.get_current_user_id') as mock_get_user, \
             patch('api.auth.dependencies.verify_store_access') as mock_verify:

            mock_get_user.return_value = "user123"
            mock_verify.return_value = {"id": "store123", "role": "ADMIN"}

            product_doc = MagicMock()
            product_doc.id = "product1"
            product_doc.to_dict.return_value = {
                "name": "Search Product",
                "store_id": "store123",
                "sellingPrice": 100,
                "stockQuantity": 10,
                "status": True,
                "description": "A searchable product",
                "note": "",
                "purchasePrice": 80,
                "discountPrice": 0,
                "avatarUrl": None
            }

            mock_where = MagicMock()
            mock_where.get.return_value = [product_doc]

            mock_collection = MagicMock()
            mock_collection.where.return_value = mock_where

            mock_firestore.collection.return_value = mock_collection

            response = client.get(
                "/products/search?store_id=store123&q=search&page=1&size=10",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["data"]["items"]) == 1
            assert data["data"]["items"][0]["name"] == "Search Product"

