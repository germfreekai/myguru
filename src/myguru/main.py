"""
myproject-guru

This tool has a simple goal, provide an AI personalized assistant
for your own projects. This AI assistant should be an expert on your
specific tool, project or code.

For this we are implement a chroma_db_storage for Embedding, this way
we provide persisting storage and context to the AI agent.
The used LLM models will depend on the user and their own hardware
limitations.
"""

import argparse
import os
import sys

import maginner

from myguru.cls import Logger, RAGBuilder, RAGQuery

LOGGER = Logger()


def rag_query(tool_name, args):
    """
    RAG Query operation mode.

    Execute agent in conversation mode or single-query mode.

    Arguments:
        - tool_name (str): Tool's name.
        - args      (parser.args): Parsed arguments.
    """
    if args.json and args.query is None:
        LOGGER.warning("--json has no effect without -q/--query. Running interactive mode.")

    base_url = args.base_url + ":" + args.port
    builder = RAGBuilder(tool_name, args.src, args.db, args.llm, args.cle, base_url)

    index = builder.get_index()

    query = RAGQuery(builder, index)

    query.run_query(args.debug, args.query, args.json)


def rag_builder(tool_name, args):
    """
    RAG Builder operation mode.

    Create or update a project's vector DB.

    Arguments:
        - tool_name (str): Tool's name.
        - args      (parser.args): Parsed arguments.
    """
    base_url = args.base_url + ":" + args.port
    builder = RAGBuilder(tool_name, args.src, args.db, args.llm, args.cle, base_url)

    if args.create:
        builder.setup_index(args.hash_file, args.exclude, args.exclude_all, args.exclude_ext)

    if args.update:
        builder.update_index(args.hash_file)

    sys.exit(0)


def print_banner(tool_name):
    """
    Print Banner.

    Arguments:
        - tool_name (str): Tool's name.
    """
    maginner.maginner(tool_name)


def _validate_required_args(args, parser):
    """
    Validate args that are required but accept env-var fallbacks.

    Arguments:
        - args   (argparse.Namespace): Parsed arguments.
        - parser (argparse.ArgumentParser): Parser instance for error reporting.
    """
    missing = []
    if not args.src:
        missing.append("--src / MYGURU_SRC")
    if not args.db:
        missing.append("--db / MYGURU_DB")
    if missing:
        parser.error(f"Required argument(s) not provided: {', '.join(missing)}")


def parse_args(tool_name):
    """
    Parse CLI arguments.

    All flags accept environment-variable fallbacks so myguru can run
    config-free in CI pipelines. CLI args take precedence over env vars.

    Arguments:
        - tool_name (str): Tool's name.

    Returns:
        - args (argparse.Namespace): Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description=f"{tool_name}. Your own project guru.", epilog="Happy Hacking!"
    )

    tool_options = parser.add_argument_group(f"{tool_name} options")
    tool_options.add_argument(
        "-s",
        "--src",
        type=str,
        required=False,
        default=os.environ.get("MYGURU_SRC"),
        help="Your project's src path. [env: MYGURU_SRC]",
    )
    tool_options.add_argument(
        "--db",
        type=str,
        required=False,
        default=os.environ.get("MYGURU_DB"),
        help="Chroma Vector DB path. [env: MYGURU_DB]",
    )

    model_groups = parser.add_argument_group("Used models for operations.")
    model_groups.add_argument(
        "--llm",
        type=str,
        default=os.environ.get("MYGURU_LLM", "qwen2.5-coder:latest"),
        help="LLM model for code analysis and generation. [env: MYGURU_LLM] [qwen2.5-coder:latest]",
    )
    model_groups.add_argument(
        "--cle",
        type=str,
        default=os.environ.get("MYGURU_EMBED_MODEL", "nomic-embed-text"),
        help="Context Length Encoder for vector DB generation. [env: MYGURU_EMBED_MODEL]",
    )

    ollama_options = parser.add_argument_group("Ollama options")
    ollama_options.add_argument(
        "-p",
        "--port",
        type=str,
        default=os.environ.get("MYGURU_PORT", "11434"),
        help="Ollama server port. [env: MYGURU_PORT] [11434]",
    )
    ollama_options.add_argument(
        "-u",
        "--base-url",
        type=str,
        default=os.environ.get("MYGURU_BASE_URL", "http://127.0.0.1"),
        help="Ollama base url. [env: MYGURU_BASE_URL] [http://127.0.0.1]",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=bool(os.environ.get("MYGURU_QUIET")),
        help="Suppress INFO log output; errors and warnings remain visible. [env: MYGURU_QUIET]",
    )

    subparsers = parser.add_subparsers(title="Operation Modes", dest="mode", required=True)

    rag_builder_mode = subparsers.add_parser("learning", help="Feed knowledge to the guru.")
    hash_file_options = rag_builder_mode.add_argument_group("Update  DB options.")
    mut_exc_gropu = hash_file_options.add_mutually_exclusive_group(required=True)
    mut_exc_gropu.add_argument(
        "-c", "--create", action="store_true", help="Create a project's hash file."
    )
    mut_exc_gropu.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update a project's guru. Updates hash file and DB.",
    )
    hash_file_options.add_argument(
        "-f",
        "--hash-file",
        type=str,
        default="project_hashes.json",
        help="Hashes file path. [project_hashes.json]",
    )

    exclude_options = rag_builder_mode.add_argument_group("Exclude options.")
    exclude_options.add_argument(
        "-e",
        "--exclude",
        action="append",
        help="Files or dirs to exclude from processing. [path/to/file_or_dir]",
    )
    exclude_options.add_argument(
        "-ea",
        "--exclude-all",
        action="append",
        help="Files or dirs to exclude under evey subpath. [file_or_dir] ",
    )
    exclude_options.add_argument(
        "-ee", "--exclude-ext", action="append", help="File extensions to exclude. [ext]"
    )

    rag_query_mode = subparsers.add_parser("guru", help="Wake up the guru.")
    rag_query_mode.add_argument(
        "-d", "--debug", action="store_true", help="Show processed files chunks when answering."
    )
    rag_query_mode.add_argument(
        "-q",
        "--query",
        type=str,
        default=None,
        help="Single-query mode: run one question and exit (no REPL). [env: MYGURU_QUERY]",
    )
    rag_query_mode.add_argument(
        "--json",
        action="store_true",
        help="With -q/--query: print response as structured JSON to stdout.",
    )

    args = parser.parse_args()
    _validate_required_args(args, parser)
    return args


def main():
    """Tool's main logic."""
    tool_name = sys.argv[0].split("/")[-1]

    if "-h" in sys.argv or "--help" in sys.argv:
        print_banner(tool_name)

    args = parse_args(tool_name)

    if args.quiet:
        Logger.set_quiet()

    if args.mode == "learning":
        rag_builder(tool_name, args)

    if args.mode == "guru":
        rag_query(tool_name, args)


if __name__ == "__main__":
    main()
