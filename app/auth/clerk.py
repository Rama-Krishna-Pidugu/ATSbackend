import requests
from jose import jwk, jwt
from jose.utils import base64url_decode
from fastapi import Depends, HTTPException, status, Request
from functools import wraps
from typing import Dict

# Clerk configuration
CLERK_JWKS_URL = "https://big-racer-91.clerk.accounts.dev/.well-known/jwks.json"

# Cache the JWKS
try:
    jwks = requests.get(CLERK_JWKS_URL).json()["keys"]
except Exception as e:
    print(f"Error fetching JWKS: {str(e)}")
    jwks = []

def verify_clerk_token(request: Request) -> Dict:
    """Verify Clerk JWT token and return user claims."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = auth_header.split(" ")[1]
    headers = jwt.get_unverified_header(token)

    key = None
    for jwk_key in jwks:
        if jwk_key["kid"] == headers["kid"]:
            key = jwk_key
            break

    if key is None:
        raise HTTPException(status_code=401, detail="Public key not found.")

    public_key = jwk.construct(key)
    message, encoded_signature = str(token).rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode())

    if not public_key.verify(message.encode(), decoded_signature):
        raise HTTPException(status_code=401, detail="Signature verification failed.")

    claims = jwt.get_unverified_claims(token)
    return claims  # Return full claims dict

     
def get_current_user_claims(request: Request) -> Dict:
    """Dependency to get current user claims from Clerk token."""
    return verify_clerk_token(request)

def get_current_user(request: Request) -> str:
    """Dependency to get current user ID from Clerk token."""
    claims = verify_clerk_token(request)
    return claims['sub']

def require_auth():
    """Decorator to require authentication for routes."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            claims = verify_clerk_token(request)
            user_id = claims['sub']
            kwargs['user_id'] = user_id
            kwargs['user_claims'] = claims
            return await func(*args, **kwargs)
        return wrapper
    return decorator
