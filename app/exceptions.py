from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIException(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.message},
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"status": "error", "message": "Resource not found"},
    )


async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=405,
        content={"status": "error", "message": "Method not allowed"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An unexpected error occurred"},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}

    loc = first.get("loc", [])
    msg = first.get("msg", "Validation error")
    field = loc[-1] if loc else "field"

    message = f"{field}: {msg}".lower()

    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": message},
    )
