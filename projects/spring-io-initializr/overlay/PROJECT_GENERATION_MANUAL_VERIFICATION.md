# Project Generation Manual Verification

Use this when a change should be verified with real generated archives, but a
permanent test is not needed.

## Run Target

`initializr-web` is a library module. Run the sample service:

```text
initializr-service-sample
```

## Temporary Setup

Put verification-only code on the runtime classpath. Code under `src/test` is
not enough when checking archives through HTTP.

Common places:

- sample metadata:
  `initializr-service-sample/src/main/resources/application.yaml`
- sample application beans:
  `initializr-service-sample/src/main/java/sample/service/ServiceApplication.java`
- generation contributors:
  `ProjectGenerationConfiguration` registered in `META-INF/spring.factories`

Lifecycle note:

- `ProjectDescriptionCustomizer` beans run when `ProjectDescription` is created.
- `ProjectGenerationConfiguration` classes are processed after that.

So, put temporary `ProjectDescriptionCustomizer` beans in the running sample
application context. Put generated-file customizers or contributors in a
`ProjectGenerationConfiguration`.

## Build And Run

From the repository root:

```bash
./mvnw -pl initializr-service-sample -am -DskipTests install
```

From `initializr-service-sample`:

```bash
../mvnw spring-boot:run \
  -Dspring-boot.run.jvmArguments=-Dspring.devtools.restart.enabled=false
```

The devtools option avoids classloader surprises with temporary
`spring.factories` or classpath changes.

The service runs at:

```text
http://localhost:8080
```

## Generate Archives

Generate a positive case and enough negative cases to prove the behavior is
scoped correctly.

Example:

```bash
curl -sS -o /tmp/case-a.zip \
  'http://localhost:8080/starter.zip?type=maven-project&javaVersion=1.8'

curl -sS -o /tmp/case-b.zip \
  'http://localhost:8080/starter.zip?type=maven-project&javaVersion=1.8&dependencies=web'
```

Adjust request parameters for the feature being checked, such as `type`,
`language`, `javaVersion`, `dependencies`, or `packaging`.

## Inspect Output

Inspect files without extracting the archive:

```bash
unzip -p /tmp/case-b.zip pom.xml
unzip -p /tmp/case-b.zip build.gradle
unzip -p /tmp/case-b.zip HELP.md
```

Filter expected lines:

```bash
unzip -p /tmp/case-b.zip pom.xml |
  rg '<java.version>|spring-boot-starter-web'

unzip -p /tmp/case-b.zip HELP.md |
  rg 'expected warning|expected section|expected link'
```

Record the request, inspected file, expected output, and actual output for each
case.

## Record And Revert

If the temporary setup is useful review context, record it and immediately
remove it:

```bash
git add <temporary-files>
git commit -s -m "Verify <behavior being checked>" \
  -m "Add test-only setup to verify <short expected behavior>."

git revert --no-edit --signoff HEAD
```

Follow normal commit style: imperative subject, concise body, 80-column line
wrapping, and `Signed-off-by`.

## Stop

Stop `spring-boot:run` with `Ctrl-C`.

If needed:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
kill <pid>
```
