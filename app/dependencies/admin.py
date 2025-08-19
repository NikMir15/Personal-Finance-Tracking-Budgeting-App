"""
Admin authentication and authorization dependencies.
"""

from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.dependencies.jwt_auth import get_current_user


def get_admin_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to verify that the current user has admin privileges.
    
    This is a simplified admin check. In a production system, you might:
    - Have a separate admin role/permission system
    - Use more sophisticated authorization logic
    - Check against specific permissions rather than just admin status
    
    For demo purposes, we'll consider users with specific usernames as admins.
    """
    # Simple admin check - in production, use proper role-based access control
    admin_users = ["admin", "administrator", "root"]
    
    if current_user.username.lower() not in admin_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation"
        )
    
    return current_user


def verify_admin_permissions(
    operation: str,
    current_user: User = Depends(get_admin_user)
) -> bool:
    """
    Verify specific admin permissions for different operations.
    
    Args:
        operation: The operation being performed (e.g., "data_cleanup", "user_management")
        current_user: The admin user
        
    Returns:
        True if the user has permission for the operation
    """
    # In a real system, this would check against a permission matrix
    # For now, all admin users have all permissions
    
    allowed_operations = [
        "data_cleanup",
        "user_management", 
        "system_monitoring",
        "backup_restore",
        "retention_management"
    ]
    
    if operation not in allowed_operations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation '{operation}' not allowed"
        )
    
    return True
