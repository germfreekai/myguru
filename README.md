# myguru

myguru turns any local source tree into a queryable AI assistant. It indexes your project files into a ChromaDB vector database, then uses Ollama to answer questions about your code — entirely offline, with no external API calls. There is no server to run; it is a CLI tool invoked once per session.

---

## Prerequisites

**Python:** 3.12.3 or later.

**Ollama** must be installed and running locally:

```bash
# Install Ollama (Linux / WSL2)
curl -fsSL https://ollama.com/install.sh | sh
```

See https://ollama.com/download for macOS and Windows installers.

Start the Ollama server if it is not already running as a service:

```bash
ollama serve
```

Pull the default models (required before first use):

```bash
ollama pull qwen2.5-coder:latest   # LLM — configurable via --llm
ollama pull nomic-embed-text       # embedding model — configurable via --cle
```

---

## Installation

```bash
git clone https://github.com/germfreekai/myguru.git
cd myguru
python3 -m venv env
source env/bin/activate
pip install -e .
```

To make `myguru` available outside the virtualenv:

```bash
deactivate
ln -s "$(readlink -f env/bin/myguru)" ~/.local/bin/myguru
```

---

## Configuration via `.env`

All CLI options can also be set via environment variables in a `.env` file. The `.env` file is loaded automatically when you run `myguru` from the project root. CLI flags always take precedence over `.env`/environment values.

### Remote Ollama hosts

| Variable | Description |
|---|---|
| `MYGURU_LLM_HOST` | Full Ollama server URL for the LLM — overrides `--base-url`/`--port` (and their env equivalents) when set (e.g. `http://192.168.1.100:11434`) |
| `MYGURU_CLE_HOST` | Full URL for the embedding model host, if different from the LLM host. Falls back to the resolved LLM host when unset. |

### Example `.env`

```bash
# Create a .env file in the project root
$ cat .env
MYGURU_SRC=./src
MYGURU_DB=./myguru-db
MYGURU_LLM=qwen2.5-coder:latest
MYGURU_EMBED_MODEL=nomic-embed-text
MYGURU_QUIET=1
# MYGURU_LLM_HOST=http://192.168.1.100:11434
# MYGURU_CLE_HOST=http://192.168.1.101:11434
```

