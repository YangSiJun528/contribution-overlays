# contribution-overlays

`contribution-overlays` manages project-specific agent instruction files in this
repository and places them into external target repositories as symlinks.

The target repository's Git history should not contain these overlay files.
`sync` updates `.git/info/exclude`, never `.gitignore`.

## Layout

```text
projects/
  <project-name>/
    overlay.toml
    overlay/
      AGENTS.md
      some/path/AGENTS.md
    notes.md
```

Example `overlay.toml`:

```toml
project = "rust-lang-rust"

files = [
  "AGENTS.md",
  "compiler/AGENTS.md",
  "library/AGENTS.md",
]
```

Rules:

- `project` must match the directory name under `projects/`.
- `files` are target repository relative paths.
- Each file must exist under the project's `overlay/` directory.
- Absolute paths, `..`, `.git/` paths, and duplicates are rejected.

## Commands

```bash
uv run contribution-overlays sync <target-repo> <project-name>
uv run contribution-overlays check <target-repo> <project-name>
uv run contribution-overlays unlink <target-repo> <project-name>
```

Useful options:

```bash
uv run contribution-overlays sync --dry-run <target-repo> <project-name>
uv run contribution-overlays sync --prune --clean-exclude <target-repo> <project-name>
uv run contribution-overlays sync --replace-wrong <target-repo> <project-name>
uv run contribution-overlays unlink --clean-exclude <target-repo> <project-name>
```

By default the source root is the current working directory. Use
`--source-root <path>` before the subcommand when running from another location.

## Safety Model

Status values are fixed in code:

- `OK`: target symlink points at the expected overlay file.
- `MISSING`: target path does not exist.
- `BROKEN`: target path is a broken symlink.
- `WRONG`: target path is a symlink to a different target.
- `CONFLICT`: target path is a regular file or directory.
- `TRACKED`: target Git tracks the path.
- `STAGED`: target Git index has the path staged.
- `IGNORE_MISSING`: `.git/info/exclude` lacks the path.
- `EXTRA`: a symlink that appears to point into this project's overlay remains,
  but is no longer listed in `overlay.toml`.

Automatic `sync` handling is limited to `MISSING`, `BROKEN`, and
`IGNORE_MISSING`. `WRONG` and `EXTRA` require options. `CONFLICT`, `TRACKED`,
and `STAGED` are never modified automatically.

