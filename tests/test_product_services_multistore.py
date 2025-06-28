"""
Unit tests for product services with multi-store support.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from api.products.services import (
    get_products,
    get_product_by_id,
    create_product,
    update_product,
    delete_product,
    search_products
)
from api.products.schemas import ProductInDB


class TestProductServices:
    """Test product services with store_id integration."""

    @pytest.mark.asyncio
    async def test_get_products_success(self, mock_firestore):
        """Test successful retrieval of products for a specific store."""
        # Mock count query
        count_result = MagicMock()
        count_result.value = 2
        mock_count_query = MagicMock()
        mock_count_query.get.return_value = [[count_result]]

        # Mock product documents
        product_doc1 = MagicMock()
        product_doc1.id = "product1"
        product_doc1.to_dict.return_value = {
            "name": "Product 1",
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

        product_doc2 = MagicMock()
        product_doc2.id = "product2"
        product_doc2.to_dict.return_value = {
            "name": "Product 2",
            "store_id": "store123",
            "sellingPrice": 200,
            "stockQuantity": 5,
            "status": True,
            "description": "",
            "note": "",
            "purchasePrice": 160,
            "discountPrice": 0,
            "avatarUrl": None
        }

        # Mock query chain
        mock_collection = MagicMock()
        mock_where = MagicMock()
        mock_order_by = MagicMock()
        mock_limit = MagicMock()

        mock_collection.where.return_value = mock_where
        mock_where.count.return_value = mock_count_query
        mock_where.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.get.return_value = [product_doc1, product_doc2]

        mock_firestore.collection.return_value = mock_collection

        result = await get_products("store123", limit=10, offset=0)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].name == "Product 1"
        assert result.items[1].name == "Product 2"
        assert result.page == 1
        assert result.size == 10

        mock_collection.where.assert_called_with('store_id', '==', 'store123')

    @pytest.mark.asyncio
    async def test_get_products_missing_store_id(self):
        """Test error when store_id is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_products("")

        assert exc_info.value.status_code == 400
        assert "Missing store ID parameter" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, mock_firestore):
        """Test successful retrieval of a product by ID."""
        product_doc = MagicMock()
        product_doc.exists = True
        product_doc.id = "product123"  # Set the id on the document object itself
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
        doc_ref.get.return_value = product_doc  # The document returned has the id property

        collection_ref = MagicMock()
        collection_ref.document.return_value = doc_ref

        mock_firestore.collection.return_value = collection_ref

        result = await get_product_by_id("product123", "store123")

        assert isinstance(result, ProductInDB)
        assert result.name == "Test Product"
        assert result.store_id == "store123"
        assert result.id == "product123"

    @pytest.mark.asyncio
    async def test_get_product_by_id_wrong_store(self, mock_firestore):
        """Test error when product belongs to different store."""
        product_doc = MagicMock()
        product_doc.exists = True
        product_doc.to_dict.return_value = {
            "name": "Test Product",
            "store_id": "store456",  # Different store
            "sellingPrice": 100
        }

        doc_ref = MagicMock()
        doc_ref.get.return_value = product_doc

        collection_ref = MagicMock()
        collection_ref.document.return_value = doc_ref

        mock_firestore.collection.return_value = collection_ref

        with pytest.raises(HTTPException) as exc_info:
            await get_product_by_id("product123", "store123")

        assert exc_info.value.status_code == 404
        assert "Product not found in the specified store" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_product_success(self, mock_firestore):
        """Test successful product creation."""
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

        products_collection = MagicMock()
        products_collection.document.return_value = new_product_ref

        def mock_collection(name):
            if name == 'stores':
                mock_stores = MagicMock()
                mock_stores.document.return_value = store_ref
                return mock_stores
            elif name == 'products':
                return products_collection

        mock_firestore.collection.side_effect = mock_collection

        product_data = {
            "name": "New Product",
            "sellingPrice": 100,
            "stockQuantity": 10
        }

        with patch('api.common.storage.mark_image_permanent'):
            result = await create_product(product_data, "store123")

        assert isinstance(result, ProductInDB)
        assert result.name == "New Product"
        assert result.store_id == "store123"
        assert result.id == "new_product_id"

        new_product_ref.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_store_not_found(self, mock_firestore):
        """Test error when store doesn't exist."""
        store_doc = MagicMock()
        store_doc.exists = False

        store_ref = MagicMock()
        store_ref.get.return_value = store_doc

        stores_collection = MagicMock()
        stores_collection.document.return_value = store_ref

        mock_firestore.collection.return_value = stores_collection

        with pytest.raises(HTTPException) as exc_info:
            await create_product({"name": "Test"}, "nonexistent_store")

        assert exc_info.value.status_code == 404
        assert "Store with ID nonexistent_store not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_product_success(self, mock_firestore):
        """Test successful product update."""
        existing_product_doc = MagicMock()
        existing_product_doc.exists = True
        existing_product_doc.to_dict.return_value = {
            "name": "Old Product",
            "store_id": "store123",
            "sellingPrice": 100
        }

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

        update_data = {"name": "Updated Product", "sellingPrice": 150}

        with patch('api.common.storage.mark_image_permanent'):
            result = await update_product("product123", update_data, "store123")

        assert isinstance(result, ProductInDB)
        assert result.name == "Updated Product"
        assert result.sellingPrice == 150
        assert result.id == "product123"

        product_ref.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_wrong_store(self, mock_firestore):
        """Test error when trying to update product from wrong store."""
        existing_product_doc = MagicMock()
        existing_product_doc.exists = True
        existing_product_doc.to_dict.return_value = {
            "name": "Product",
            "store_id": "store456",  # Different store
            "sellingPrice": 100
        }

        product_ref = MagicMock()
        product_ref.get.return_value = existing_product_doc

        products_collection = MagicMock()
        products_collection.document.return_value = product_ref

        mock_firestore.collection.return_value = products_collection

        with pytest.raises(HTTPException) as exc_info:
            await update_product("product123", {"name": "Updated"}, "store123")

        assert exc_info.value.status_code == 404
        assert "Product not found in the specified store" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_product_success(self, mock_firestore):
        """Test successful product deletion."""
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

        result = await delete_product("product123", "store123")

        assert result is True
        product_ref.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_products_success(self, mock_firestore):
        """Test successful product search within a store."""
        # Mock product documents
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

        result = await search_products("search", "store123", limit=10, offset=0)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].name == "Search Product"

        mock_collection.where.assert_called_with('store_id', '==', 'store123')

    @pytest.mark.asyncio
    async def test_search_products_empty_query_calls_get_products(self):
        """Test that empty search query calls get_products instead."""
        with patch('api.products.services.get_products') as mock_get_products:
            mock_get_products.return_value = MagicMock()

            await search_products("", "store123", limit=10, offset=0)

            mock_get_products.assert_called_once_with(
                store_id="store123",
                limit=10,
                offset=0
            )
