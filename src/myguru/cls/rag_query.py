"""
RAG Query.

Query RAG agent in conversation/user mode.
"""

import time
import sys

from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.retrievers import VectorIndexRetriever

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
            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=5)
            synthesizer = CompactAndRefine(
                text_qa_template=self.qa_prompt,
                verbose=debug,
            )

            while True:
                user_prompt = input("[user] > ")
                if user_prompt.lower() in ["quit", "exit"]:
                    self.LOGGER.info("Exiting user's session ...")
                    break

                self.LOGGER.info("Retrieving context from ChromaDB ...")
                start = time.time()
                nodes = retriever.retrieve(user_prompt)
                elapsed = time.time() - start
                self.LOGGER.info(f"Retrieved {len(nodes)} context chunks in {elapsed:.1f}s")

                self.LOGGER.info(f"Sending to LLM ({self.llm}) at {self.base_url} (timeout 300s) ...")
                start = time.time()
                response = synthesizer.synthesize(user_prompt, nodes=nodes)
                elapsed = time.time() - start
                self.LOGGER.info(f"LLM responded in {elapsed:.1f}s")

                print(f"[myguru] > {response}")
                print("_" * 25)

                if debug:
                    self.LOGGER.warning("Retrieved context chunks ...")
                    for i, node in enumerate(nodes):
                        print(f"Chunk {i+1} (Score: {node.score:.4f}):")
                        print(f"Source: {node.metadata.get('file_path', 'N/A')}")
                        print(node.get_content().strip())
                        print("--------------------------------")
        except (TimeoutError, Exception) as err:
            self.LOGGER.error(f"Query failed: {err}")
            self.LOGGER.error(f"Check if Ollama is reachable at {self.base_url} and the model '{self.llm}' is pulled")
            sys.exit(1)
