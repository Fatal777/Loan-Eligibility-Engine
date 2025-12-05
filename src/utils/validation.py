"""
Validation utility functions
"""

import re
from typing import Dict, List, Optional, Tuple


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_credit_score(score: int) -> Tuple[bool, str]:
    """
    Validate credit score.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(score, (int, float)):
        return False, "Credit score must be a number"
    
    score = int(score)
    if score < 300:
        return False, "Credit score too low (minimum 300)"
    if score > 900:
        return False, "Credit score too high (maximum 900)"
    
    return True, ""


def validate_monthly_income(income: float) -> Tuple[bool, str]:
    """
    Validate monthly income.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(income, (int, float)):
        return False, "Monthly income must be a number"
    
    if income < 0:
        return False, "Monthly income cannot be negative"
    
    return True, ""


def validate_age(age: int) -> Tuple[bool, str]:
    """
    Validate user age.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(age, (int, float)):
        return False, "Age must be a number"
    
    age = int(age)
    if age < 18:
        return False, "User must be at least 18 years old"
    if age > 100:
        return False, "Invalid age (maximum 100)"
    
    return True, ""


def validate_employment_status(status: str) -> Tuple[bool, str]:
    """
    Validate employment status.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_statuses = ['salaried', 'self-employed', 'self_employed', 'business', 'professional']
    
    if not status:
        return False, "Employment status is required"
    
    if status.lower().replace('-', '_') not in [s.replace('-', '_') for s in valid_statuses]:
        return False, f"Invalid employment status. Valid options: {', '.join(valid_statuses)}"
    
    return True, ""


def validate_user_data(user: Dict) -> Tuple[bool, List[str]]:
    """
    Validate complete user data.
    
    Args:
        user: Dictionary with user data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Required fields
    if not user.get('user_id'):
        errors.append("user_id is required")
    
    if not user.get('email'):
        errors.append("email is required")
    elif not validate_email(user['email']):
        errors.append("Invalid email format")
    
    # Credit score
    if 'credit_score' in user:
        is_valid, error = validate_credit_score(user['credit_score'])
        if not is_valid:
            errors.append(error)
    else:
        errors.append("credit_score is required")
    
    # Monthly income
    if 'monthly_income' in user:
        is_valid, error = validate_monthly_income(user['monthly_income'])
        if not is_valid:
            errors.append(error)
    else:
        errors.append("monthly_income is required")
    
    # Age
    if 'age' in user:
        is_valid, error = validate_age(user['age'])
        if not is_valid:
            errors.append(error)
    else:
        errors.append("age is required")
    
    # Employment status
    if 'employment_status' in user:
        is_valid, error = validate_employment_status(user['employment_status'])
        if not is_valid:
            errors.append(error)
    else:
        errors.append("employment_status is required")
    
    return len(errors) == 0, errors
