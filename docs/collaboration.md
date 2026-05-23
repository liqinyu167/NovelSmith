# 协作约定

## 分支

- `main` 保存稳定规划和可运行版本。
- 功能开发使用 `feature/<name>`。
- 修复使用 `fix/<name>`。

## 提交

提交信息建议使用：

```text
type(scope): summary
```

常用 type：

- `docs`
- `feat`
- `fix`
- `refactor`
- `test`
- `chore`

## 质量门槛

每次合并至少满足：

- 文档更新和实现一致。
- 核心流程有测试或手动验证记录。
- AI 相关能力有输入输出样例。
- 不提交本地数据库、密钥、缓存和构建产物。

## 决策记录

重大选择写入 `docs/decisions/`，格式为：

```text
YYYY-MM-DD-title.md
```

每条记录包含：

- 背景
- 决策
- 备选方案
- 影响
