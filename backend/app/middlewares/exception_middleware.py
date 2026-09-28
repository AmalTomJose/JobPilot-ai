from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class UserException(Exception):

    def __init__(
        self,
        status_code: int,
        message: str,
        details: dict | None = None
    ):
        self.status_code = status_code
        self.message = message
        self.details = details


def register_exception_handlers(app: FastAPI):

    # --------------------------------
    # User / Business Exceptions
    # --------------------------------

    @app.exception_handler(UserException)
    async def user_exception_handler(
        request: Request,
        exc: UserException
    ):
        return JSONResponse(
            status_code=exc.status_code,
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
            content={
                "success": False,
                "message": exc.message,
                **({"details": exc.details} if exc.details is not None else {}),
            }
        )

    # --------------------------------
    # Request Validation Exceptions
    # --------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "success": False,
                "message": exc.errors()[0]["msg"]
            }
        )

    # --------------------------------
    # HTTP Exceptions
    # --------------------------------

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ):
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "success": False,
                "message": str(exc.detail)
            }
        )

    # --------------------------------
    # Unexpected Exceptions
    # --------------------------------

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception
    ):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An unexpected error occurred"
            }
        )