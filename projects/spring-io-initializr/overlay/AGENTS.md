# AGENTS.md

These instructions apply to this Spring Initializr checkout.

## Local Overlay

- Target upstream is `spring-io/initializr`; personal forks may be `origin`, so treat `upstream` as the project reference.
- `AGENTS.md` and `.codex/` are local assistant overlay artifacts. Keep them in English and outside the target repository's Git tracking.

## Environment

- Use SDKMAN for Java/toolchain setup.
- Run Maven through the repository wrapper, `./mvnw`.

## GitHub CLI

- Project-scoped Codex rules forbid direct `gh pr` and `gh issue` write operations, including create, edit, close, reopen, comment, review, and merge actions.
- Do not bypass this with reordered `gh` arguments, `gh api`, browser automation, or another GitHub write channel. Read-only `gh` inspection commands are fine.

## Maven

- Clean build/test: `./mvnw clean install`
- Format Java source: `./mvnw io.spring.javaformat:spring-javaformat-maven-plugin:apply`
- Formatting/checkstyle gate: `./mvnw validate`
- Verify: `./mvnw verify`
- Full docs/artifacts build, including Asciidoctor and JavaDoc: `./mvnw clean install -Pfull`

## Contribution Workflow

- Keep upstream commits focused and include a `Signed-off-by` trailer.
- During development, run focused tests/checks for the area being changed.
- Work and commit in meaningful testable change units, which may be internal behavior changes rather than end-to-end features.
- Before committing, run a clean verification pass with `./mvnw clean verify` so tests, formatting, and checkstyle pass.
- After implementation and regular verification, use
  `PROJECT_GENERATION_MANUAL_VERIFICATION.md` only for final manual checks of
  generated output.
- Prefer rebasing feature branches on upstream `main` before opening or updating a PR.

## Contribution Code Rules

- TDD is optional, but logic changes need commit-time test verification through existing, updated, removed, or new tests.
- Add `@author` only for new classes or substantial functional changes where ownership context is useful.
- Skip it for formatting, small fixes, tests-only changes, and minor helper or developer-convenience additions.
