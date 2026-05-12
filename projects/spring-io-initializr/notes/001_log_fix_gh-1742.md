# JVM Version Change Reason Plan Rationale

This note records why the current initializr-only plan exists and how the design changed during review.

## Starting Point

Issue `spring-io/initializr#1742` asks for a way to record why the JVM version changed so that start.spring.io can produce a better help document warning.

The initial investigation found two separate responsibilities:

- `initializr` owns the project generation model, `ProjectDescription`, `MutableProjectDescription`, and `ProjectDescriptionDiff`.
- `start.spring.io` owns the concrete JVM compatibility policies and the help document text.

In this checkout, `initializr` only sets the requested Java version on the `Language` during request conversion. The actual policy-based changes described in the issue live in start.spring.io customizers.

## Review Feedback And Design Changes

- The initial idea was a generic list of change reasons on `ProjectDescription`.
  This was narrowed because the issue is specifically about JVM version changes, and a generic change-reason API would invite a much broader public contract.

- The help document was identified as start.spring.io's responsibility.
  As a result, the initializr-side plan excludes warning text, Vaadin/jOOQ/Kotlin wording, and reason-to-message mapping.

- The current cases were checked and the changed project description field is `language`.
  The customizers replace the `Language` with the same language id and a different `jvmVersion`, so the API should model a JVM version adjustment, not a general language change.

- A two-step API was considered:
  `setLanguage(...)` followed by recording a reason.
  This was rejected because callers could forget the second step. The replacement is one method that changes the JVM version and records the reason together.

- A bare `String reason` was considered.
  This was refined because the string is not user-facing text. It is an opaque identifier that the caller defines and interprets.

- Existing code patterns were checked.
  Similar string-based selectors use `id` terminology, such as `forId(...)`, `getId()`, `BuildItemResolver`, and condition annotations.

- A plain `reasonId` field was considered.
  This was refined again into a `JvmVersionChangeReason` value object with an `id`, which fits the existing "object with id" style and leaves room for future extension without exposing a bare string everywhere.

- A separate JVM-version customizer/resolver lifecycle was considered.
  This was rejected because `ProjectDescriptionCustomizer` already provides the extension point. Adding another lifecycle would create ordering and responsibility questions without solving a new core problem.

## Current Plan

The initializr contribution should provide only the model-level transport for JVM version change reasons:

- Add `JvmVersionChangeReason`, an immutable value object with an `id`.
- Add `JvmVersionChange`, an immutable value object with `from`, `to`, and `reason`.
- Add `ProjectDescription.getJvmVersionChanges()` as a default method returning an empty list.
- Add `MutableProjectDescription.changeJvmVersion(String jvmVersion, JvmVersionChangeReason reason)`.
- Keep `MutableProjectDescription.setLanguage(...)` unchanged and untracked.

`changeJvmVersion(...)` should:

- require an existing language;
- require a non-empty JVM version;
- require a non-null reason;
- preserve the current language id;
- replace only the JVM version through `Language.forId(current.id(), jvmVersion)`;
- record a `JvmVersionChange` only when the JVM version actually changes;
- preserve insertion order and allow repeated reason ids.

## Out Of Scope

The initializr PR should not add:

- start.spring.io reason enums or constants;
- help document warning text;
- Vaadin, jOOQ, Kotlin, or Spring Boot policy decisions;
- reason grouping, deduplication, or message rendering;
- a new customizer lifecycle.

Those belong in start.spring.io, where existing `ProjectDescriptionCustomizer` implementations can call `changeJvmVersion(...)` and the help document customizer can render `getJvmVersionChanges()`.

## Test Focus

The focused initializr tests should verify:

- `changeJvmVersion(...)` preserves language id and updates JVM version;
- changes are recorded with `from`, `to`, and reason;
- no event is recorded when the JVM version is unchanged;
- invalid inputs are rejected;
- returned change lists are immutable;
- `createCopy()` copies existing changes and remains independent from later mutations.

## Implementation Update

During implementation, the `JvmVersionChange` event object with `from`, `to`, and `reason` was removed from the plan.

That shape records internal JVM version transitions, but the target consumer needs to explain why the final JVM version changed. Intermediate transition values can be harder to turn into user-facing help text, especially when several customizers adjust the JVM version in sequence.

The current implementation therefore records only ordered `JvmVersionChangeReason` entries:

