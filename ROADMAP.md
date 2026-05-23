# NovelSmith Roadmap

NovelSmith is moving toward a local-first, Hermes/Codex-style writing agent for long-form fiction. The current MVP proves the core loop: chat with an agent, detect intent, create a write plan, wait for user approval, then stream manuscript text into the editor.

## Product Direction

NovelSmith should feel like a writing cockpit, not a generic chatbot. The right panel is the Director Agent conversation. The center is the manuscript. The left hamburger menu switches workspaces such as manuscript, outline, worldbuilding, characters, memory, and review.

The agent must support normal conversation and tool use. Not every user message should become manuscript text. The system should route intent first:

- Chat: answer questions, discuss structure, inspect current context, suggest strategy.
- Plan: prepare a structured write action without modifying the manuscript.
- Execute: write only after the user approves the plan.
- Review: inspect consistency, tone, pacing, hooks, and continuity.
- Remember: update project memory, character facts, and writing preferences.

## Near-Term Milestones

### 1. Agent Runtime

- Replace the in-memory run store with persistent run records.
- Add run receipts: prompt, model, provider, plan, approval, output, token usage, and errors.
- Add a stronger state machine: idle, classifying, tool_use, planning, awaiting_approval, executing, reviewing, done, failed.
- Support interrupt, retry, regenerate, and rollback for every write action.
- Add provider test calls and clearer model/API error messages.

### 2. Tool System

- Formalize tools instead of hardcoding context reads.
- Initial tools:
  - `read_project_context`
  - `read_manuscript_excerpt`
  - `summarize_chapter`
  - `inspect_characters`
  - `update_project_memory`
  - `propose_write_plan`
  - `apply_manuscript_patch`
- Display tool activity as compact process bubbles in the conversation.
- Require user approval for destructive or manuscript-changing tools.

### 3. Writing Memory

- Add SQLite persistence for projects, chapters, messages, run events, and memories.
- Maintain layered memory:
  - Project brief
  - World rules
  - Character facts
  - Chapter summaries
  - User writing preferences
  - Reusable writing skills
- Add automatic memory extraction after confirmed writes.

### 4. Manuscript Workflow

- Move from raw append-only writing to patch-based updates.
- Show proposed diff before applying rewrites.
- Support chapter outline, scene cards, and beat-level planning.
- Add undo/rollback per approved write.
- Add export to Markdown first, then EPUB later.

### 5. Review Agent

- Add review modes:
  - Continuity check
  - Character consistency
  - Hook strength
  - Pacing
  - Style drift
  - Repetition detection
- Review should produce actionable comments, not auto-edit without approval.

### 6. Frontend

- Keep the right-side agent language and interaction model.
- Keep the center editor manuscript-first.
- Add hamburger workspaces:
  - Manuscript
  - Outline
  - Characters
  - Worldbuilding
  - Memory
  - Review
  - Settings
- Add a proper project switcher and chapter list.
- Add keyboard-first writing ergonomics and better mobile fallback.

### 7. Local Deployment

- Add Docker Compose for frontend, backend, and SQLite volume.
- Add `.env.example`.
- Add production build instructions.
- Add optional Ollama/OpenAI-compatible local model profile.

## Longer-Term Vision

NovelSmith should become a self-hosted writing agent that learns each author's workflow. It should remember story facts, writing habits, preferred pacing, recurring revision patterns, and reusable workflows. Over time, common successful workflows can be crystallized into named skills, such as "web novel opening hook", "chapter cliffhanger pass", "romance tension rewrite", or "mystery clue consistency audit".

The goal is not to replace the author. The goal is to make the AI behave like a careful writing partner: it asks before changing the manuscript, explains what it is about to do, uses tools when needed, and leaves an audit trail of every meaningful change.