Once the file is in place, just run `myguru` — no CLI flags are needed for anything already set in `.env`. See [Configuration Reference](#configuration-reference) below for the full list of flags and their env-var equivalents.

---

## Quick Start for Automation / CI

All flags have environment-variable fallbacks. Set them once in your pipeline; no flags are needed on the command line.

```bash
export MYGURU_SRC=/workspace/myproject/src
export MYGURU_DB=/workspace/myproject-db
export MYGURU_QUIET=1
export MYGURU_BASE_URL=http://ollama-service   # if Ollama is on a remote host

# Index — exits 0 on success, 1 on failure
if myguru learning -c -ea __pycache__ -ee pyc; then
    echo "Indexing complete"
else
    echo "Indexing failed" >&2
    exit 1
fi

# Single structured query — clean JSON on stdout, logs on stderr
result=$(myguru guru -q "List all public functions" --json 2>/dev/null)
echo "$result" | jq '.response'

# Redirect logs to a file while keeping the JSON on stdout
myguru guru -q "Summarize the architecture" --json 2>guru.log
```

### `--quiet` placement gotcha

`--quiet` is a **global flag** and must appear **before** the subcommand name:

```bash
# Correct — --quiet before the subcommand
myguru --quiet -s src --db mydb learning -c
myguru -s src --db mydb --quiet learning -c

# Wrong — --quiet after the subcommand will error
myguru -s src --db mydb learning --quiet -c
# → error: unrecognized arguments: --quiet
```

---

## Usage — Interactive (local development)

### Index a project from scratch

```bash
myguru -s src --db myproject-db learning -c \
    -ea __pycache__ \
    -ea .git \
    -ee pyc \
    -ee egg-info
```

| Exclude flag | What it does |
|---|---|
| `-e path/to/file_or_dir` | Exclude a specific file or directory by path |
| `-ea name` | Exclude any file or directory with this name, at any depth |
| `-ee ext` | Exclude all files with this extension |

All exclude parameters are stored in `project_hashes.json` and reused on subsequent `learning -u` runs.

### Update an index after code changes

```bash
myguru -s src --db myproject-db learning -u
```

Files whose MD5 has changed are removed from the index and re-embedded. New files added to the source tree since the last `learning -c` are detected automatically and added to the index.

### Interactive query session

```bash
myguru -s src --db myproject-db guru
```

```
[user] > how is the configuration loaded?
[myguru] > Configuration is loaded in main.py via parse_args()...
_________________________
[user] > quit
```

Type `quit` or `exit` to end the session.

---

## Usage — Single Query Mode

Run one question non-interactively and exit. No REPL is started.

```bash
# Plain-text response
myguru -s src --db myproject-db guru -q "What does walk_directory do?"

# Structured JSON to stdout (logs go to stderr)
myguru -s src --db myproject-db guru -q "What does walk_directory do?" --json
```

### JSON output shape

```json
{
  "query": "What does walk_directory do?",
  "response": "walk_directory recursively walks src_path...",
  "sources": [
    {
      "file_path": "src/myguru/utils/utils.py",
      "score": 0.8312,
      "content": "def walk_directory(src_path, exclude, ..."
    }
  ]
}
```

Exit code: `0` on success, `1` on error. No REPL prompt text appears on stdout in this mode.

---

## Configuration Reference

| Flag | Short | Env variable | Default |
|---|---|---|---|
| `--src` | `-s` | `MYGURU_SRC` | _(required)_ |
| `--db` | | `MYGURU_DB` | _(required)_ |
| `--llm` | | `MYGURU_LLM` | `qwen2.5-coder:latest` |
| `--cle` | | `MYGURU_EMBED_MODEL` | `nomic-embed-text` |
| `--base-url` | `-u` | `MYGURU_BASE_URL` | `http://127.0.0.1` |
| `--port` | `-p` | `MYGURU_PORT` | `11434` |
| `--quiet` | | `MYGURU_QUIET` | unset |
| `--hash-file` | `-f` | _(none)_ | `project_hashes.json` |
| _(none)_ | | `MYGURU_LLM_HOST` | _(unset — falls back to --base-url + --port)_ |
| _(none)_ | | `MYGURU_CLE_HOST` | _(unset — falls back to --base-url + --port)_ |

CLI flags take precedence over environment variables. `--src` and `--db` are required unless set via their env vars.

`MYGURU_LLM_HOST` and `MYGURU_CLE_HOST` are host-override env vars with no CLI flag equivalent. When set, they take full precedence over --base-url and --port for their respective models.

The following parameters are hardcoded and require source changes to modify:

| Parameter | Value | Location |
|---|---|---|
| LLM temperature | `0.0` | `rag_base.py` |
| Request timeout | `300.0 s` | `rag_base.py` |
| Similarity top-k | `5` | `rag_query.py` |
| Chunk size | LlamaIndex default (1024 tokens) | `rag_builder.py` |

---

## Running a Smoke Test

This end-to-end check confirms that Ollama, ChromaDB, and myguru are all wired correctly. It indexes the myguru source itself and queries it.

```bash
# 1. From the repo root, index the myguru source
myguru -s src --db /tmp/myguru-smoketest-db learning -c \
    -ea __pycache__ \
    -ee pyc
# Expected: INFO lines showing each file being parsed, then "Indexing completed!"
# Exit code must be 0.

# 2. Run a single structured query
myguru -s src --db /tmp/myguru-smoketest-db \
    guru -q "What does the walk_directory function do?" --json 2>/dev/null
```

Expected output (abbreviated):

```json
{
  "query": "What does the walk_directory function do?",
  "response": "The walk_directory function recursively walks a source directory...",
  "sources": [
    {
      "file_path": "src/myguru/utils/utils.py",
      "score": 0.8541,
      "content": "def walk_directory(src_path, exclude, exclude_all, exclude_ext):\n..."
    }
  ]
}
```

If the response is populated and the exit code is 0, the setup is working. Clean up afterward:

```bash
rm -rf /tmp/myguru-smoketest-db project_hashes.json
```

---

## Migration Notes (upgrading from pre-0.1 optimization)

If you have an existing myguru database created before the optimization pass, three breaking changes require action:

1. **Collection name changed.** The ChromaDB collection is now named using a SHA-1 hash of the absolute `--src` path instead of the last directory component. Existing databases are unreadable by the new code. Delete the old DB and re-index:
   ```bash
   rm -rf your-existing-db/
   myguru -s your/src --db your-existing-db learning -c [exclude options]
   ```

2. **Exit codes changed.** `learning` now exits `0` on success (it was `1`). Update any script that checked `$? -ne 0` after an indexing run.

3. **Logs moved to stderr.** All `INFO`/`WARNING`/`ERROR` output now goes to `stderr`. Program output (JSON responses, REPL answers) goes to `stdout`. Update any wrapper script that captured log lines from `stdout`.

See `CHANGES.md` for a full list of changes.

---

## Development

CI runs `black`, `isort`, `pylint`, and a package build on every push/PR via `.github/workflows/ci.yml`.

The repo also includes an opt-in pre-push git hook at `.githooks/pre-push` that runs the same checks locally before every push, auto-installing any missing tools. Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

Verify it's active:

```bash
git config core.hooksPath
# Should output: .githooks
```

To skip the hook for a specific push (e.g. work-in-progress):

```bash
git push --no-verify
```

---

## Known Limitations

- **Single source directory.** Only one `--src` path per database. Indexing multiple unrelated directories requires separate databases.
- **No chunking configuration via CLI.** Chunk size and overlap use LlamaIndex defaults (1024 tokens / 20-token overlap). Changing them requires editing `rag_builder.py`.
- **No test suite.** There are no automated tests. Correctness is verified manually.
- **No type hints.** Function signatures lack Python type annotations; static type checkers cannot analyze this code.
- **LLM parameters hardcoded.** `temperature`, `request_timeout`, `similarity_top_k`, and the system prompt cannot be changed without editing source files.
- **`learning -u` requires the hash file.** If `project_hashes.json` is lost or deleted, a full re-index (`learning -c` on a fresh DB) is required.
