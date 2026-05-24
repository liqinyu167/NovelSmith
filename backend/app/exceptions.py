"""NovelSmith 自定义异常模块。

定义后端专用异常类，供 API 层和服务层统一使用。
"""


class NovelSmithError(Exception):
    """NovelSmith 后端基础异常。"""


class ProviderNotConfiguredError(NovelSmithError):
    """LLM 服务商未配置（缺少 base_url / model / api_key）。"""

    def __init__(self, message: str = "请先在右上角配置 Base URL、Model 和 API Key。") -> None:
        super().__init__(message)


class ProviderConnectionError(NovelSmithError):
    """无法连接到 LLM 服务商。"""

    def __init__(self, message: str = "无法连接到 LLM 服务商，请检查网络和配置。") -> None:
        super().__init__(message)


class InvalidBaseURLError(NovelSmithError):
    """base_url 不合法（例如指向内网地址或使用了非 http(s) 协议）。"""

    def __init__(self, url: str = "", reason: str = "") -> None:
        detail = f"不合法的 Base URL: {url}" if url else "不合法的 Base URL"
        if reason:
            detail = f"{detail} ({reason})"
        super().__init__(detail)
        self.url = url
        self.reason = reason


class PlanGenerationError(NovelSmithError):
    """写作计划生成失败。"""

    def __init__(self, message: str = "写作计划生成失败，请稍后重试。") -> None:
        super().__init__(message)
