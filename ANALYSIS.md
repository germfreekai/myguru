# myguru — Technical Analysis

> Read-only analysis pass. No code was modified.
> Date: 2026-06-30

---

## 1. Architecture Overview

`myguru` is a local CLI tool that turns any project's source tree into a queryable AI assistant. It has no server, no HTTP API, and no persistent background process — it is invoked once per session.

### Module Map

```
src/myguru/
├── main.py              # Entry point, CLI parsing, mode dispatch
├── cls/
│   ├── __init__.py      # Re-exports Logger, RAGBuilder, RAGQuery
│   ├── rag_base.py      # RAGBase: shared init (Ollama, ChromaDB, embeddings, prompt)
│   ├── rag_builder.py   # RAGBuilder(RAGBase): indexing and updating the vector DB
│   └── rag_query.py     # RAGQuery(RAGBase): interactive query loop
└── utils/
    ├── __init__.py      # Re-exports walk_directory, md5, write_hash_file, read_hash_file
    └── utils.py         # File-system helpers and MD5 hashing
```

**Inheritance:** `RAGBase` ← `RAGBuilder`, `RAGBase` ← `RAGQuery`. Both subclasses share initialization logic (Ollama LLM, embedding model, ChromaDB client) through `RAGBase.__init__`.

### Data Flow — Indexing (`learning` mode)

```
myguru -s <src> --db <db> learning -c
         │
         ▼
    main() → rag_builder()
         │
         ▼
    RAGBuilder.__init__
    └── RAGBase.__init__
        ├── Ollama(model, base_url) → Settings.llm
        ├── OllamaEmbedding(model, base_url) → Settings.embed_model
        └── chromadb.PersistentClient(db_path) → chroma_collection
         │
         ▼
    RAGBuilder.setup_index()
    ├── walk_directory(src_path, excludes) → list[file_paths]
    ├── FlatReader().load_data(file) per file → Documents
    │   └── prepends "File Path: <path>\n\n" to each doc's content
    ├── VectorStoreIndex.from_documents(docs, storage_context)
    │   └── LlamaIndex embeds each doc via OllamaEmbedding
    │       └── Vectors stored in ChromaDB (on disk)
    └── _create_project_hash_file() → project_hashes.json
        └── md5(file) for every indexed file
```

### Data Flow — Querying (`guru` mode)

```
myguru -s <src> --db <db> guru
         │
         ▼
    main() → rag_query()
         │
         ▼
    RAGBuilder.__init__ (initializes shared state — Ollama, ChromaDB, embedding)
    RAGBuilder.get_index()
    └── VectorStoreIndex.from_vector_store(chroma_vector_store) → index
         │
         ▼
    RAGQuery.__init__ (RAGBase.__init__ is SKIPPED due to _IS_INIT singleton)
    └── stores index
         │
         ▼
    RAGQuery.run_query()
    └── index.as_query_engine(similarity_top_k=5, text_qa_template=qa_prompt)
        │
        └── [interactive loop]
            ├── input("[user] > ") → user_prompt
            ├── query_engine.query(user_prompt)
            │   ├── OllamaEmbedding.embed(user_prompt) → query vector
            │   ├── ChromaDB ANN search → top-5 document chunks
            │   └── Ollama LLM generates answer from chunks + prompt template
            └── print("[myguru] > {response}")
```

---

## 2. Dependencies & Libraries

All dependencies are declared in `pyproject.toml` with minimum version pins (no upper bounds, no exact pins).

| Package | Version Constraint | Purpose |
|---|---|---|
| `chromadb` | `>=1.3.3` | Vector database — stores and retrieves embeddings |
| `llama-index-vector-stores-chroma` | `>=0.5.3` | LlamaIndex adapter for ChromaDB |
| `llama-index-embeddings-ollama` | `>=0.8.3` | Ollama embedding model integration for LlamaIndex |
| `llama-index-llms-ollama` | `>=0.9.0` | Ollama LLM integration for LlamaIndex |
| `llama-index-readers-file` | `>=0.5.4` | `FlatReader` — reads source files as LlamaIndex Documents |
| `coloredlogs` | `>=15.0.1` | Colored terminal log output |
| `maginner` | `>=0.1` | ASCII banner display (used in `main.py` for `-h` flag) |
| `pyyaml` | `>=6.0.2` | **Not used anywhere in source code** (unused dependency) |
| `humanfriendly` | `>=10.0` | **Not used anywhere in source code** (unused dependency) |
| `importlib_resources` | `>=6.5.2` | **Not used anywhere in source code** (unused dependency) |

**Note:** LlamaIndex `core` is pulled in transitively by the llama-index-* packages above — it is used directly (`VectorStoreIndex`, `PromptTemplate`, `Settings`, `StorageContext`) but is not explicitly declared as a dependency.

