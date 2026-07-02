# myguru — Changes

> Optimization and hardening pass. See ANALYSIS.md for the pre-change audit.

---

## PRIORITY 1 — CI/CD Blockers

### 1. Fixed: `learning` mode always exited with code 1 (`main.py`)

**Before:** `rag_builder()` called `sys.exit(1)` unconditionally at the end, even on success.
**After:** `sys.exit(0)` on success. All error paths inside `RAGBuilder` already called `sys.exit(1)`, so the semantics are now correct: 0 = success, 1 = failure.

**Behavior change you need to know:** If you were checking `$?` after `myguru learning` and expecting 1, update your scripts to expect 0.

---

### 2. New: Single-query mode for `guru` (`rag_query.py`, `main.py`)

Two new flags on the `guru` subcommand:

| Flag | Description |
|---|---|
| `-q TEXT` / `--query TEXT` | Run one question and exit. No REPL is started. |
| `--json` | With `-q`: print a structured JSON object to stdout and exit. |

**Usage:**

```bash
# Plain-text single query
myguru -s src --db mydb guru -q "What does walk_directory do?"

# Machine-readable JSON output (stdout only; logs go to stderr)
myguru -s src --db mydb guru -q "What does walk_directory do?" --json
```

**JSON output shape:**
```json
{
  "query": "What does walk_directory do?",
  "response": "...",
  "sources": [
    { "file_path": "src/...", "score": 0.4231, "content": "..." }
  ]
}
```

Exit codes: 0 on success, 1 on error. No REPL prompt text (`[user] >`, `[myguru] >`) is written to stdout in this mode.

---

### 3. Fixed: Collection name collision (`rag_base.py`)

**Before:** Collection name derived from the last path component of `--src`:
```python
self.collection_name = self.src_path.split("/")[-1]
# e.g. --src /home/user/project/src  →  collection "src"
```
Two different projects sharing a final directory name (e.g. both called `src/`) would collide in the same ChromaDB.

**After:** SHA-1 hash of the absolute resolved path:
```python
self.collection_name = hashlib.sha1(os.path.abspath(src_path).encode()).hexdigest()
```

**Breaking change — action required:** Any ChromaDB created with the old code uses a collection under the old name. Existing databases **cannot be read** by the new code without recreation. To migrate:

```bash
rm -rf your-existing-db/
myguru -s your/src --db your-existing-db learning -c [exclude options]
```

---

## PRIORITY 2 — Correctness Fixes

### 4. Fixed: New files not detected by `learning -u` (`rag_builder.py`)

**Before:** `update_index` only compared MD5s of files already in `project_hashes.json`. Files added to the project after the initial `learning -c` were never indexed.

**After:** `update_index` now walks the source directory using the exclude parameters stored in the hash file and adds any files not already tracked.

**New hash file format:** The hash file now uses a structured format:
```json
{
  "files": { "path/to/file.py": "<md5>", ... },
  "meta":  {
    "src_path": "/abs/path/to/src",
    "exclude": null,
    "exclude_all": ["__pycache__"],
    "exclude_ext": null
  }
}
```

Legacy flat hash files (`{ "path": "hash", ... }`) are read transparently but do not support new-file detection because the original exclude parameters were not stored. Re-run `learning -c` with a fresh DB to enable new-file detection.

---

### 5. Fixed: `_IS_INIT` class-level singleton (`rag_base.py`, `rag_query.py`)

**Before:** `RAGBase` used a class-level `_IS_INIT` flag intended to prevent double initialization when `RAGQuery` was also instantiated in the same process. The mechanism was broken — it operated on instance attributes instead of the class attribute, so `RAGBase.__init__` actually ran twice (visible as two `INIT RAG BASE` log lines per guru session).

**After:** `_IS_INIT` is removed entirely. `RAGQuery` no longer inherits from `RAGBase` — it uses composition:

```python
# Old (inheritance):
query = RAGQuery(tool_name, src, db, llm, cle, base_url, index)

# New (composition — RAGQuery receives an already-initialized builder):
query = RAGQuery(builder, index)
```

`RAGBase.__init__` now runs exactly once per invocation. The `INIT RAG BASE` log line now appears only once instead of twice.

---

### 6. Fixed: Dangling loop variable in `update_index` (`rag_builder.py`)

