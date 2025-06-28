"""
Unit tests for product schemas with store_id validation.
"""
import pytest
from pydantic import ValidationError

from api.products.schemas import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductInDB,
    ProductUpsert
)


class TestProductSchemas:
    """Test product schemas with store_id field validation."""

    def test_product_base_valid_data(self):
        """Test ProductBase with valid data including store_id."""
        product_data = {
            "name": "Test Product",
            "description": "A test product",
            "barcode": "123456789",
            "note": "Test note",
            "purchasePrice": 80.0,
            "sellingPrice": 100.0,
            "discountPrice": 90.0,
            "stockQuantity": 50,
            "status": True,
            "avatarUrl": "https://example.com/image.jpg",
            "store_id": "store123"
        }
        
        product = ProductBase(**product_data)
        
        assert product.name == "Test Product"
        assert product.store_id == "store123"
        assert product.sellingPrice == 100.0
        assert product.stockQuantity == 50

    def test_product_base_missing_store_id(self):
        """Test ProductBase fails without store_id."""
        product_data = {
            "name": "Test Product",
            "sellingPrice": 100.0
            # Missing store_id
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProductBase(**product_data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("store_id",) for error in errors)

    def test_product_base_missing_required_fields(self):
        """Test ProductBase fails without required fields."""
        product_data = {
            "store_id": "store123"
            # Missing name and sellingPrice
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProductBase(**product_data)
        
        errors = exc_info.value.errors()
        field_names = [error["loc"][0] for error in errors]
        assert "name" in field_names
        assert "sellingPrice" in field_names

    def test_product_create_with_store_id(self):
        """Test ProductCreate includes store_id from ProductBase."""
        product_data = {
            "name": "New Product",
            "sellingPrice": 150.0,
            "store_id": "store456"
        }
        
        product = ProductCreate(**product_data)
        
        assert product.name == "New Product"
        assert product.store_id == "store456"
        assert product.sellingPrice == 150.0

    def test_product_update_optional_store_id(self):
        """Test ProductUpdate has optional store_id field."""
        # Test with store_id
        update_data = {
            "name": "Updated Product",
            "store_id": "store789"
        }
        
        product_update = ProductUpdate(**update_data)
        assert product_update.name == "Updated Product"
        assert product_update.store_id == "store789"
        
        # Test without store_id
        update_data_no_store = {
            "name": "Updated Product Only"
        }
        
        product_update_no_store = ProductUpdate(**update_data_no_store)
        assert product_update_no_store.name == "Updated Product Only"
        assert product_update_no_store.store_id is None

    def test_product_in_db_with_store_id(self):
        """Test ProductInDB includes store_id and id fields."""
        product_data = {
            "id": "product123",
            "name": "DB Product",
            "sellingPrice": 200.0,
            "store_id": "store123",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z"
        }
        
        product = ProductInDB(**product_data)
        
        assert product.id == "product123"
        assert product.name == "DB Product"
        assert product.store_id == "store123"
        assert product.sellingPrice == 200.0

    def test_product_upsert_optional_store_id(self):
        """Test ProductUpsert has optional store_id field."""
        # Test for create (no id, with store_id)
        create_data = {
            "name": "New Product",
            "sellingPrice": 100.0,
            "store_id": "store123"
        }
        
        product_upsert = ProductUpsert(**create_data)
        assert product_upsert.id is None
        assert product_upsert.store_id == "store123"
        
        # Test for update (with id, optional store_id)
        update_data = {
            "id": "product456",
            "name": "Updated Product",
            "sellingPrice": 150.0
        }
        
        product_upsert_update = ProductUpsert(**update_data)
        assert product_upsert_update.id == "product456"
        assert product_upsert_update.store_id is None

    def test_product_base_default_values(self):
        """Test ProductBase default values work correctly."""
        minimal_data = {
            "name": "Minimal Product",
            "sellingPrice": 50.0,
            "store_id": "store123"
        }
        
        product = ProductBase(**minimal_data)
        
        assert product.name == "Minimal Product"
        assert product.description == ""
        assert product.barcode == ""
        assert product.note == ""
        assert product.purchasePrice == 0
        assert product.discountPrice == 0
        assert product.stockQuantity == 0
        assert product.status is True
        assert product.avatarUrl is None
        assert product.store_id == "store123"

    def test_product_validation_negative_prices(self):
        """Test validation doesn't allow invalid price values."""
        # Note: You might want to add custom validators for this
        product_data = {
            "name": "Test Product",
            "sellingPrice": -100.0,  # Negative price
            "store_id": "store123"
        }
        
        # Currently this would pass, but you might want to add validation
        product = ProductBase(**product_data)
        assert product.sellingPrice == -100.0  # This passes but might not be desired

    def test_product_validation_negative_stock(self):
        """Test validation with negative stock quantity."""
        product_data = {
            "name": "Test Product",
            "sellingPrice": 100.0,
            "stockQuantity": -5,  # Negative stock
            "store_id": "store123"
        }
        
        # Currently this would pass, but you might want to add validation
        product = ProductBase(**product_data)
        assert product.stockQuantity == -5  # This passes but might not be desired
