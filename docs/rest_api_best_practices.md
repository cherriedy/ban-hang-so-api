# REST API Best Practices for Ban Hang So API

This document outlines the best practices for designing and implementing REST APIs in this project. Following these guidelines will ensure consistency and maintainability across the codebase.

## Table of Contents

1. [Project Structure](#project-structure)
2. [URL Structure](#url-structure)
3. [HTTP Methods](#http-methods)
4. [Request & Response Format](#request--response-format)
5. [Status Codes](#status-codes)
6. [Authentication & Authorization](#authentication--authorization)
7. [Versioning](#versioning)
8. [Pagination](#pagination)
9. [Filtering, Sorting & Searching](#filtering-sorting--searching)
10. [Error Handling](#error-handling)
11. [Documentation](#documentation)
12. [Testing](#testing)

## Project Structure

The API follows a modular structure with the following components:

```
api/
  ├── module_name/
  │   ├── routers.py    # API endpoints and route definitions
  │   ├── schemas.py    # Pydantic models for request/response validation
  │   └── services.py   # Business logic and data access methods
  └── common/
      └── schemas.py    # Common schemas shared across modules
```

Each module should represent a logical business domain (e.g., products, stores, auth).

## URL Structure

Follow these practices for URL structure:

- Use kebab-case for URLs
- Use plural nouns for resource collections
- Nest resources to indicate relationships
- Keep URLs simple and intuitive

Examples:
```
/api/products                   # Get all products
/api/products/{id}              # Get a specific product
/api/stores/{store_id}/products # Get products for a specific store
```

## HTTP Methods

Use standard HTTP methods appropriately:

| Method | Usage |
|--------|-------|
| GET    | Retrieve resource(s) without side effects |
| POST   | Create a new resource |
| PUT    | Replace a resource completely |
| PATCH  | Update a resource partially |
| DELETE | Remove a resource |

## Request & Response Format

### Schema Design

1. Use the common pattern established in the project:
   - Base models for common fields
   - Create/Update models for input validation
   - Response models using JSendResponse format

2. Follow the schema inheritance pattern:

```python
# Base model with common fields
class ResourceBase(BaseModel):
    """Base model docstring"""
    name: str
    # other required fields

# Create model (inherits from base)
class ResourceCreate(ResourceBase):
    """Create model docstring"""
    # additional fields for creation

# Update model (all fields optional)
class ResourceUpdate(BaseModel):
    """Update model docstring"""
    name: Optional[str] = None
    # other optional fields

# Database model (inherits from base + timestamps)
class ResourceInDB(ResourceBase, TimestampMixin):
    """DB model docstring"""
    id: str
    # other DB-specific fields

# Response models using JSend format
class ResourceResponse(JSendResponse):
    """Response model docstring"""
    data: Optional[ResourceInDB] = None
```

### JSend Response Format

All API responses should follow the JSend specification:

```json
{
  "status": "success|fail|error",
  "data": { /* response data object */ },
  "message": "Optional message (primarily for errors)",
  "code": 400 // Optional error code
}
```

## Status Codes

Use appropriate HTTP status codes:

| Code | Description |
|------|-------------|
| 200  | OK - Request succeeded |
| 201  | Created - Resource created successfully |
| 204  | No Content - Request succeeded with no response body |
| 400  | Bad Request - Invalid input |
| 401  | Unauthorized - Authentication required |
| 403  | Forbidden - Authenticated but not authorized |
| 404  | Not Found - Resource not found |
| 422  | Unprocessable Entity - Validation error |
| 500  | Internal Server Error - Server-side issue |

## Authentication & Authorization

1. Use JWT tokens for authentication
2. Include role-based access control
3. Store user role information in the JWT token
4. Validate permissions at the router level

Example:
```python
@router.get("/products/{id}", response_model=ProductResponse)
async def get_product(
    id: str, 
    current_user: User = Depends(get_current_user)
):
    # Authorization check
    if not current_user.can_access_product(id):
        raise HTTPException(status_code=403, detail="Not authorized")
    # Implementation
```

## Versioning

Use URL-based versioning for major API changes:

```
/api/v1/products
/api/v2/products
```

## Pagination

Implement pagination for collection endpoints:

1. Use limit/offset or page/size query parameters:
   ```
   /api/products?limit=20&offset=40
   /api/products?page=3&size=20
   ```

2. Include pagination metadata in responses:
   ```json
   {
     "status": "success",
     "data": {
       "items": [...],
       "total": 142,
       "page": 3,
       "size": 20,
       "pages": 8
     }
   }
   ```

## Filtering, Sorting & Searching

1. Use query parameters for filtering:
   ```
   /api/products?status=active
   /api/products?category=electronics
   ```

2. Support sorting with sort/order parameters:
   ```
   /api/products?sort=price&order=desc
   ```

3. Implement search functionality:
   ```
   /api/products?search=keyword
   ```

## Error Handling

1. Use consistent error response format:
   ```json
   {
     "status": "error",
     "message": "Detailed error message",
     "code": 400
   }
   ```

2. Centralize error handling with middleware/exception handlers

3. Log errors with appropriate severity levels

## Documentation

1. Use descriptive docstrings for all schemas and endpoint functions
2. Implement OpenAPI documentation (Swagger UI) at `/docs`
3. Include example request/response models

Example docstring:
```python
"""
Get a product by ID

Returns detailed information about a specific product.
Requires authentication and appropriate permissions.

Parameters:
    id (str): The unique product identifier

Returns:
    ProductResponse: The product data in JSend format
    
Raises:
    404: If product not found
    403: If not authorized to view the product
"""
```

## Testing

1. Write comprehensive tests for each endpoint
2. Test happy paths and error scenarios
3. Verify status codes, response format, and data integrity
4. Use dependency injection to mock services for unit testing

Example test:
```python
async def test_get_product():
    # Setup test data
    test_product = {"id": "123", "name": "Test Product"}
    # Mock service response
    service_mock.get_product.return_value = test_product
    # Make request
    response = await client.get("/api/products/123")
    # Assertions
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["name"] == "Test Product"
```

## Implementation Example

Here's a complete example of how to implement a resource:

### 1. Define schemas (schemas.py):

```python
from typing import Optional
from pydantic import BaseModel
from api.common.schemas import TimestampMixin, JSendResponse

class ResourceBase(BaseModel):
    """Base resource model with required fields"""
    name: str
    description: str = ""

class ResourceCreate(ResourceBase):
    """Request model for creating a resource"""
    pass

class ResourceUpdate(BaseModel):
    """Request model for updating a resource"""
    name: Optional[str] = None
    description: Optional[str] = None

class ResourceInDB(ResourceBase, TimestampMixin):
    """Database model for the resource"""
    id: str

class ResourceResponse(JSendResponse):
    """Response model with JSend format"""
    data: Optional[ResourceInDB] = None
```

### 2. Implement services (services.py):

```python
async def get_resource(id: str) -> dict:
    """Get resource by ID from database"""
    # Implementation
    pass

async def create_resource(data: dict) -> str:
    """Create a new resource"""
    # Implementation
    pass

async def update_resource(id: str, data: dict) -> bool:
    """Update existing resource"""
    # Implementation
    pass
```

### 3. Define routes (routers.py):

```python
from fastapi import APIRouter, Depends, HTTPException
from .schemas import ResourceCreate, ResourceUpdate, ResourceResponse
from .services import get_resource, create_resource, update_resource
from ..auth.services import get_current_user

router = APIRouter(prefix="/resources", tags=["resources"])

@router.get("/{id}", response_model=ResourceResponse)
async def get_resource_endpoint(id: str, current_user = Depends(get_current_user)):
    resource = await get_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {
        "status": "success",
        "data": resource
    }

@router.post("/", response_model=ResourceResponse)
async def create_resource_endpoint(
    resource: ResourceCreate, 
    current_user = Depends(get_current_user)
):
    resource_id = await create_resource(resource.dict())
    new_resource = await get_resource(resource_id)
    return {
        "status": "success",
        "data": new_resource
    }
```

By following these best practices, you'll maintain consistency across the API and provide a great developer experience for API consumers.
