"""
Base class.

This class initializes all the necessary parts to run
the RAG DB builder and the RAG qwery.
"""

import sys
from llama_index.core import Settings, PromptTemplate
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
import chromadb

from myguru.cls.logger import Logger

class RAGBase:
    """RAG Base Class."""

    LOGGER = Logger()

    _IS_INIT = False

    def __init__(self, tool_name, src_path, db_path, llm, cle, base_url):
        """
        Init Base Class.
        
        Arguments:
            - tool_name (str): Tool's name
            - src_path  (str): Src path.
            - db_path   (str): ChromaDB path.
            - llm       (str): LLM model for code analysis and generation.
            - cle       (str): Embedding model.
            - base_url  (str): Ollama base url. url:port
        """
        if not self._IS_INIT:
            self.tool_name = tool_name
            self.src_path = src_path
            self.db_path = db_path
            self.llm = llm
            self.cle = cle
            self.base_url = base_url

            self.LOGGER.info(f"INIT RAG BASE || LLM: {self.llm} || EMBEDDING MODEL: {self.cle}")

            try:
                # create our model persona
                Settings.llm = Ollama(
                    model = self.llm,
                    base_url = self.base_url,
                    temperature = 0.0,
                    request_timeout=300.0,
                    system_prompt = (
                        f"You are {self.tool_name}, an expert code analyser and generator."
                        "You provide ONLY and STRICTLY answers refering to the project's context provided."
                        "When you generate code, you ALWAYS make sure the code works for the project's context provided."
                        "You ALWAYS keep in mind the project current structure and make sure not to change this structure, unless "
                        "the user's new feature requires such change."
                        "When asked for a new feature, you ALWAYS keep into consideration existing code and how to enhance for the new goal."
                        "Your 3 main rules are, 1. Understand the project's source code. 2. Provide useful insights about the project's source code."
                        "3. Generate code when requested, which is useful for the project's source code."
                    )
                )

                # configure embedding model
                Settings.embed_model = OllamaEmbedding(
                    model_name = self.cle,
                    base_url = self.base_url
                )

                # define context information
                self.qa_prompt = PromptTemplate(
                    "Context Information is below.\n"
                    "+---------------------+\n"
                    "{context_str}\n"
                    "+---------------------+\n"
                    "Given the context information, keeping and refering to existing structure, "
                    "answer the query. If the context does not contain the necessary information "
                    "to provide an answer, say: 'Can't find relevant details for this query in this project'\n"
                    "When generating code, always provide a brief summary and then the code snippet."
                    "When answering any user's quesiton, for code analysis or generation, ALWAYS provide the path to the needed file."
                    "Query: {query_str}\n"
                    "Answer: "
                )

                # init chromaDB client
                self.db_client = chromadb.PersistentClient(path = self.db_path)
                self.collection_name = self.src_path.split("/")[-1]  # get project name if path given
                self.chroma_collection = self.db_client.get_or_create_collection(name = self.collection_name)

                self._IS_INIT = True

            except (TypeError, ConnectionError, Exception) as err:
                self.LOGGER.error(err)
                sys.exit(1)

