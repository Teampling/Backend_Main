from http.client import HTTPException

from starlette import status


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})

    def bad_request(message="Bad Request"):
        raise AppError(status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", message)

    def unauthorized(message="Unauthorized"):
        raise AppError(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)

    def forbidden(message="Forbidden"):
        raise AppError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)

    def not_found(entity="resourse"):
        raise AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{entity} not found")