---
name: commit-style
description: Use when the user asks to commit changes or draft a commit message.
---

# Commit Style

## Workflow

When the user asks to commit in this repository:

1. Inspect the current state with `git status`, relevant `git diff`, and `git diff --staged`.
2. Read `AGENTS.md` and skim `git log --oneline -10` for local constraints.
3. Identify logical work units before staging; mixed changes should usually become separate commits.
4. Stage only one work unit at a time by explicit path after checking for secrets or unrelated changes.
5. Commit with the message format below. Ask first only when the split is ambiguous or risky.
6. Confirm with `git status`.

## Commit Units

- Prefer one commit per coherent reason for change, not one commit per file.
- Split unrelated docs, fixes, features, and maintenance work.
- If drafting messages only, draft one message per work unit.

## Message Format

Use `<type>: <Korean subject>`. Keep the type set small:

- `feat`: user-visible behavior or capability
- `fix`: bug fix or incorrect behavior correction
- `docs`: documentation, instructions, or writing-only change
- `chore`: tests, build, config, dependencies, cleanup, or maintenance

Rules:

- Write the subject and any body in Korean.
- Keep the subject short, concrete, and without trailing punctuation.
- Use a body only when the reason needs context.
- In the body, explain why the change matters rather than narrating the diff.

Examples:

```text
feat: 오버레이 동기화 검증 추가
fix: 잘못된 심링크 판정 수정
docs: 커밋 스킬 지침 정리
chore: 테스트 설정 정리
```

## Constraints

- Do not push unless the user explicitly asks.
- Do not use `--amend`, `--no-verify`, or `--no-gpg-sign` unless explicitly requested.
