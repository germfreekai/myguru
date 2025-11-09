"""
RAG Query.

Query RAG agent in conversation/user mode.
"""

import sys

from myguru.cls.rag_base import RAGBase


class RAGQuery(RAGBase):
    """RAG Query Class."""

    def __init__(self, tool_name, src_path, db_path, llm, cle, base_url, index):
        """
        Init RAG Query Class.

        Arguments:
            - tool_name (str): Tool's name
            - src_path  (str): Src path.
            - db_path   (str): ChromaDB path.
            - llm       (str): LLM model for code analysis and generation.
            - cle       (str): Embedding model.
            - base_url  (str): Ollama base url. url:port
            - index     (VectorStoreIndex): Index object.
        """
        super().__init__(tool_name, src_path, db_path, llm, cle, base_url)

        self.index = index

    def run_query(self, debug):
        """
        Execute RAG agent's query.

        Arguments:
            - debug (bool): Flag to show chunk mnessages.
        """
        self.LOGGER.info("Starting Query operation ...")

        try:
            query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                text_qa_template=self.qa_prompt,
                response_mode="compact",
                response_synthesizer_mode="compact",
            )

            self.LOGGER.info("Query engine mode ...")

            while True:
                user_prompt = input("[user] > ")
                if user_prompt.lower() in ["quit", "exit"]:
                    self.LOGGER.info("Exiting user's session ...")
                    break

                response = query_engine.query(user_prompt)

                print(f"[myguru] > {response}")
                print("_" * 25)

                if debug:
                    self.LOGGER.warning("Retrieved context chunks ...")
                    for i, node in enumerate(response.source_nodes):
                        print(f"Chunk {i+1} (Score: {node.score:.4f}):")
                        print(f"Source: {node.metadata.get('file_path', 'N/A')}")
                        print(node.get_content().strip())
                        print("--------------------------------")
        except (TimeoutError, Exception) as err:
            self.LOGGER.error(err)
            sys.exit(1)
