# 织文技术架构

## 总体选择

MVP 推荐采用前后端分离架构：

- Frontend：React + TypeScript + Vite
- UI：Tailwind CSS + Radix UI
- State：Zustand
- Editor：ProseMirror 或 TipTap
- Backend：Python FastAPI
- Database：PostgreSQL
- Queue：Redis + RQ
- Search：PostgreSQL full text search, 后续可升级为 Meilisearch
- AI Provider：OpenAI-compatible adapter, 预留多供应商配置

## 分层

```text
apps/
  web/                 用户界面
  api/                 HTTP API
packages/
  schema/              共享类型和接口契约
  prompts/             提示词模板和评测样例
  text-engine/         摘要、分章、检查等纯逻辑
docs/
  product-spec.md
  mvp-scope.md
```

## 后端边界

API 层只处理认证、权限、输入校验和响应格式。业务逻辑进入 service 层。AI 调用必须经过 provider adapter，避免业务代码直接绑定某个模型厂商。

核心服务：

- ProjectService：项目、成员、权限。
- OutlineService：卷、章节、场景结构。
- ManuscriptService：正文、版本、批注。
- LoreService：人物、地点、组织、术语、规则。
- ConsistencyService：冲突检查、伏笔追踪、时间线校验。
- AssistantService：AI 生成、改写、摘要、建议。

## 数据模型草案

主要实体：

- User
- Project
- ProjectMember
- OutlineNode
- ManuscriptBlock
- Revision
- Comment
- LoreCard
- TimelineEvent
- ForeshadowingThread
- AssistantRun

关键关系：

- Project 拥有多个 OutlineNode 和 LoreCard。
- OutlineNode 可以表示卷、章、场景，并通过 parent_id 形成树。
- ManuscriptBlock 绑定 OutlineNode，用于支持局部版本和批注。
- AssistantRun 保存输入、输出、引用来源和采纳状态。

## AI 安全边界

- AI 不能静默改写正文，只能生成建议或草稿版本。
- 每次 AI 输出都记录来源上下文、模型、参数和用户处理结果。
- 长上下文任务通过检索项目资料和章节摘要完成，不直接塞入全量正文。
- 默认不上传用户未选择的私密资料到外部模型。

## 非功能目标

- 单项目 100 万字内保持常用操作流畅。
- 章节编辑首屏加载小于 1.5 秒。
- 本地草稿自动保存间隔小于 10 秒。
- AI 任务失败时可重试，并保留失败原因。