---

## 3. ChromaDB / RAG Implementation

### How files are chunked and embedded

`FlatReader` (from `llama-index-readers-file`) is used as the document loader. It reads each file as a single flat document — **there is no chunking**. LlamaIndex's default text splitter then divides each document into chunks during `VectorStoreIndex.from_documents()`. The default LlamaIndex chunk size is 1024 tokens with a 20-token overlap (configurable in LlamaIndex's `Settings`, but not exposed via myguru's CLI).

Each document has its content prepended with `"File Path: <path>\n\n"` and `doc_id` set to the file path, enabling source attribution in query responses.

### Embedding model

Default: **`nomic-embed-text`** — a text embedding model served locally by Ollama.
Configurable via the `--cle` flag at runtime.

### Vector DB persistence

**Disk-persisted.** `chromadb.PersistentClient(path=self.db_path)` is used, not `EphemeralClient`. The DB is stored at the path provided via `--db` on every invocation.

The ChromaDB collection name is derived by taking the **last path component of `--src`**:

```python
self.collection_name = self.src_path.split("/")[-1]
```

For example, `--src /home/user/myproject/src` → collection name `src`. This is fragile (see Known Issues).

### Incremental re-indexing vs. full rebuild

**Both are supported, controlled by the user:**

- **`learning -c` (create):** Full build. Checks `chroma_collection.count() == 0` first — refuses to run if the DB already has data and exits with an error. After indexing, writes `project_hashes.json` (MD5 of every indexed file).
- **`learning -u` (update):** Incremental. Reads `project_hashes.json`, recomputes MD5 for each tracked file, collects files where the hash changed, deletes their old vector entries, and inserts fresh embeddings. Only changed files are re-processed. The hash file is updated afterward.

**Limitation:** The update mode only tracks files that existed at create time. New files added to the project after initial indexing are **not** detected or added automatically.

---

## 4. Ollama Integration

### Models

| Parameter | Default | CLI Flag |
|---|---|---|
| LLM (generation) | `qwen2.5-coder:latest` | `--llm` |
| Embedding model | `nomic-embed-text` | `--cle` |

Both models must already be pulled locally in Ollama (`ollama pull <model>`). myguru does not manage model downloads.

### Connection configuration

| Parameter | Default | CLI Flag |
|---|---|---|
| Base URL | `http://127.0.0.1` | `-u` / `--base-url` |
| Port | `11434` | `-p` / `--port` |

The final URL is constructed as: `base_url + ":" + port` (e.g., `http://127.0.0.1:11434`).

### Hardcoded LLM parameters

These values are set in `rag_base.py` and are **not exposed via CLI**:

```python
temperature=0.0        # deterministic output
request_timeout=300.0  # 5-minute timeout per request
```

The system prompt is also hardcoded in `rag_base.py:54-69`.

### Query engine parameters

Set in `rag_query.py` and **not exposed via CLI**:

```python
similarity_top_k=5      # retrieve top-5 most similar chunks
response_mode="compact" # condense retrieved chunks before sending to LLM
```

---

## 5. Entry Points

### Installed CLI command

```
myguru   →   myguru.main:main   (declared in pyproject.toml [project.scripts])
```

After `pip install .`, the `myguru` binary is available on `$PATH`.

### Operation modes (subcommands)

```bash
# Index a project from scratch
myguru -s <src_path> --db <db_path> learning -c \
    [-f project_hashes.json] \
    [-e path/to/exclude] \
    [-ea dir_to_exclude_everywhere] \
    [-ee ext_to_exclude]

# Incrementally update an existing index
myguru -s <src_path> --db <db_path> learning -u [-f project_hashes.json]

# Start interactive query session
myguru -s <src_path> --db <db_path> guru [-d]
```

### Typical workflow

```bash
# 1. Index
myguru -s src/ --db myproject-db learning -c -ea __pycache__ -ee pyc

# 2. Query (interactive REPL, exit with 'quit' or 'exit')
myguru -s src/ --db myproject-db guru

# 3. After code changes, update index
myguru -s src/ --db myproject-db learning -u
```

---

## 6. Configuration

**There is no config file, no `.env` file, and no environment variable support.** All configuration is passed as CLI arguments on every invocation.

| Setting | How configured | Default |
|---|---|---|
| Source path | `--src` (required) | — |
| ChromaDB path | `--db` (required) | — |
| LLM model | `--llm` | `qwen2.5-coder:latest` |
| Embedding model | `--cle` | `nomic-embed-text` |
| Ollama base URL | `--base-url` | `http://127.0.0.1` |
| Ollama port | `--port` | `11434` |
| Hash file path | `--hash-file` | `project_hashes.json` |
| Temperature | hardcoded | `0.0` |
| Request timeout | hardcoded | `300.0` |
| Similarity top-k | hardcoded | `5` |

