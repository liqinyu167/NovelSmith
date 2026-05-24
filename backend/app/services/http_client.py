"""共享 httpx.AsyncClient 模块。

提供模块级别的 httpx 异步客户端，避免每次请求都创建/销毁连接池。
通过 FastAPI lifespan 事件管理启动和关闭。
"""

import logging

import httpx

logger = logging.getLogger("novelsmith.http_client")

# 模块级共享客户端实例
_client: httpx.AsyncClient | None = None

# 默认超时配置
_DEFAULT_TIMEOUT = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)


async def startup() -> None:
    """启动时初始化共享 httpx 客户端。"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
        logger.info("共享 httpx.AsyncClient 已启动")


async def shutdown() -> None:
    """关闭时销毁共享 httpx 客户端。"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("共享 httpx.AsyncClient 已关闭")


def get_client() -> httpx.AsyncClient:
    """获取共享 httpx 客户端实例。

    如果客户端尚未初始化（例如在 lifespan 之外调用），会创建一个新的实例。
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
        logger.warning("httpx 客户端在 lifespan 外被创建，建议通过 startup() 初始化")
    return _client
