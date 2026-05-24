"""
NovelSmith Agent Tools — 工具注册中心入口

导入此包时自动注册所有工具模块，使 registry.dispatch 可以派发所有工具。
"""
from app.agent_tools import registry  # noqa: F401
from app.agent_tools import manuscript  # noqa: F401
from app.agent_tools import workspace  # noqa: F401
from app.agent_tools import knowledge  # noqa: F401
from app.agent_tools import chapter  # noqa: F401
from app.agent_tools import audit  # noqa: F401