---

## 7. Known Issues and Rough Edges

### Critical for CI/CD

**1. `sys.exit(1)` on successful indexing (`main.py:63`)**

```python
def rag_builder(tool_name, args):
    ...
    if args.create:
        builder.setup_index(...)
    if args.update:
        builder.update_index(...)
    sys.exit(1)   # ← always exits with failure code, even on success
```

Exit code `1` signals failure to every CI system. A successful `learning` run will fail any CI pipeline step checking `$?`. This needs to be `sys.exit(0)`.

---

### Design Issues

**2. Class-level `_IS_INIT` singleton (`rag_base.py:23`)**

```python
class RAGBase:
    _IS_INIT = False   # class variable, shared across ALL instances
```

This is a manual singleton guard. When `rag_query()` in `main.py` creates a `RAGBuilder` first and then a `RAGQuery`, the second `RAGBase.__init__` call is skipped entirely because `_IS_INIT` is already `True`. The current call order happens to work, but:
- Any test that creates two instances in one process will malfunction.
- Any future refactor that changes instantiation order will produce silent bugs.
- The pattern is surprising and undocumented.

**3. `update_index()` only tracks files present at create time (`rag_builder.py:128`)**

Files added to the project after the initial `learning -c` run are never discovered or indexed by `learning -u`. There is no directory walk in the update path — it only rehashes the files already in `project_hashes.json`.

**4. Collection name derived from last path component of `--src` (`rag_base.py:94`)**

```python
self.collection_name = self.src_path.split("/")[-1]
```

- `--src src/` → collection name `src`
- `--src .` → collection name `.`
- Two different projects with the same final directory name share a collection name and will collide in the same ChromaDB instance.

Using `os.path.abspath` + a hash or a full sanitized path would be safer.

---

### Exception Handling

**5. `write_hash_file` has no error handling (`utils.py:31`)**

Every other function in `utils.py` raises or catches exceptions, but `write_hash_file` has no `try/except`. A permission error writing the hash file would produce an unhandled traceback.

**6. Redundant exception types alongside `Exception` (`rag_base.py:103`, `rag_builder.py:77`, etc.)**

```python
except (TypeError, ConnectionError, Exception) as err:
```

`TypeError` and `ConnectionError` are subclasses of `Exception`. Listing them alongside `Exception` is redundant — all are handled identically. This makes the intent (differentiating error types) misleading since no differentiated handling is performed.

**7. `update_index()` uses `doc` after the inner loop (`rag_builder.py:157-163`)**

```python
for doc in docs:
    ...

# doc here refers to the LAST document yielded by FlatReader
index.delete_ref_doc(doc.doc_id, ...)
index.insert(doc)
```

`FlatReader` returns one document per file in practice, so this works. But if it ever returns multiple documents (e.g., for a multi-stream file), only the final document is re-indexed, silently dropping the others.

---

### Missing Features / Quality Gaps

**8. No test suite**

There is no `tests/` directory and no test files anywhere in the project. No unit tests, no integration tests.

**9. Three unused dependencies**

`pyyaml`, `humanfriendly`, and `importlib_resources` are declared in `pyproject.toml` but are not imported anywhere in the source. They bloat the install unnecessarily.

**10. No type annotations on function signatures**

Type information exists only in docstring `Args:` sections, not as Python type hints (`:` and `->` annotations). `mypy` or `pyright` cannot statically check this code.

**11. No input validation on user query**

In `run_query()`, `user_prompt` is passed directly to `query_engine.query()` with no length check, sanitization, or filtering. For a local dev tool this is low-risk, but worth noting for any future networked deployment.

**12. LLM parameters not configurable without code changes**

`temperature`, `request_timeout`, `similarity_top_k`, and the system prompt are hardcoded. For CI/CD or scripted use, there is no way to tune these without editing source.

**13. No structured output or machine-readable exit on query**

`run_query()` prints to stdout via `print()` in a human-readable format. There is no JSON output mode, no way to pipe a single query and get a clean answer — the interactive REPL format (`[user] >`, `[myguru] >`) makes scripting difficult.

---

## Summary Table

| Area | Status |
|---|---|
| Architecture | Clean, simple, well-structured for a v0.1 tool |
| ChromaDB persistence | Disk-persisted, works correctly |
| Incremental update | Implemented via MD5, but new files not detected |
| Ollama integration | Fully configurable model/host/port via CLI |
| CI/CD readiness | Blocked by `sys.exit(1)` on success |
| Test coverage | None |
| Type hints | Absent from function signatures |
| Config management | CLI-only, no env vars, no config file |
| Unused dependencies | 3 packages unused (`pyyaml`, `humanfriendly`, `importlib_resources`) |
| Error handling | Mostly present; `write_hash_file` uncovered; exception specificity misleading |
