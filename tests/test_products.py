"""
Tests for products endpoints.
"""
from unittest.mock import MagicMock


def test_list_products_success(client, mock_firestore):
    """Test successful products listing."""
    # Mock the products collection and query results
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection

    # Mock query builder methods
    mock_query = MagicMock()
    mock_products_collection.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query

    # Create mock documents
    mock_doc1 = MagicMock()
    mock_doc1.id = "product1"
    mock_doc1.to_dict.return_value = {
        "name": "Product 1",
        "sellingPrice": 19.99,
        "description": "Test product 1",
        "createdAt": "2025-06-01T10:00:00Z",
        "updatedAt": "2025-06-01T10:00:00Z",
        "barcode": "123"
    }

    mock_doc2 = MagicMock()
    mock_doc2.id = "product2"
    mock_doc2.to_dict.return_value = {
        "name": "Product 2",
        "sellingPrice": 29.99,
        "description": "Test product 2",
        "createdAt": "2025-06-02T10:00:00Z",
        "updatedAt": "2025-06-02T10:00:00Z",
        "barcode": "456"
    }

    # Configure mock query results
    mock_query.get.return_value = [mock_doc1, mock_doc2]

    # Mock the count query for total items
    mock_count_query = MagicMock()
    mock_products_collection.count.return_value = mock_count_query
    mock_aggregation_result = MagicMock()
    mock_aggregation_result.value = 2
    mock_count_query.get.return_value = [[mock_aggregation_result]]

    # Make request with pagination and sorting params
    response = client.get("/products?page=1&size=10&sort_by=createdAt&sort_order=desc")

    # Assert response
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    assert len(response_json["data"]["items"]) == 2
    assert response_json["data"]["total"] == 2
    assert response_json["data"]["page"] == 1
    assert response_json["data"]["size"] == 10
    assert response_json["data"]["pages"] == 1
    assert response_json["data"]["items"][0]["id"] == "product1"
    assert response_json["data"]["items"][1]["id"] == "product2"


def test_get_product_by_id_success(client, mock_firestore):
    """Test getting a product by ID."""
    # Product ID to test
    product_id = "test_product_id"

    # Mock the Firestore document snapshot
    mock_product_doc = MagicMock()
    mock_product_doc.exists = True
    mock_product_doc.id = product_id
    mock_product_doc.to_dict.return_value = {
        "name": "Test Product",
        "sellingPrice": 24.99,
        "description": "A test product",
        "createdAt": "2025-06-10T15:30:00Z",
        "updatedAt": "2025-06-10T15:30:00Z",
        "barcode": "123"
    }

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection
    mock_products_collection.document.return_value.get.return_value = mock_product_doc

    # Make the request
    response = client.get(f"/products/{product_id}")

    # Assert response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["id"] == product_id
    assert response.json()["data"]["name"] == "Test Product"
    assert response.json()["data"]["sellingPrice"] == 24.99


def test_get_product_not_found(client, mock_firestore):
    """Test getting a non-existent product."""
    # Product ID to test
    product_id = "nonexistent_product"

    # Mock the Firestore document snapshot for non-existent product
    mock_product_doc = MagicMock()
    mock_product_doc.exists = False

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection
    mock_products_collection.document.return_value.get.return_value = mock_product_doc

    # Make the request
    response = client.get(f"/products/{product_id}")

    # Assert response
    assert response.status_code == 200  # JSendResponse always returns 200
    assert response.json()["status"] == "error"
    assert "Product not found" in response.json()["message"]


def test_create_product_success(client, mock_firestore):
    """Test successful product creation."""
    # Test product data
    product_data = {
        "name": "New Product",
        "sellingPrice": 39.99,
        "description": "A new test product"
    }

    # Mock document reference
    mock_product_ref = MagicMock()
    mock_product_ref.id = "new_product_id"

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection

    # Mock the document creation
    mock_new_doc_ref = MagicMock()
    mock_new_doc_ref.id = "new_product_id"
    mock_products_collection.document.return_value = mock_new_doc_ref

    # Mock the get call after creation
    created_doc_snapshot = MagicMock()
    created_doc_snapshot.exists = True
    created_doc_snapshot.id = "new_product_id"
    created_doc_snapshot.to_dict.return_value = {
        "name": "New Product",
        "sellingPrice": 39.99,
        "description": "A new test product",
        "createdAt": "2025-06-18T10:00:00Z",
        "updatedAt": "2025-06-18T10:00:00Z",
        "barcode": ""
    }
    mock_new_doc_ref.get.return_value = created_doc_snapshot

    # Make the request
    response = client.post("/products", json=product_data)

    # Assert response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["id"] == "new_product_id"
    assert response.json()["data"]["name"] == "New Product"
    assert response.json()["data"]["sellingPrice"] == 39.99


