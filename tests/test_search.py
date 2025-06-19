import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from api.products.services import search_products
from api.products.schemas import ProductsData

client = TestClient(app)


def test_search_endpoint(mock_firestore):
    """Test that the search API endpoint returns results correctly"""
    # Create mock search response
    mock_product1 = {
        "id": "product1",
        "name": "Blue T-Shirt",
        "description": "A comfortable blue t-shirt",
        "price": 19.99,
        "sku": "BTS001",
        "brand": {"id": "brand1", "name": "Fashion Brand"},
        "category": {"id": "cat1", "name": "T-Shirts"},
        "sellingPrice": 19.99,
        "purchasePrice": 10.00,
        "discountPrice": 0,
        "stockQuantity": 100,
        "status": True,
        "barcode": "123456789",
        "note": "",
        "avatarUrl": "https://example.com/shirt.jpg"
    }

    mock_product2 = {
        "id": "product2",
        "name": "Red Hoodie",
        "description": "A warm red hoodie with t-shirt material inside",
        "price": 39.99,
        "sku": "RH002",
        "brand": {"id": "brand1", "name": "Fashion Brand"},
        "category": {"id": "cat2", "name": "Hoodies"},
        "sellingPrice": 39.99,
        "purchasePrice": 20.00,
        "discountPrice": 0,
        "stockQuantity": 50,
        "status": True,
        "barcode": "987654321",
        "note": "",
        "avatarUrl": "https://example.com/hoodie.jpg"
    }

    # Mock the search_products service function using standard patch instead of mocker
    with patch("api.products.routers.search_products_service") as mock_search:
        # Configure mock response
        mock_response = ProductsData(
            items=[mock_product1, mock_product2],
            total=2,
            page=1,
            size=10,
            pages=1
        )
        mock_search.return_value = mock_response

        # Call the endpoint with the correct path
        response = client.get("/products/search?q=shirt")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["items"]) == 2
        assert data["data"]["total"] == 2

        # Verify the content of the returned items
        assert any(item["name"] == "Blue T-Shirt" for item in data["data"]["items"])
        assert any(item["description"] == "A warm red hoodie with t-shirt material inside" for item in data["data"]["items"])


@pytest.mark.asyncio
async def test_search_products_function():
    """Test the actual search_products function implementation with mocked Firestore"""
    # Mock product data that would be in Firestore
    mock_products = [
        {
            "id": "product1",
            "name": "Blue T-Shirt",
            "description": "A comfortable blue t-shirt",
            "price": 19.99,
            "sku": "BTS001",
            "brand": {"id": "brand1", "name": "Fashion Brand"},
            "category": {"id": "cat1", "name": "T-Shirts"},
            "sellingPrice": 19.99,
            "purchasePrice": 10.00,
            "discountPrice": 0,
            "stockQuantity": 100,
            "status": True,
            "barcode": "123456789",
            "note": "",
            "avatarUrl": "https://example.com/shirt.jpg"
        },
        {
            "id": "product2",
            "name": "Red Hoodie",
            "description": "A warm red hoodie with t-shirt material inside",
            "price": 39.99,
            "sku": "RH002",
            "brand": {"id": "brand1", "name": "Fashion Brand"},
            "category": {"id": "cat2", "name": "Hoodies"},
            "sellingPrice": 39.99,
            "purchasePrice": 20.00,
            "discountPrice": 0,
            "stockQuantity": 50,
            "status": True,
            "barcode": "987654321",
            "note": "",
            "avatarUrl": "https://example.com/hoodie.jpg"
        },
        {
            "id": "product3",
            "name": "Black Pants",
            "description": "Formal black pants",
            "price": 49.99,
            "sku": "BP003",
            "brand": {"id": "brand2", "name": "Formal Wear"},
            "category": {"id": "cat3", "name": "Pants"},
            "sellingPrice": 49.99,
            "purchasePrice": 25.00,
            "discountPrice": 0,
            "stockQuantity": 75,
            "status": True,
            "barcode": "567891234",
            "note": "",
            "avatarUrl": "https://example.com/pants.jpg"
        }
    ]

    # Create mock documents that mimic Firestore documents
    class MockDoc:
        def __init__(self, doc_id, doc_data):
            self.id = doc_id
            self._data = doc_data

        def to_dict(self):
            return self._data.copy()

    mock_docs = [MockDoc(p["id"], {k: v for k, v in p.items() if k != "id"}) for p in mock_products]

    # Mock the get_firestore_client function to use our test data
    with patch("api.products.services.get_firestore_client") as mock_client:
        mock_collection = MagicMock()
        mock_client.return_value.collection.return_value = mock_collection
        mock_collection.get.return_value = mock_docs

        # Test 1: Search for "shirt" should find both T-Shirt in name and hoodie in description
        results = await search_products("shirt")
        assert results.total == 2
        assert any(p.name == "Blue T-Shirt" for p in results.items), "Should find 'Blue T-Shirt'"
        assert any("t-shirt material" in p.description.lower() for p in results.items), "Should find shirt in description"

        # Test 2: Search for "blue" should find only Blue T-Shirt
        results = await search_products("blue")
        assert results.total == 1
        assert results.items[0].name == "Blue T-Shirt"

        # Test 3: Search for "formal" should find Black Pants (from brand name)
        results = await search_products("formal")
        assert results.total == 1
        assert results.items[0].name == "Black Pants"

        # Test 4: Empty search should return all products
        # For empty search, we need to mock the get_products function since it's called
        with patch("api.products.services.get_products") as mock_get_all:
            mock_get_all.return_value = ProductsData(
                items=mock_products,
                total=3,
                page=1,
                size=10,
                pages=1
            )
            results = await search_products("")
            assert mock_get_all.called
            assert results.total == 3
