# AGENTS.md

These instructions apply to the whole Spring Initializr repository.

## Project Context

- The contribution target is `spring-io/initializr`.
- Local checkouts may use a personal fork as `origin`; use `upstream` as the project reference when reasoning about this overlay.
- This is a multi-module Maven project for Spring Initializr.
- Use the Maven wrapper from the repository root.
- The README currently states that building from source needs Java 25 and a bash-like shell.

## Common Commands

- Full build: `./mvnw clean install`
- Full build with docs: `./mvnw clean install -Pfull`
- Validate formatting/checkstyle: `./mvnw validate`
- Apply Spring JavaFormat: `./mvnw io.spring.javaformat:spring-javaformat-maven-plugin:apply`

## Contribution Notes

- Do not commit this `AGENTS.md`; it is managed by `contribution-overlays`.
- Keep target repository commits focused on upstream contribution changes.
- Commit messages for upstream work need a `Signed-off-by` trailer.
- New Java files should follow existing license header, Javadoc, and `@author` conventions.
- Prefer rebasing feature branches on upstream `main` before opening or updating a PR.
