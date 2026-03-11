from fastapi import HTTPException

from starlette import status


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "data": None})

    @staticmethod
    def bad_request(message="Bad Request"):
        return AppError(status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", message)

    @staticmethod
    def unauthorized(message="Unauthorized"):
        return AppError(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)

    @staticmethod
    def forbidden(message="Forbidden"):
        return AppError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)

    @staticmethod
    def not_found(entity="resourse"):
        return AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{entity}을(를) 찾을 수 없습니다.")