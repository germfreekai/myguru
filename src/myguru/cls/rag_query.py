"""
RAG Query.

Query RAG agent in conversation/user mode. Uses composition: receives an
initialized RAGBase (or RAGBuilder) and an index rather than re-running
the shared initialization path.
"""

import json
import sys


class RAGQuery:
    """
    RAG Query Class.

    Wraps a query engine built from an existing VectorStoreIndex.
    Depends on an already-initialized RAGBase for the prompt template
    and logger; does not re-run Ollama or ChromaDB initialization.
    """

    def __init__(self, base, index):
        """
        Init RAG Query Class.

        Arguments:
            - base  (RAGBase): An initialized RAGBase (or RAGBuilder) instance.
            - index (VectorStoreIndex): Pre-loaded vector index.
        """
        self._logger = base.LOGGER
        self.qa_prompt = base.qa_prompt
        self.index = index

    def run_query(self, debug, query_text=None, json_output=False):
        """
        Execute RAG agent's query.

        When query_text is provided, runs a single non-interactive query and
        returns. Without query_text, runs an interactive REPL until the user
        types 'quit' or 'exit'.

        Arguments:
            - debug       (bool): Flag to show chunk messages in REPL mode.
            - query_text  (str):  If set, run one query and exit instead of the REPL.
            - json_output (bool): If True with query_text, print a JSON object to stdout.

        Raises:
            - SystemExit(1): On unrecoverable error.
        """
        self._logger.info("Starting Query operation ...")

        try:
            query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                text_qa_template=self.qa_prompt,
                response_mode="compact",
                response_synthesizer_mode="compact",
            )

            if query_text is not None:
                response = query_engine.query(query_text)

                if json_output:
                    sources = []
                    for node in response.source_nodes:
                        sources.append(
                            {
                                "file_path": node.metadata.get("file_path", ""),
                                "score": (
                                    round(float(node.score), 4) if node.score is not None else None
                                ),
                                "content": node.get_content().strip(),
                            }
                        )
                    payload = {
                        "query": query_text,
                        "response": str(response),
                        "sources": sources,
                    }
                    print(json.dumps(payload, indent=2))
                else:
                    print(str(response))
                return

            self._logger.info("Query engine mode ...")

            while True:
                user_prompt = input("[user] > ")
                if user_prompt.lower() in ["quit", "exit"]:
                    self._logger.info("Exiting user's session ...")
                    break

                response = query_engine.query(user_prompt)

                print(f"[myguru] > {response}")
                print("_" * 25)

                if debug:
                    self._logger.warning("Retrieved context chunks ...")
                    for i, node in enumerate(response.source_nodes):
                        print(f"Chunk {i+1} (Score: {node.score:.4f}):")
                        print(f"Source: {node.metadata.get('file_path', 'N/A')}")
                        print(node.get_content().strip())
                        print("--------------------------------")

        except Exception as err:
            self._logger.error(err)
            sys.exit(1)
