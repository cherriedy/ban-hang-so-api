#!/usr/bin/env python3
"""
Test script to verify DOB validation works correctly.
"""

from api.customers.schemas import CustomerCreate, CustomerUpdate

def test_dob_validation():
    """Test DOB validation with different formats."""
    
    # Test cases
    test_cases = [
        # Valid ISO datetime format (what client sends)
        {"dob": "2025-07-01T13:39:11.410Z", "expected": "2025-07-01"},
        # Valid date format
        {"dob": "2025-07-01", "expected": "2025-07-01"},
        # None value
        {"dob": None, "expected": None},
        # Empty string
        {"dob": "", "expected": None},
        # Another ISO datetime format
        {"dob": "1990-12-25T00:00:00.000Z", "expected": "1990-12-25"},
    ]
    
    print("Testing CustomerCreate DOB validation:")
    for i, test_case in enumerate(test_cases):
        try:
            customer_data = {
                "name": "Test Customer",
                "dob": test_case["dob"]
            }
            customer = CustomerCreate(**customer_data)
            result = customer.dob
            expected = test_case["expected"]
            
            if result == expected:
                print(f"✓ Test {i+1}: PASS - Input: {test_case['dob']} → Output: {result}")
            else:
                print(f"✗ Test {i+1}: FAIL - Input: {test_case['dob']} → Expected: {expected}, Got: {result}")
                
        except Exception as e:
            print(f"✗ Test {i+1}: ERROR - Input: {test_case['dob']} → Error: {str(e)}")
    
    print("\nTesting CustomerUpdate DOB validation:")
    for i, test_case in enumerate(test_cases):
        try:
            customer_data = {
                "dob": test_case["dob"]
            }
            customer = CustomerUpdate(**customer_data)
            result = customer.dob
            expected = test_case["expected"]
            
            if result == expected:
                print(f"✓ Test {i+1}: PASS - Input: {test_case['dob']} → Output: {result}")
            else:
                print(f"✗ Test {i+1}: FAIL - Input: {test_case['dob']} → Expected: {expected}, Got: {result}")
                
        except Exception as e:
            print(f"✗ Test {i+1}: ERROR - Input: {test_case['dob']} → Error: {str(e)}")

if __name__ == "__main__":
    test_dob_validation()
