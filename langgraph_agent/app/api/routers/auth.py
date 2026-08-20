import logging
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordRequestForm
from app.api.schemas import TokenResponse, UserResponse
from app.services.auth_service import auth_service
from database.user_repository import user_repository
from app.api.auth import require_auth, AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Dashboard Login",
    description="Exchange email and password for a JWT access token."
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = await user_repository.get_user_by_email(form_data.username)
    if not user:
        logger.warning(f"Failed login attempt for unknown email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("active", True):
        logger.warning(f"Login attempt for inactive user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if not auth_service.verify_password(form_data.password, user["password_hash"]):
        logger.warning(f"Invalid password attempt for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate JWT
    access_token = auth_service.create_access_token(
        data={"sub": user["user_id"], "role": user["role"]}
    )
    
    # Audit logging for login
    from database.audit_repository import audit_repository
    await audit_repository.create_audit_log(
        action="AUTH_LOGIN_SUCCESS",
        actor=f"{user['role']}:{user['user_id']}",
        details=f"Dashboard login successful for {user['email']}",
        after_state={"email": user["email"]}
    )

    return TokenResponse(access_token=access_token, token_type="bearer")

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current Dashboard User",
    description="Returns the currently authenticated dashboard user details."
)
async def get_current_user_details(
    user: AuthenticatedUser = Security(require_auth)
) -> UserResponse:
    # If the user is a service account authenticating via static API key
    if user.key_identifier.startswith("***") or user.role == "service":
        return UserResponse(
            user_id=user.key_identifier,
            email="service@elarion.internal",
            role=user.role,
            active=True
        )
        
    db_user = await user_repository.get_user_by_id(user.key_identifier)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return UserResponse(
        user_id=db_user["user_id"],
        email=db_user["email"],
        role=db_user["role"],
        active=db_user["active"],
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at")
    )