**Before:** Delete and insert operations for a changed file were executed on `doc` after the `for doc in docs:` loop, referencing only the last document yielded. If `FlatReader` ever returned more than one document per file, all but the last would be silently skipped.

**After:** Delete and insert are executed inside the loop body, processing every document correctly.

---

## PRIORITY 3 — CI/CD Ergonomics

### 7. New: Environment variable support for all flags (`main.py`)

All configuration flags now accept environment-variable fallbacks. CLI flags take precedence.

| Flag | Environment Variable | Default |
|---|---|---|
| `-s` / `--src` | `MYGURU_SRC` | _(required)_ |
| `--db` | `MYGURU_DB` | _(required)_ |
| `--llm` | `MYGURU_LLM` | `qwen2.5-coder:latest` |
| `--cle` | `MYGURU_EMBED_MODEL` | `nomic-embed-text` |
| `-u` / `--base-url` | `MYGURU_BASE_URL` | `http://127.0.0.1` |
| `-p` / `--port` | `MYGURU_PORT` | `11434` |
| `--quiet` | `MYGURU_QUIET` | unset |

**CI/CD usage example (GitHub Actions, Dockerfile, etc.):**
```bash
# Set in environment; no CLI flags needed
export MYGURU_SRC=/workspace/src
export MYGURU_DB=/workspace/guru-db
export MYGURU_QUIET=1
export MYGURU_BASE_URL=http://ollama-service

myguru learning -c -ea __pycache__
myguru guru -q "Summarize this codebase." --json
```

---

### 8. New: `--quiet` flag (`main.py`, `logger.py`)

`--quiet` (or `MYGURU_QUIET=1`) suppresses all INFO-level log output. Warnings and errors remain visible on stderr.

**Usage:**
```bash
# Suppress INFO logs globally (flag must come before the subcommand)
myguru --quiet -s src --db db learning -c
myguru --quiet -s src --db db guru -q "..."
```

**Important:** `--quiet` is a global flag and must appear **before** the subcommand name (`learning` or `guru`). Placing it after the subcommand will cause an argument error.

---

## PRIORITY 4 — Cleanup

### 9. Removed: Three unused dependencies (`pyproject.toml`)

`pyyaml`, `humanfriendly`, and `importlib_resources` were declared as dependencies but never imported in any source file. They have been removed. Run `pip install -e .` to update your local environment.

---

### 10. Fixed: `write_hash_file` had no error handling (`utils.py`)

File write failures now raise `OSError` with a clear message:
```
Failed to write hash file '/path/to/file': [Errno 13] Permission denied
```
This is caught and logged by the callers in `RAGBuilder`.

---

### 11. Fixed: Redundant exception types in `except` clauses

`except (TypeError, ConnectionError, Exception)` and similar patterns where specific subtypes were listed alongside the catch-all `Exception` have been simplified to `except Exception`. Behavior is identical; the code now accurately reflects that all exceptions are handled the same way.

---

## Logger behavior changes

Two cross-cutting logger changes apply globally:

| Change | Before | After |
|---|---|---|
| Output stream | `sys.stdout` | `sys.stderr` |
| Handler deduplication | Not guarded (multiple `Logger()` instances could install duplicate handlers) | Guarded: handlers installed only once per process |

**What this means for you:** Log output (INFO, WARNING, ERROR lines) now goes to **stderr**. Program output (JSON responses in `-q --json` mode, REPL responses) goes to **stdout**. This is the standard UNIX convention and makes it easy to capture just the response in scripts:

```bash
# Capture JSON response; discard logs
result=$(myguru -s src --db db guru -q "my question" --json 2>/dev/null)
```

---

## Summary of breaking changes

| # | What changed | Migration |
|---|---|---|
| Exit code | `learning` now exits 0 on success (was 1) | Update any script checking `$? -ne 0` after `learning` |
| Collection name | SHA-1 hash of abs path (was last path component) | Delete existing DB, re-run `learning -c` |
| Hash file format | New `{files, meta}` structure (old flat format read-only) | Re-run `learning -c` to enable new-file detection |
| `RAGQuery` constructor | `RAGQuery(builder, index)` (was 7 positional args) | Only relevant if importing `RAGQuery` directly in custom code |
| Log stream | Logs go to stderr (was stdout) | Update log capture in any wrapper scripts |