def test_update_product_success(client, mock_firestore):
    """Test successful product update."""
    # Product ID to update
    product_id = "test_product_id"

    # Update data
    update_data = {
        "name": "Updated Product Name",
        "sellingPrice": 49.99
    }

    # Mock document reference and snapshot
    mock_product_doc = MagicMock()
    mock_product_doc.exists = True
    mock_product_doc.id = product_id
    mock_product_doc.to_dict.return_value = {
        "name": "Original Product Name",
        "sellingPrice": 24.99,
        "description": "A test product",
        "createdAt": "2025-06-10T15:30:00Z",
        "updatedAt": "2025-06-10T15:30:00Z",
        "barcode": "123"
    }

    # Updated product doc
    mock_updated_doc = MagicMock()
    mock_updated_doc.exists = True
    mock_updated_doc.id = product_id
    mock_updated_doc.to_dict.return_value = {
        "name": "Updated Product Name",
        "sellingPrice": 49.99,
        "description": "A test product",
        "createdAt": "2025-06-10T15:30:00Z",
        "updatedAt": "2025-06-18T10:00:00Z",
        "barcode": "123"
    }

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection

    # Setup mock for the get and update operations
    mock_doc_ref = MagicMock()
    mock_products_collection.document.return_value = mock_doc_ref

    # First get returns original, second get returns updated
    mock_doc_ref.get.side_effect = [mock_product_doc, mock_updated_doc]

    # Make the request
    response = client.put(f"/products/{product_id}", json=update_data)

    # Assert response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["id"] == product_id
    assert response.json()["data"]["name"] == "Updated Product Name"
    assert response.json()["data"]["sellingPrice"] == 49.99
    assert response.json()["data"]["description"] == "A test product"  # Unchanged field


def test_update_product_not_found(client, mock_firestore):
    """Test updating a non-existent product."""
    # Product ID to update
    product_id = "nonexistent_product"

    # Update data
    update_data = {
        "name": "Updated Product Name",
        "sellingPrice": 49.99
    }

    # Mock document snapshot for non-existent product
    mock_product_doc = MagicMock()
    mock_product_doc.exists = False

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection
    mock_products_collection.document.return_value.get.return_value = mock_product_doc

    # Make the request
    response = client.put(f"/products/{product_id}", json=update_data)

    # Assert response
    assert response.status_code == 200  # JSendResponse always returns 200
    assert response.json()["status"] == "error"
    assert "Product not found" in response.json()["message"]


def test_delete_product_success(client, mock_firestore):
    """Test successful product deletion."""
    # Product ID to delete
    product_id = "test_product_id"

    # Mock document snapshot - product exists
    mock_product_doc = MagicMock()
    mock_product_doc.exists = True

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection
    mock_doc_ref = mock_products_collection.document.return_value
    mock_doc_ref.get.return_value = mock_product_doc

    # Make the request
    response = client.delete(f"/products/{product_id}")

    # Assert response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"] is True

    # Verify delete was called
    mock_doc_ref.delete.assert_called_once()


def test_delete_product_not_found(client, mock_firestore):
    """Test deleting a non-existent product."""
    # Product ID to delete
    product_id = "nonexistent_product"

    # Mock document snapshot for non-existent product
    mock_product_doc = MagicMock()
    mock_product_doc.exists = False

    # Configure the firestore mock
    mock_products_collection = MagicMock()
    mock_firestore.collection.return_value = mock_products_collection
    mock_products_collection.document.return_value.get.return_value = mock_product_doc

    # Make the request
    response = client.delete(f"/products/{product_id}")

    # Assert response
    assert response.status_code == 200  # JSendResponse always returns 200
    assert response.json()["status"] == "error"
    assert "Product not found" in response.json()["message"]
