from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
