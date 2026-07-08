# myguru

**myguru is a terminal application** — you interact with it entirely from the command line, not in a browser.

It is your personal project expert AI assistant that knows everything about your own project. It helps you understand how your project works and answers questions directly in your terminal.

## Dependencies
Ollama and ChromeDb for Vector Databases.

## How to run?
Running with a python environment is recommended.
- Installation
```bash
$ git clone https://github.com/germfreekai/myguru.git
$ cd myguru
$ python3 -m venv env
$ source env/bin/activate
$ pip install .
```
- Run everywhere
```bash
$ deactivate
$ readlink -f env/bin/myguru   # copy this stdout (e.g /home/user/myguru/env/bin/myguru)
$ cd ~/.local/bin/
$ ln -s /home/user/myguru/env/bin/myguru myguru
$ cd
```
> Source your terminal file and now it should available everywhere.

## Configuration via `.env`

All CLI options can also be set via environment variables in a `.env` file. The `.env` file is loaded automatically when you run `myguru` from the project root. Values in `.env` are overridden by any corresponding CLI flags, giving you a layered configuration:

**CLI flag > `MYGURU_LLM_HOST` / `MYGURU_CLE_HOST` env var > `--base-url`/`--port` CLI flag > `MYGURU_BASE_URL`/`MYGURU_PORT` env var > built-in default**

### Available environment variables

| Variable | Required | Description |
|---|---|---|
| `MYGURU_SRC` | Yes | Path to your project's source directory |
| `MYGURU_DB` | Yes | Path to the Chroma Vector DB directory, or full URL for remote ChromaDB (e.g. `https://chromadb.example.com`) |
| `MYGURU_LLM` | No | LLM model (default: `qwen2.5-coder:latest`) |
| `MYGURU_CLE` | No | Embedding model (default: `nomic-embed-text`) |
| `MYGURU_PORT` | No | Ollama port (default: `11434`) |
| `MYGURU_BASE_URL` | No | Ollama base URL without port (default: `http://127.0.0.1`) |
| `MYGURU_LLM_HOST` | No | Full Ollama server URL — overrides `MYGURU_BASE_URL` and `MYGURU_PORT` when set (e.g. `http://192.168.1.100:11434`) |
| `MYGURU_CLE_HOST` | No | Full URL for the embedding model host, if different from the LLM host (e.g. `http://192.168.1.101:11434`) |
| `MYGURU_HASH_FILE` | No | Hash file path (default: `project_hashes.json`) |
| `MYGURU_EXCLUDE` | No | Comma-separated files/dirs to exclude |
| `MYGURU_EXCLUDE_ALL` | No | Comma-separated names to exclude under every subpath |
| `MYGURU_EXCLUDE_EXT` | No | Comma-separated file extensions to exclude |

### Example `.env`

```bash
# Create a .env file in the project root
$ cat .env
MYGURU_SRC=./src
MYGURU_DB=https://chromadb.example.com   # or a local path like ./myguru-db
MYGURU_LLM=qwen2.5-coder:latest
MYGURU_CLE=nomic-embed-text
MYGURU_PORT=11434
MYGURU_BASE_URL=http://127.0.0.1
# MYGURU_LLM_HOST=http://192.168.1.100:11434
# MYGURU_CLE_HOST=http://192.168.1.100:11434
MYGURU_HASH_FILE=project_hashes.json
# MYGURU_EXCLUDE=__pycache__,node_modules
# MYGURU_EXCLUDE_ALL=.gitkeep
# MYGURU_EXCLUDE_EXT=.egg-info
```

### Starting the app with `.env`

Once the `.env` file is in place in the project root, simply run `myguru` as usual — the variables are loaded automatically. You can omit any CLI flags that are already set in `.env`:

```bash
# Without .env (full CLI):
$ myguru -s src --db myguru-db learning -c

# With .env (shorter CLI):
$ myguru learning -c

# With .env + MYGURU_LLM_HOST set (no need for --base-url or --port):
$ myguru -s src --db myguru-db guru
```

You can also mix and match — CLI flags always take precedence:

```bash
# Override just the model from .env:
$ myguru --llm llama3.2:latest guru
```

## Usage

myguru runs entirely in **your terminal** — no browser, no web UI. It has two modes. All flags below can be set once via `.env` and omitted from CLI thereafter.

### 1. `learning` — Index your project

Feed your project's source code into the vector database so myguru can learn it:

```bash
# Full CLI (every time):
$ myguru -s ./src --db ./myguru-db learning -c

# Or set MYGURU_SRC and MYGURU_DB in .env, then just:
$ myguru learning -c
```

- `-s, --src` — path to your source code (or `MYGURU_SRC` in `.env`)
- `--db` — where to store the vector database — local path or remote URL (or `MYGURU_DB` in `.env`)
- `-c, --create` — create a fresh index
- `-u, --update` — update an existing index
- `-e, --exclude` — exclude specific files/dirs (repeatable)
- `-ea, --exclude-all` — exclude by name in every subdirectory (repeatable)
- `-ee, --exclude-ext` — exclude by extension (repeatable)

### 2. `guru` — Ask questions

Once indexed, start an interactive chat session in your terminal:

```bash
# Full CLI (every time):
$ myguru -s ./src --db ./myguru-db guru
[user] > how does authentication work?
[myguru] > Based on the project's source code, authentication is handled in ...
[user] > quit

# Or with a .env file, just:
$ myguru guru
```

- `-d, --debug` — show which source chunks were used to answer

> Type `quit` or `exit` to end the conversation.

### See all options

```bash
$ myguru --help
$ myguru learning --help
$ myguru guru --help
```
