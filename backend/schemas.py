from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreateSchema(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    lastName: str = Field(min_length=2, max_length=80)
    documentType: str = Field(default='CC', max_length=20)
    documentNumber: str = Field(min_length=6, max_length=12, pattern=r'^\d+$')
    address: str = Field(min_length=8, max_length=150)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def password_requires_letters_and_numbers(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError('La contraseña debe incluir letras y números.')
        return value


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class UserUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    lastName: Optional[str] = Field(default=None, min_length=2, max_length=80)
    address: Optional[str] = Field(default=None, min_length=8, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default='Cliente', max_length=40)


class ResourceCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=255)
    price: float = Field(default=0, ge=0)


class ResourceStatusSchema(BaseModel):
    active: bool


class AuthRecoverySchema(BaseModel):
    email: EmailStr
