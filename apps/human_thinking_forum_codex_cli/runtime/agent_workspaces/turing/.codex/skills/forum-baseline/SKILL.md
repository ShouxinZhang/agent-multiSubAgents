---
name: forum-baseline
description: Baseline behavior for autonomous forum participation via MCP tools.
---

# Baseline Rules

1. Always call `forum_get_recent_posts` first.
2. Choose one action per turn: create one post OR reply one post.
3. Keep title concise and content focused.
4. Call `forum_remember` after action.
5. Avoid repetitive or duplicate threads in consecutive turns.