- Keep `JvmVersionChangeReason` as the value object with an `id`.
- Add `ProjectDescription.getJvmVersionChangeReasons()` as the read API.
- Keep `MutableProjectDescription.changeJvmVersion(String jvmVersion, JvmVersionChangeReason reason)`.
- Record the reason only when the JVM version actually changes.
- Preserve insertion order and allow repeated reason ids.

The final and original JVM versions can still be derived by consumers from the current `ProjectDescription` and the existing `ProjectDescriptionDiff` original description. The reason list remains the initializr-owned transport for start.spring.io help document rendering.

The focused tests were also narrowed to behavior that matters for this contribution:

- JVM version changes preserve the language id and record the provided reason.
- A no-op JVM version change records no reason.
- The returned reason list is immutable.
- Multiple changes preserve reason order.
- Copy behavior is covered through the existing `ProjectDescriptionDiff` source-copy test data.

## Package Placement Review Point

`JvmVersionChangeReason` currently lives in `io.spring.initializr.generator.project`.

This appears to be the least surprising package because the type is recorded on `ProjectDescription`, written by `MutableProjectDescription.changeJvmVersion(...)`, and intended to be used by `ProjectDescriptionCustomizer` implementations. It is project description metadata, not a language implementation type.

However, this is a careful review point. The `project` package does not currently have a strong precedent for storing a list of opaque id-based marker objects that are interpreted by another application. Existing id-based objects in the generator, such as languages, build systems, repositories, and version qualifiers, tend to be intrinsic domain objects rather than external reason markers.

Alternatives considered:

- Keep it in `project`, because the lifecycle and storage are project-description concerns.
- Create a narrow subpackage under `project` if reviewers want to avoid adding this marker type to the top-level project package.
- Avoid `language`, because the reason is not part of the language model even though the changed value is `Language.jvmVersion()`.
- Avoid `version`, because the type is not a parsed version, version range, or version qualifier.

When opening the PR, call this out explicitly and ask whether maintainers prefer the current `project` package or a narrower package boundary.

## Additional Interface Rework Notes

After further review, the implementation moved from a concrete `JvmVersionChangeReason` value object to an interface:

```java
public interface JvmVersionChangeReason {

	String id();

}
```

The interface is intentionally not annotated with `@FunctionalInterface`. It happens to be lambda-friendly today, but the public API should not promise that the type will always have exactly one abstract method.

No default implementation or factory was added. The reason ids are consumer-defined, so Initializr should not prescribe a concrete reason catalog.

`MutableProjectDescription.changeJvmVersion(...)` now validates:

- `jvmVersion` is not empty;
- `reason` is not null;
- `reason.id()` is not empty;
- `language` is already set.

The method is not responsible for deciding whether a requested JVM version is too low or too high. Callers should only call it when a policy has decided that the generated project needs a different JVM version.

## start.spring.io Follow-Up Examples

If this Initializr support is merged, start.spring.io can define its own reason ids and render them in generated documentation.

Simple enum-based reasons are enough for broad cases:

```java
enum StartJvmVersionChangeReason implements JvmVersionChangeReason {

	SPRING_BOOT_REQUIRES_HIGHER_JAVA("spring-boot.requires-higher-java"),

	KOTLIN_DOES_NOT_SUPPORT_JVM_VERSION("kotlin.unsupported-jvm-version"),

	DEPENDENCY_REQUIRES_HIGHER_JAVA("dependency.requires-higher-java");

	private final String id;

	StartJvmVersionChangeReason(String id) {
		this.id = id;
	}

	@Override
	public String id() {
		return this.id;
	}

}
```

Dependency-specific handling could either use dependency-specific ids, such as `dependency.vaadin.requires-java-21`, or a non-functional implementation that keeps extra start.spring.io-only context while still exposing only `id()` through the Initializr contract:

```java
final class DependencyJvmVersionChangeReason implements JvmVersionChangeReason {

	private final String dependencyId;

	private final String requiredJvmVersion;

	DependencyJvmVersionChangeReason(String dependencyId, String requiredJvmVersion) {
		this.dependencyId = dependencyId;
		this.requiredJvmVersion = requiredJvmVersion;
	}

	@Override
	public String id() {
		return "dependency.%s.requires-java-%s".formatted(this.dependencyId, this.requiredJvmVersion);
	}

	String dependencyId() {
		return this.dependencyId;
	}

	String requiredJvmVersion() {
		return this.requiredJvmVersion;
	}

}
```

