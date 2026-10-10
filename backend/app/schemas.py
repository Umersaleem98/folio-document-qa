from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Register(StrictModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class Login(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Profile(StrictModel):
    name: str = Field(min_length=1, max_length=100)


class PasswordChange(StrictModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class NewConversation(StrictModel):
    document_ids: list[str] = Field(min_length=1, max_length=10)
    title: str = Field(default='Document conversation', min_length=1, max_length=120)


class Question(StrictModel):
    content: str = Field(min_length=1, max_length=2000)


class UserUpdate(StrictModel):
    active: bool
    role_id: int


class LimitsUpdate(StrictModel):
    max_upload_mb: int = Field(ge=1, le=100)
    max_documents: int = Field(ge=1, le=1000)
    daily_questions: int = Field(ge=1, le=10000)


class RoleCreate(StrictModel):
    name: str = Field(min_length=2, max_length=40, pattern=r'^[a-z][a-z0-9_-]+$')
    permissions: list[str]


class RoleUpdate(StrictModel):
    permissions: list[str]
