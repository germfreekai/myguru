"""
RAG Query.

Query RAG agent in conversation/user mode.
"""

import json
import sys
import time
import urllib.request

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

    def _format_context(self, nodes):
        """Format retrieved nodes into a single context string."""
        sections = []
        for i, node in enumerate(nodes, 1):
            path = node.metadata.get("file_path", "N/A")
            content = node.get_content().strip()
            sections.append(f"--- chunk {i} ({path}) ---\n{content}")
        return "\n\n".join(sections)

    def _stream_ollama(self, prompt):
        """Stream completion directly from Ollama API."""
        system_prompt = self.SYSTEM_PROMPT.format(tool_name=self.tool_name)

        payload = json.dumps(
            {
                "model": self.llm,
                "system": system_prompt,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.0,
                    "num_thread": 24,
                },
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=600) as resp:
            for line in resp:
                if not line:
                    continue
                data = json.loads(line)
                if not data.get("done", False):
                    yield data.get("response", "")
                else:
                    yield "__DONE__"

    def run_query(self, debug):
        """
        Execute RAG agent's query.

        Arguments:
            - debug (bool): Flag to show chunk mnessages.
        """
        self.LOGGER.info("Starting Query operation ...")

        try:
            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=5)

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

                context = self._format_context(nodes)
                formatted_prompt = self.qa_prompt.format(context_str=context, query_str=user_prompt)

                self.LOGGER.info(
                    f"Sending to LLM ({self.llm}) at {self.base_url} (timeout 300s) ..."
                )
                start = time.time()
                sys.stdout.write("[myguru] > ")
                sys.stdout.flush()
                for token in self._stream_ollama(formatted_prompt):
                    if token == "__DONE__":
                        break
                    sys.stdout.write(token)
                    sys.stdout.flush()
                elapsed = time.time() - start
                print()
                print("_" * 25)
                self.LOGGER.info(f"LLM responded in {elapsed:.1f}s")

                if debug:
                    self.LOGGER.warning("Retrieved context chunks ...")
                    for i, node in enumerate(nodes):
                        print(f"Chunk {i+1} (Score: {node.score:.4f}):")
                        print(f"Source: {node.metadata.get('file_path', 'N/A')}")
                        print(node.get_content().strip())
                        print("--------------------------------")
        except (TimeoutError, Exception) as err:
            self.LOGGER.error(f"Query failed: {err}")
            self.LOGGER.error(
                f"Check if Ollama is reachable at {self.base_url}"
                f" and the model '{self.llm}' is pulled"
            )
            sys.exit(1)
