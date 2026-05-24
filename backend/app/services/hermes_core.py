"""Hermes 核心决策模块。

提供基于关键词的意图分类（写作 / 对话），作为 LLM 意图分类的降级方案。
"""

from dataclasses import dataclass
from typing import Literal

# 代理可执行的动作类型
AgentAction = Literal["chat", "write"]


@dataclass
class AgentDecision:
    """意图分类结果。"""
    action: AgentAction
    reason: str
    requires_approval: bool


def decide_intent(prompt: str) -> AgentDecision:
    """基于关键词启发式分类用户意图。

    优先级：
    1. 含有设定卡片或知识库专有词汇 → 一律走 chat 路由（以便通过工具修改设定）
    2. 强写作关键词 → write（需确认计划）
    3. 弱写作关键词（且不含疑问词）→ write（需确认计划）
    4. 其他 → chat（无需确认）
    """
    # 知识库设定专属词汇 (P0 防御)
    knowledge_words = [
        "设定", "卡片", "世界观", "角色", "大纲", "伏笔", "时间轴", "时间线",
        "目录", "人物", "背景", "线索", "配置文件",
    ]
    if any(word in prompt for word in knowledge_words):
        return AgentDecision(
            action="chat",
            reason="涉及设定或知识库的修改与讨论，走对话及工具调用路由",
            requires_approval=False,
        )

    # 明确的写作指令关键词
    strong_write_words = [
        "续写", "改写", "润色", "扩写", "生成正文",
        "插入", "补一段", "写一段", "写入",
    ]
    # 较弱的写作暗示关键词
    weak_write_words = ["写", "开头", "结尾", "章节"]
    # 疑问/讨论类关键词（用于排除弱写作误判）
    question_words = [
        "怎么", "为什么", "讨论", "分析", "配置", "状态",
        "能不能", "是什么", "建议", "架构", "？", "?",
        # 扩展的中文疑问模式
        "如何", "什么时候", "哪个", "请问", "告诉我",
        "有没有", "可以吗",
    ]

    if any(word in prompt for word in strong_write_words):
        return AgentDecision(
            action="write",
            reason="检测到明确正文写入意图",
            requires_approval=True,
        )

    if any(word in prompt for word in weak_write_words) and not any(
        word in prompt for word in question_words
    ):
        return AgentDecision(
            action="write",
            reason="检测到写作请求",
            requires_approval=True,
        )

    return AgentDecision(
        action="chat",
        reason="普通对话或工具咨询",
        requires_approval=False,
    )
