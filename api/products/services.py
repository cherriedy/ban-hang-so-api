from fastapi import HTTPException
from firebase_admin import firestore

from api.products.schemas import ProductInDB, ProductsData


def get_firestore_client():
    return firestore.client()


async def get_products(limit: int = 100, offset: int = 0,
                       sort_by: str = "createdAt", sort_order: str = "desc") -> ProductsData:
    """
    Service function to retrieve products with pagination and sorting.

    Args:
        limit: Maximum number of products to return
        offset: Number of products to skip
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        ProductsData object containing the paginated products

    Raises:
        HTTPException: If errors occur during retrieval
    """
    try:
        db = get_firestore_client()
        products_ref = db.collection('products')

        # Count total products for pagination info
        total_query = products_ref.count()
        total = total_query.get()[0][0].value

        # Get products with pagination
        direction = "DESCENDING"
        if sort_order and sort_order.lower().startswith("asc"):
            direction = "ASCENDING"

        query = products_ref.order_by(sort_by, direction=direction)

        if offset > 0:
            query = query.offset(offset)

        query = query.limit(limit)
        products_docs = query.get()

        product_items = []
        for doc in products_docs:
            product_data = doc.to_dict()
            product_data['id'] = doc.id
            product_items.append(ProductInDB(**product_data))

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return ProductsData(
            items=product_items,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def get_product_by_id(product_id: str) -> ProductInDB:
    """
    Service function to retrieve a single product by ID.

    Args:
        product_id: The unique identifier of the product

    Returns:
        ProductInDB object containing the product data

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        doc_ref = products_ref.document(product_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product_data = doc.to_dict()
        product_data['id'] = doc.id
        return ProductInDB(**product_data)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def create_product(product_data: dict) -> ProductInDB:
    """
    Service function to create a new product.

    Args:
        product_data: The product data to create

    Returns:
        ProductInDB object containing the created product data

    Raises:
        HTTPException: If errors occur during creation
    """
    try:
        db = get_firestore_client()

        # Fetch and replace brand data if provided
        if 'brand' in product_data and product_data.get('brand'):
            brand_id = product_data['brand']['id']
            brand_ref = db.collection('brands').document(brand_id)
            brand_doc = brand_ref.get()
            if not brand_doc.exists:
                raise HTTPException(status_code=404, detail=f"Brand with ID {brand_id} not found")
            product_data['brand'] = brand_doc.to_dict()

        # Fetch and replace category data if provided
        if 'category' in product_data and product_data.get('category'):
            category_id = product_data['category']['id']
            category_ref = db.collection('categories').document(category_id)
            category_doc = category_ref.get()
            if not category_doc.exists:
                raise HTTPException(status_code=404, detail=f"Category with ID {category_id} not found")
            product_data['category'] = category_doc.to_dict()

        products_ref = db.collection('products')

        product_data['createdAt'] = firestore.firestore.SERVER_TIMESTAMP
        product_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP

        # Create new document
        new_product_ref = products_ref.document()
        new_product_ref.set(product_data)

        # Retrieve the created product to return
        created_product = new_product_ref.get().to_dict()
        created_product['id'] = new_product_ref.id

        return ProductInDB(**created_product)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def search_products(query: str, limit: int = 100, offset: int = 0) -> ProductsData:
    """
    Service function to search for products by name, brand, category, description or SKU with pagination.

    Args:
        query: The search query
        limit: Maximum number of products to return
        offset: Number of products to skip

    Returns:
        ProductsData object containing the paginated search results

    Raises:
        HTTPException: If errors occur during search
    """
    try:
        db = get_firestore_client()
        products_ref = db.collection('products')

        # If query is empty, return all products instead of searching
        if not query or query.strip() == "":
            return await get_products(limit=limit, offset=offset)

        query = query.lower().strip()  # Normalize query for case-insensitive search

        # Dictionary to store all found products with their relevance score
        products = {}

        # Fetch all products and perform client-side filtering
        # This approach allows searching for substrings anywhere in the fields
        all_products = products_ref.get()

        for doc in all_products:
            product_data = doc.to_dict()
            product_data['id'] = doc.id

            # Skip products that don't have required fields
            if not product_data:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check name field (highest priority)
            name = product_data.get('name', '').lower()
            if query in name:
                # Higher score for exact matches
                if name == query:
                    relevance_score += 15
                # Higher score if query is at the beginning of the name
                elif name.startswith(query):
                    relevance_score += 12
                # Standard score for substring matches
                else:
                    relevance_score += 10

            # Check SKU field (high priority)
            sku = product_data.get('sku', '').lower()
            if query in sku:
                relevance_score += 8

            # Check brand name (medium priority)
            brand = product_data.get('brand', {})
            if isinstance(brand, dict) and query in brand.get('name', '').lower():
                relevance_score += 5

            # Check category name (medium-low priority)
            category = product_data.get('category', {})
            if isinstance(category, dict) and query in category.get('name', '').lower():
                relevance_score += 3

            # Check description (lowest priority)
            description = product_data.get('description', '').lower()
            if query in description:
                relevance_score += 1

            # If this product matches the query in any field, add it to the results
            if relevance_score > 0:
                products[doc.id] = {
                    'product': ProductInDB(**product_data),
                    'relevance': relevance_score
                }

        # Sort results by relevance score (highest first)
        sorted_products = sorted(
            list(products.values()),
            key=lambda item: item['relevance'],
            reverse=True
        )

        # Extract just the product objects for the response
        all_results = [item['product'] for item in sorted_products]

        total = len(all_results)

        # Apply pagination
        paginated_results = all_results[offset:offset + limit]

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return ProductsData(
            items=paginated_results,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def update_product(product_id: str, product_data: dict) -> ProductInDB:
    """
    Service function to update an existing product.

    Args:
        product_id: The unique identifier of the product to update
        product_data: The product data to update

    Returns:
        ProductInDB object containing the updated product data

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        product_ref = products_ref.document(product_id)
        product = product_ref.get()

        if not product.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        update_data = product_data.copy()

        # Fetch and replace brand data if provided
        if 'brand' in update_data:
            if update_data.get('brand'):
                brand_id = update_data['brand']['id']
                brand_ref = db.collection('brands').document(brand_id)
                brand_doc = brand_ref.get()
                if not brand_doc.exists:
                    raise HTTPException(status_code=404, detail=f"Brand with ID {brand_id} not found")
                update_data['brand'] = brand_doc.to_dict()
            else:  # handle case where brand is set to null
                update_data['brand'] = None

        # Fetch and replace category data if provided
        if 'category' in update_data:
            if update_data.get('category'):
                category_id = update_data['category']['id']
                category_ref = db.collection('categories').document(category_id)
                category_doc = category_ref.get()
                if not category_doc.exists:
                    raise HTTPException(status_code=404, detail=f"Category with ID {category_id} not found")
                update_data['category'] = category_doc.to_dict()
            else:  # handle case where category is set to null
                update_data['category_name_lower'] = None

        # Update only provided fields
        update_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP
        product_ref.update(update_data)

        # Return updated product
        updated_product_dict = product_ref.get().to_dict()
        if updated_product_dict is None:
            # This can happen if the mock is not set up correctly for the second get
            raise HTTPException(status_code=500, detail="Failed to retrieve updated product")

        updated_product_dict['id'] = product_id
        return ProductInDB(**updated_product_dict)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def delete_product(product_id: str) -> bool:
    """
    Service function to delete a product by ID.

    Args:
        product_id: The unique identifier of the product to delete

    Returns:
        bool: True if the product was deleted successfully

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        product_ref = products_ref.document(product_id)
        product = product_ref.get()

        if not product.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product_ref.delete()
        return True

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,

            detail=f"Internal server error: {str(exc)}"
        )
