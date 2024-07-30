from fastapi import FastAPI, Depends
import uvicorn
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from fastapi_azure_auth.exceptions import InvalidAuth
from fastapi_azure_auth.user import User

from fastapi import FastAPI

from pydantic import AnyHttpUrl, computed_field
from pydantic_settings import BaseSettings
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from typing import Union


class Settings(BaseSettings):
    BACKEND_CORS_ORIGINS: list[Union[str, AnyHttpUrl]] = ["http://localhost:8000"]
    OPENAPI_CLIENT_ID: str = ""
    APP_CLIENT_ID: str = ""
    TENANT_ID: str = ""
    SCOPE_DESCRIPTION: str = ""

    @computed_field
    @property
    def SCOPE_NAME(self) -> str:
        return f"api://{self.APP_CLIENT_ID}/{self.SCOPE_DESCRIPTION}"

    @computed_field
    @property
    def SCOPES(self) -> dict:
        return {
            self.SCOPE_NAME: self.SCOPE_DESCRIPTION,
        }

    @computed_field
    @property
    def OPENAPI_AUTHORIZATION_URL(self) -> str:
        return (
            f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/authorize"
        )

    @computed_field
    @property
    def OPENAPI_TOKEN_URL(self) -> str:
        return f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/token"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Load OpenID config on startup.
    """
    await azure_scheme.openid_config.load_config()
    yield


app = FastAPI(
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.OPENAPI_CLIENT_ID,
        "scopes": settings.SCOPE_NAME,
    },
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=settings.APP_CLIENT_ID,
    tenant_id=settings.TENANT_ID,
    scopes=settings.SCOPES,
)


@app.get("/")
async def root(user: User = Depends(azure_scheme)):
    print(user.roles)
    return {"message": "Hello World"}


@app.get("/me")
async def me(user: User = Depends(azure_scheme)):
    return user.model_dump()


@app.delete("/delete")
async def delete_data(id: int, user: User = Depends(azure_scheme)):
    if "API.Admins" not in user.roles:
        raise InvalidAuth("User is not authorized to access this endpoint.")
    else:
        return {"message": "delete called."}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
