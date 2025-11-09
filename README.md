# myguru
---
myguru is your personal project expert. This AI assistant knows everything about your own project.

This guru goal is to assist you understanding how is your project working and answer any question based on your own project, directly from the terminal.

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
- Options
```
$ myguru -h
 __  __  _    _  ______  __   __  ______  __   __
|  \/  |\ \  / /|  ____||  | |  ||      ||  | |  |
|      | \ \/ / | | ___ |  | |  ||    ▄ ||  | |  |
| |\/| |  \  /  | ||_  ||  | |  ||    __||  | |  |
| |  | |  / /   | |__| ||  |_|  || |\ \  |  |_|  |
|_|  |_| /_/    |______||_______||_| \_\ |_______|
usage: myguru [-h] -s SRC --db DB [--llm LLM] [--cle CLE] [-p PORT] [-u BASE_URL] {learning,guru} ...

myguru. Your own project guru.

options:
  -h, --help            show this help message and exit

myguru options:
  -s SRC, --src SRC     Your project's src path.
  --db DB               Chroma Vector DB path.

Used models for operations.:
  --llm LLM             LLM model for code analysis and generation. [qwen2.5-coder:latest]
  --cle CLE             Context Length Encoder for vector DB generation. [nomic-embed-text]

Ollama options:
  -p PORT, --port PORT  Ollama server port. [11434]
  -u BASE_URL, --base-url BASE_URL
                        Ollama base url. [http://127.0.0.1]

Operation Modes:
  {learning,guru}
    learning            Feed knowledge to the guru.
    guru                Wake up the guru.

Happy Hacking!

$ myguru learning -h
 __  __  _    _  ______  __   __  ______  __   __
|  \/  |\ \  / /|  ____||  | |  ||      ||  | |  |
|      | \ \/ / | | ___ |  | |  ||    ▄ ||  | |  |
| |\/| |  \  /  | ||_  ||  | |  ||    __||  | |  |
| |  | |  / /   | |__| ||  |_|  || |\ \  |  |_|  |
|_|  |_| /_/    |______||_______||_| \_\ |_______|
usage: myguru learning [-h] (-c | -u) [-f HASH_FILE] [-e EXCLUDE] [-ea EXCLUDE_ALL] [-ee EXCLUDE_EXT]

options:
  -h, --help            show this help message and exit

Update  DB options.:
  -c, --create          Create a project's hash file.
  -u, --update          Update a project's guru. Updates hash file and DB.
  -f HASH_FILE, --hash-file HASH_FILE
                        Hashes file path. [project_hashes.json]

Exclude options.:
  -e EXCLUDE, --exclude EXCLUDE
                        Files or dirs to exclude from processing. [path/to/file_or_dir]
  -ea EXCLUDE_ALL, --exclude-all EXCLUDE_ALL
                        Files or dirs to exclude under evey subpath. [file_or_dir]
  -ee EXCLUDE_EXT, --exclude-ext EXCLUDE_EXT
                        File extensions to exclude. [ext]

$ myguru guru -h
 __  __  _    _  ______  __   __  ______  __   __
|  \/  |\ \  / /|  ____||  | |  ||      ||  | |  |
|      | \ \/ / | | ___ |  | |  ||    ▄ ||  | |  |
| |\/| |  \  /  | ||_  ||  | |  ||    __||  | |  |
| |  | |  / /   | |__| ||  |_|  || |\ \  |  |_|  |
|_|  |_| /_/    |______||_______||_| \_\ |_______|
usage: myguru guru [-h] [-d]

options:
  -h, --help   show this help message and exit
  -d, --debug  Show processed files chunks when answering.
```
- Make your guru learn your project, exclude unnecessary files or dirs
```
$ myguru -s src --db clisnap-db learning -c -ea __pycache__ -ea .gitkeep -ee src/clisnap.egg-info
2025-11-09 20:16 - INFO : INIT RAG BASE || LLM: qwen2.5-coder:latest || EMBEDDING MODEL: nomic-embed-text
2025-11-09 20:16 - INFO : Starting indexing || src: src || DB: clisnap-db ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/__init__.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/main.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/cls/logger.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/cls/__init__.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/cls/clisnap.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/utils/utils.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap/utils/__init__.py ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/requires.txt ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/PKG-INFO ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/dependency_links.txt ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/SOURCES.txt ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/top_level.txt ...
2025-11-09 20:16 - INFO : Parsing file: src/clisnap.egg-info/entry_points.txt ...
2025-11-09 20:16 - INFO : Indexing completed! ...
2025-11-09 20:16 - INFO : Creating hash file: project_hashes.json ...
```
- Ask your guru
```bash
$ myguru -s src --db clisnap-db guru
2025-11-09 20:18 - INFO : INIT RAG BASE || LLM: qwen2.5-coder:latest || EMBEDDING MODEL: nomic-embed-text
2025-11-09 20:18 - INFO : Loading existing Vector Index from disk: clisnap-db ...
2025-11-09 20:18 - INFO : INIT RAG BASE || LLM: qwen2.5-coder:latest || EMBEDDING MODEL: nomic-embed-text
2025-11-09 20:18 - INFO : Starting Query operation ...
2025-11-09 20:18 - INFO : Query engine mode ...
[user] > how do I write the JSON files?
[myguru] > To write JSON files in your project, you can use the `write_json_file` function from the `clisnap.utils` module. This function takes three arguments:

1. `tool`: The name of the tool for which the JSON file is being written.
2. `file_path`: The path to the JSON file.
3. `data`: The data to be written to the JSON file, typically a dictionary.

Here's an example of how you can use this function in your code:

from clisnap.utils import write_json_file

# Example data to be written to the JSON file
cmds = {
    1: {"cmd": "ls", "description": "List directory contents"},
    2: {"cmd": "pwd", "description": "Print current working directory"}
}

# Write the data to a JSON file
write_json_file("example_tool", "/path/to/example_tool.json", cmds)

This will create or overwrite the `example_tool.json` file in the specified path with the provided data.
[user] > quit
2025-11-09 20:21 - INFO : Exiting user's session ...
```
