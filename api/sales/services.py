"""
This module contains the business logic for sales-related operations.
"""

from fastapi import HTTPException
from firebase_admin import firestore

from api.sales.schemas import ProductSaleData, ProductSaleItem


def get_firestore_client():
    return firestore.client()


async def get_products_for_sale(store_id: str, limit: int = 100, offset: int = 0,
                               sort_by: str = "createdAt", sort_order: str = "desc"):
    """
    Service function to retrieve products optimized for sale endpoints with only essential fields.
    This function fetches only the necessary fields for better performance.

    Args:
        store_id: The ID of the store to retrieve products from
        limit: Maximum number of products to return
        offset: Number of products to skip
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        ProductSaleData object containing the paginated products with essential fields only

    Raises:
        HTTPException: If errors occur during retrieval
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products').where('storeId', '==', store_id)

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

            # Only extract essential fields for sale
            sale_item = ProductSaleItem(
                id=doc.id,
                name=product_data.get('name', ''),
                thumbnailUrl=product_data.get('thumbnailUrl'),
                sellingPrice=product_data.get('sellingPrice', 0),
                purchasePrice=product_data.get('purchasePrice', 0),
                discountPrice=product_data.get('discountPrice', 0),
                status=product_data.get('status', True)
            )
            product_items.append(sale_item)

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        result = ProductSaleData(
            items=product_items,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def search_products_for_sale(query: str, store_id: str, limit: int = 100, offset: int = 0):
    """
    Service function to search for products optimized for sale endpoints with only essential fields.
    This function searches products and returns only the necessary fields for better performance.

    Args:
        query: The search query
        store_id: The ID of the store to search products in
        limit: Maximum number of products to return
        offset: Number of products to skip

    Returns:
        ProductSaleData object containing the paginated search results with essential fields only

    Raises:
        HTTPException: If errors occur during search
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        # If query is empty, return all products for the store instead of searching
        if not query or query.strip() == "":
            return await get_products_for_sale(store_id=store_id, limit=limit, offset=offset)

        # Normalize query for case-insensitive search
        normalized_query = query.lower().strip()

        db = get_firestore_client()
        products_ref = db.collection('products').where('storeId', '==', store_id)

        # Dictionary to store all found products with their relevance score
        products = {}

        # Fetch all products for the store and perform client-side filtering
        # This approach allows searching for substrings anywhere in the fields
        all_products = products_ref.get()

        for doc in all_products:
            product_data = doc.to_dict()

            # Skip products that don't have required fields
            if not product_data:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check name field (highest priority)
            name = product_data.get('name', '').lower()
            if normalized_query in name:
                # Higher score for exact matches
                if name == normalized_query:
                    relevance_score += 15
                # Higher score if query is at the beginning of the name
                elif name.startswith(normalized_query):
                    relevance_score += 12
                # Standard score for substring matches
                else:
                    relevance_score += 10

            # Check barcode/SKU field (high priority)
            barcode = product_data.get('barcode', '').lower()
            if normalized_query in barcode:
                relevance_score += 8

            # Check brand name (medium priority)
            brand = product_data.get('brand', {})
            if isinstance(brand, dict) and normalized_query in brand.get('name', '').lower():
                relevance_score += 5

            # Check category name (medium-low priority)
            category = product_data.get('category', {})
            if isinstance(category, dict) and normalized_query in category.get('name', '').lower():
                relevance_score += 3

            # Check description (lowest priority)
            description = product_data.get('description', '').lower()
            if normalized_query in description:
                relevance_score += 1

            # If this product matches the query in any field, add it to the results
            if relevance_score > 0:
                # Only extract essential fields for sale
                sale_item = ProductSaleItem(
                    id=doc.id,
                    name=product_data.get('name', ''),
                    thumbnailUrl=product_data.get('thumbnailUrl'),
                    sellingPrice=product_data.get('sellingPrice', 0),
                    purchasePrice=product_data.get('purchasePrice', 0),
                    discountPrice=product_data.get('discountPrice', 0),
                    status=product_data.get('status', True)
                )
                products[doc.id] = {
                    'product': sale_item,
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

        result = ProductSaleData(
            items=paginated_results,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )
