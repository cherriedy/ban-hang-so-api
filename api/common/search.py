"""
Module with optimized search functionality for products.
"""
from typing import List, Dict, Any, Tuple, Optional


def search_products_optimized(
    products: List[Dict[str, Any]], 
    query: str, 
    fields: List[Tuple[str, int]] = None
) -> List[Tuple[Dict[str, Any], int]]:
    """
    Optimized in-memory search for products using pre-tokenization and indexing.
    
    Args:
        products: List of product dictionaries to search through
        query: Search query string
        fields: List of (field_path, relevance_score) tuples to search in
                Default fields searched: name(10), barcode(8), brand.name(5),
                category.name(3), description(1)
    
    Returns:
        List of (product, relevance_score) tuples sorted by relevance
    """
    # Default field weights if not provided
    if fields is None:
        fields = [
            ("name", 10),         # Highest priority
            ("barcode", 8),       # High priority
            ("brand.name", 5),    # Medium priority
            ("category.name", 3), # Medium-low priority
            ("description", 1)    # Lowest priority
        ]
    
    # Normalize query for case-insensitive search
    query = query.lower().strip()
    
    # Tokenize query into words for more flexible matching
    query_tokens = set(query.split())
    
    # Add the full query as a token for exact matching
    query_tokens.add(query)
    
    # Dictionary to store results with their relevance scores
    results = {}
    
    for product in products:
        # Skip invalid products
        if not product:
            continue
        
        # Initialize relevance score
        relevance_score = 0
        
        # Check each field
        for field_path, base_weight in fields:
            # Handle nested fields like "brand.name"
            field_parts = field_path.split('.')
            value = product
            
            # Navigate through nested dictionary structure
            for part in field_parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            
            # Skip if field not found or not a string
            if not value or not isinstance(value, str):
                continue
                
            # Convert to lowercase for case-insensitive matching
            field_value = value.lower()
            
            # Calculate score for exact match
            if query == field_value:
                relevance_score += base_weight * 1.5
            
            # Calculate score for prefix match (starts with query)
            elif field_value.startswith(query):
                relevance_score += base_weight * 1.2
                
            # Calculate score for contains match
            elif query in field_value:
                relevance_score += base_weight * 1.0
            
            # Calculate token-based scoring (match individual words)
            # This helps with partial word matches and different word order
            field_tokens = set(field_value.split())
            for token in query_tokens:
                # Give points for each token that matches or is contained in field tokens
                for field_token in field_tokens:
                    if token == field_token:
                        relevance_score += base_weight * 0.5
                    elif token in field_token:
                        relevance_score += base_weight * 0.3
        
        # Add to results if has any relevance
        if relevance_score > 0:
            product_id = product.get('id')
            if product_id:
                results[product_id] = (product, relevance_score)
    
    # Sort by relevance (highest first)
    sorted_results = sorted(
        results.values(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return sorted_results
