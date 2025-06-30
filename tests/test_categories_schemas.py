"""
Unit tests for categories schemas.
Tests the Pydantic models used for category data validation and serialization.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from api.categories.schemas import (
    CategoryBase, CategoryCreate, CategoryUpdate, CategoryInDB,
    CategoryDetailData, CategoriesData, CategoryResponse, CategoriesResponse
)


class TestCategoryBase:
    """Test the CategoryBase schema."""

    def test_valid_category_base(self):
        """Test creating a valid CategoryBase."""
        data = {
            "name": "Electronics",
            "storeId": "store123"
        }
        category = CategoryBase(**data)
        assert category.name == "Electronics"
        assert category.storeId == "store123"

    def test_category_base_missing_name(self):
        """Test CategoryBase validation fails when name is missing."""
        data = {"storeId": "store123"}
        with pytest.raises(ValidationError) as exc_info:
            CategoryBase(**data)
        assert "name" in str(exc_info.value)

    def test_category_base_missing_store_id(self):
        """Test CategoryBase validation fails when storeId is missing."""
        data = {"name": "Electronics"}
        with pytest.raises(ValidationError) as exc_info:
            CategoryBase(**data)
        assert "storeId" in str(exc_info.value)

    def test_category_base_empty_name(self):
        """Test CategoryBase validation fails when name is empty."""
        data = {
            "name": "",
            "storeId": "store123"
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryBase(**data)
        assert "at least 1 character" in str(exc_info.value)

    def test_category_base_long_name(self):
        """Test CategoryBase validation fails when name is too long."""
        data = {
            "name": "A" * 101,  # 101 characters, should fail max_length=100
            "storeId": "store123"
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryBase(**data)
        assert "at most 100 characters" in str(exc_info.value)

    def test_category_base_valid_edge_cases(self):
        """Test CategoryBase with edge cases that should be valid."""
        # Exactly 100 characters
        data = {
            "name": "A" * 100,
            "storeId": "store123"
        }
        category = CategoryBase(**data)
        assert len(category.name) == 100
        assert category.storeId == "store123"

        # Single character name
        data = {
            "name": "A",
            "storeId": "store123"
        }
        category = CategoryBase(**data)
        assert category.name == "A"


class TestCategoryCreate:
    """Test the CategoryCreate schema."""

    def test_valid_category_create(self):
        """Test creating a valid CategoryCreate."""
        data = {
            "name": "Sports Equipment",
            "storeId": "store456"
        }
        category = CategoryCreate(**data)
        assert category.name == "Sports Equipment"
        assert category.storeId == "store456"

    def test_category_create_inherits_validation(self):
        """Test that CategoryCreate inherits validation from CategoryBase."""
        data = {"name": "Valid Name"}  # Missing storeId
        with pytest.raises(ValidationError):
            CategoryCreate(**data)


class TestCategoryUpdate:
    """Test the CategoryUpdate schema."""

    def test_valid_category_update(self):
        """Test creating a valid CategoryUpdate."""
        data = {"name": "Updated Electronics"}
        category = CategoryUpdate(**data)
        assert category.name == "Updated Electronics"

    def test_category_update_all_optional(self):
        """Test that all fields in CategoryUpdate are optional."""
        category = CategoryUpdate()
        assert category.name is None

    def test_category_update_name_validation(self):
        """Test that name validation still applies in CategoryUpdate."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            CategoryUpdate(name="")

        # Too long name should fail
        with pytest.raises(ValidationError):
            CategoryUpdate(name="A" * 101)

    def test_category_update_partial(self):
        """Test CategoryUpdate with only name provided."""
        data = {"name": "New Category Name"}
        category = CategoryUpdate(**data)
        assert category.name == "New Category Name"


class TestCategoryInDB:
    """Test the CategoryInDB schema."""

    def test_valid_category_in_db(self):
        """Test creating a valid CategoryInDB."""
        data = {
            "id": "cat123",
            "name": "Books",
            "storeId": "store789",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }
        category = CategoryInDB(**data)
        assert category.id == "cat123"
        assert category.name == "Books"
        assert category.storeId == "store789"
        assert category.createdAt is not None
        assert category.updatedAt is not None

    def test_category_in_db_missing_id(self):
        """Test CategoryInDB validation fails when id is missing."""
        data = {
            "name": "Books",
            "storeId": "store789",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryInDB(**data)
        assert "id" in str(exc_info.value)

    def test_category_in_db_with_timestamps(self):
        """Test CategoryInDB with proper timestamp handling."""
        now = datetime.now()
        data = {
            "id": "cat456",
            "name": "Furniture",
            "storeId": "store123",
            "createdAt": now,
            "updatedAt": now
        }
        category = CategoryInDB(**data)
        assert category.createdAt == now
        assert category.updatedAt == now


class TestCategoryDetailData:
    """Test the CategoryDetailData schema."""

    def test_valid_category_detail_data(self):
        """Test creating a valid CategoryDetailData."""
        category_in_db = CategoryInDB(
            id="cat123",
            name="Electronics",
            storeId="store456",
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )
        detail = CategoryDetailData(item=category_in_db)
        assert detail.item.id == "cat123"
        assert detail.item.name == "Electronics"

    def test_category_detail_data_missing_item(self):
        """Test CategoryDetailData validation fails when item is missing."""
        with pytest.raises(ValidationError):
            CategoryDetailData()


class TestCategoriesData:
    """Test the CategoriesData schema (pagination response)."""

    def test_valid_categories_data(self):
        """Test creating a valid CategoriesData."""
        categories = [
            CategoryInDB(
                id=f"cat{i}",
                name=f"Category {i}",
                storeId="store123",
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
            for i in range(3)
        ]
        
        data = CategoriesData(
            items=categories,
            total=10,
            page=1,
            size=3,
            pages=4
        )
        
        assert len(data.items) == 3
        assert data.total == 10
        assert data.page == 1
        assert data.size == 3
        assert data.pages == 4

    def test_categories_data_empty_list(self):
        """Test CategoriesData with empty items list."""
        data = CategoriesData(
            items=[],
            total=0,
            page=1,
            size=10,
            pages=0
        )
        assert len(data.items) == 0
        assert data.total == 0


class TestCategoryResponse:
    """Test the CategoryResponse schema."""

    def test_valid_category_response(self):
        """Test creating a valid CategoryResponse."""
        category = CategoryInDB(
            id="cat123",
            name="Electronics",
            storeId="store456",
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )
        response = CategoryResponse(
            status="success",
            data=category
        )
        assert response.status == "success"
        assert response.data.id == "cat123"

    def test_category_response_no_data(self):
        """Test CategoryResponse with no data."""
        response = CategoryResponse(status="success")
        assert response.status == "success"
        assert response.data is None


class TestCategoriesResponse:
    """Test the CategoriesResponse schema."""

    def test_valid_categories_response(self):
        """Test creating a valid CategoriesResponse."""
        categories = [
            CategoryInDB(
                id="cat1",
                name="Category 1",
                storeId="store123",
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
        ]
        
        categories_data = CategoriesData(
            items=categories,
            total=1,
            page=1,
            size=10,
            pages=1
        )
        
        response = CategoriesResponse(
            status="success",
            data=categories_data
        )
        
        assert response.status == "success"
        assert len(response.data.items) == 1
        assert response.data.total == 1
