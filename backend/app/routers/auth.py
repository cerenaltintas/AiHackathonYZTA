from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Token

router = APIRouter()

# Demo kullanıcı — gerçek projede veritabanından çekilir
_DEMO_USER = {
    "username": "admin",
    "hashed_password": hash_password("admin123"),
}


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != _DEMO_USER["username"] or not verify_password(
        form_data.password, _DEMO_USER["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": form_data.username})
    return Token(access_token=token)
