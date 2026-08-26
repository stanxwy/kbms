"""统一业务异常体系。

每个异常携带 HTTP 状态码与业务错误码，由 main 中的全局异常处理器
统一转换为 `{code, message, data}` 响应，避免堆栈/内部信息泄漏给前端。
"""


class AppError(Exception):
    """业务异常基类。"""

    status_code: int = 500
    code: int = 500
    message: str = "service error"

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        code: int | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    code = 400
    message = "bad request"


class UnauthorizedError(AppError):
    status_code = 401
    code = 401
    message = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = 403
    message = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = 404
    message = "not found"


class ConflictError(AppError):
    status_code = 409
    code = 409
    message = "conflict"