The corresponding help document customizer can read `ProjectDescription.getJvmVersionChangeReasons()` and map those ids or implementation types to start.spring.io-specific messages.

## Verification Workflow Addition

Focused test command:

```bash
./mvnw -pl initializr-generator -Dtest=MutableProjectDescriptionTests,ProjectDescriptionDiffTests test
```

Final local verification command:

```bash
./mvnw clean verify
```

Use SDKMAN for the Java toolchain and run Maven through `./mvnw`, as required by `AGENTS.md`.

After implementation and normal verification, use `PROJECT_GENERATION_MANUAL_VERIFICATION.md` only for final manual checks of generated output.

For this branch, the useful manual check is a temporary test-only setup in `initializr-service-sample`:

- add a sample `ProjectDescriptionCustomizer` that calls `changeJvmVersion("17", reason)` when Web is selected with Java 8;
- add a sample help document customizer that renders a message from `getJvmVersionChangeReasons()`;
- run the sample service locally;
- request a project with Java 8 and no Web, and verify the generated project stays on Java 8 with no help warning;
- request a project with Java 8 and Web, and verify the generated project uses Java 17 and `HELP.md` contains the reason-specific warning;
- request a project with Java 17 and Web, and verify no reason is recorded because the JVM version did not change.

This temporary setup must not remain in the final tree. Keep it as an explicit verification commit and then create a signed revert commit so the verification work remains auditable without changing the final PR diff.

The branch used this shape:

```text
Record JVM version change reasons
Verify JVM version change reason output
Revert "Verify JVM version change reason output"
```

## Branch And PR Workflow Addition

Before rewriting or pushing branch history:

```bash
git status --short --branch
git branch backup/gh-1742-before-interface-rework
```

For the implementation commit, stage only the intended Initializr files:

```bash
git add initializr-generator/src/main/java/io/spring/initializr/generator/project/JvmVersionChangeReason.java \
  initializr-generator/src/main/java/io/spring/initializr/generator/project/MutableProjectDescription.java \
  initializr-generator/src/main/java/io/spring/initializr/generator/project/ProjectDescription.java \
  initializr-generator/src/test/java/io/spring/initializr/generator/project/MutableProjectDescriptionTests.java \
  initializr-generator/src/test/java/io/spring/initializr/generator/project/ProjectDescriptionDiffTests.java
```

Use a signed-off implementation commit:

```bash
git commit -s -m "Record JVM version change reasons"
```

If the manual verification commit is created, revert it with a signed commit instead of erasing it:

```bash
git revert -s <verification-commit>
```

Final PR diff should still contain only the five implementation/test files. The verification and revert commits can remain in history when the user wants the manual verification trail preserved.

Push branch updates only; do not perform `gh pr` write operations:

```bash
git push --force-with-lease origin gh-1742
```

Project-scoped Codex rules forbid direct `gh pr` and `gh issue` write
operations, including create, edit, close, reopen, comment, review, and merge
actions. Read-only inspection is fine.

## PR Text Addition

Current PR title:

```text
Record JVM version change reasons
```

Current PR body:

```markdown
This PR adds support for recording why a project's JVM version was changed during project generation.

### Changes

- Add `JvmVersionChangeReason`, an interface that exposes a reason id.
- Add `MutableProjectDescription#changeJvmVersion` to update the JVM version and record a reason when it changes.
- Expose recorded JVM version change reasons from `ProjectDescription`.

### Notes

This change only records JVM version change reasons in Initializr. Consumers such as start.spring.io can define their own reason ids and decide how to render them in generated documentation.

If this PR is merged, I would be interested in helping with the corresponding start.spring.io changes.

Closes gh-1742
```

## PR Review Checklist Addition

After the PR is opened by the user, check it read-only:

```bash
gh pr view 1795 --repo spring-io/initializr --json title,state,mergeable,reviewDecision,statusCheckRollup,commits,files
```

Review expectations:

- title should match the implementation commit;
- final file list should be the five implementation/test files only;
- implementation, temporary verification, and revert commits may all be present when preserving the verification trail;
- PR should be mergeable against `upstream/main`;
- DCO and CodeQL should pass;
- if the build fails, inspect logs before assuming a code issue.

For PR `#1795`, local `./mvnw clean verify` passed on 2026-05-12. The GitHub `Build pull request` check failed in the `-Pfull install` Javadoc phase because `javadoc.io` returned HTTP 521 for the external `javax.cache/cache-api/1.0.0` package-list URL. That failure is external to this PR's code changes.
