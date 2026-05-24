"""URL 验证模块 —— 防止 SSRF 攻击。

在向用户指定的 LLM base_url 发起请求前，校验目标地址是否安全。
阻止指向私有 IP、回环地址、localhost 以及非 http(s) 协议的请求。
"""

import ipaddress
import socket
import logging
from urllib.parse import urlparse

from app.exceptions import InvalidBaseURLError

logger = logging.getLogger("novelsmith.url_validator")

# 允许的 URL 协议
_ALLOWED_SCHEMES = {"http", "https"}


def validate_base_url(url: str) -> None:
    """校验 base_url 是否安全，不安全则抛出 InvalidBaseURLError。

    检查项：
    1. 协议必须为 http 或 https
    2. 主机名不能是 localhost
    3. 解析后的 IP 不能是私有地址、回环地址或保留地址
    """
    if not url or not url.strip():
        raise InvalidBaseURLError(url, "URL 不能为空")

    parsed = urlparse(url.strip())

    # 检查协议
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise InvalidBaseURLError(url, f"不允许的协议: {parsed.scheme}，仅支持 http/https")

    hostname = parsed.hostname
    if not hostname:
        raise InvalidBaseURLError(url, "无法解析主机名")

    # 检查 localhost
    if hostname.lower() in {"localhost"}:
        raise InvalidBaseURLError(url, "不允许访问 localhost")

    # 尝试将主机名解析为 IP 地址并检查
    try:
        addr = ipaddress.ip_address(hostname)
        _check_ip_address(addr, url)
    except ValueError:
        # hostname 不是 IP 字面量，尝试 DNS 解析
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in resolved:
                ip_str = sockaddr[0]
                addr = ipaddress.ip_address(ip_str)
                _check_ip_address(addr, url)
        except socket.gaierror:
            # DNS 解析失败，放行让后续 HTTP 调用自然报错
            logger.warning("DNS 解析失败，放行 URL: %s", url)


def _check_ip_address(addr: ipaddress.IPv4Address | ipaddress.IPv6Address, url: str) -> None:
    """检查单个 IP 地址是否安全。"""
    # 回环地址: 127.0.0.0/8, ::1
    if addr.is_loopback:
        raise InvalidBaseURLError(url, f"不允许访问回环地址: {addr}")

    # 私有地址: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7
    if addr.is_private:
        # 允许 Clash Fake-IP 范围 (198.18.0.0/15)，因为代理工具会将公共域名解析到此范围
        if isinstance(addr, ipaddress.IPv4Address) and addr in ipaddress.ip_network("198.18.0.0/15"):
            return
        raise InvalidBaseURLError(url, f"不允许访问私有地址: {addr}")

    # 保留地址: 0.0.0.0 等
    if addr.is_reserved:
        raise InvalidBaseURLError(url, f"不允许访问保留地址: {addr}")

    # 未指定地址: 0.0.0.0, ::
    if addr.is_unspecified:
        raise InvalidBaseURLError(url, f"不允许访问未指定地址: {addr}")

    # 链路本地地址: 169.254.0.0/16, fe80::/10
    if addr.is_link_local:
        raise InvalidBaseURLError(url, f"不允许访问链路本地地址: {addr}")
