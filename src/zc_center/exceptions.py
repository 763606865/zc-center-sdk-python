from __future__ import annotations


class SapiException(Exception):
    """SDK / 协议层异常基类。"""


class CryptoException(SapiException):
    """加解密失败。"""


class SignatureException(SapiException):
    """请求或响应签名校验失败。"""


class TransportException(SapiException):
    """网络或响应格式错误。"""


class ApiException(SapiException):
    """业务接口返回非成功。"""

    def __init__(
        self,
        message: str,
        *,
        code: int = 0,
        http_status: int = 0,
        data: object | None = None,
        signature_verified: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.data = data
        self.signature_verified = signature_verified
