"""
Base class.

This class initializes all the necessary parts to run
the RAG DB builder and the RAG qwery.
"""

import hashlib
import os
import sys

import chromadb
from llama_index.core import PromptTemplate, Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from myguru.cls.logger import Logger


class RAGBase:
    """RAG Base Class."""

    LOGGER = Logger()

    SYSTEM_PROMPT = (
        "You are {tool_name}, an expert code analyser and generator."
        "You provide ONLY and STRICTLY answers refering to the project's "
        "context provided."
        "When you generate code, you ALWAYS make sure the code works for the "
        "project's context provided."
        "You ALWAYS keep in mind the project current structure and make sure "
        "not to change this structure, unless "
        "the user's new feature requires such change."
        "When asked for a new feature, you ALWAYS keep into consideration existing "
        "code and how to enhance for the new goal."
        "Your 3 main rules are, 1. Understand the project's source code. "
        "2. Provide useful insights about the project's source code."
        "3. Generate code when requested, which is useful for the project's "
        "source code."
    )

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
        self.tool_name = tool_name
        self.src_path = src_path
        self.db_path = db_path
        self.llm = llm
        self.cle = cle
        self.base_url = base_url

        cle_host = os.getenv("MYGURU_CLE_HOST")
        self.cle_base_url = cle_host.rstrip("/") if cle_host else self.base_url

        self.LOGGER.info(
            f"INIT RAG BASE || LLM: {self.llm} || LLM HOST: {self.base_url}"
            f" || EMBEDDING MODEL: {self.cle} || EMBEDDING HOST: {self.cle_base_url}"
        )

        try:
            # create our model persona
            Settings.llm = Ollama(
                model=self.llm,
                base_url=self.base_url,
                temperature=0.0,
                request_timeout=300.0,
                system_prompt=self.SYSTEM_PROMPT.format(tool_name=self.tool_name),
            )

            # configure embedding model (separate host if MYGURU_CLE_HOST is set)
            Settings.embed_model = OllamaEmbedding(model_name=self.cle, base_url=self.cle_base_url)

            # define context information
            self.qa_prompt = PromptTemplate(
                "Context Information is below.\n"
                "+---------------------+\n"
                "{context_str}\n"
                "+---------------------+\n"
                "Given the context information, keeping and refering to existing structure, "
                "answer the query. If the context does not contain the necessary information "
                "to provide an answer, say: 'Can't find relevant details for this query in "
                "this project'\n"
                "When generating code always provide a brief summary and then the code snippet."
                "When answering any user's quesiton, for code analysis or generation, ALWAYS "
                "provide the path to the needed file."
                "Query: {query_str}\n"
                "Answer: "
            )

            # init chromaDB client
            self.db_client = chromadb.PersistentClient(path=self.db_path)
            abs_src = os.path.abspath(src_path)
            self.collection_name = hashlib.sha1(abs_src.encode()).hexdigest()
            self.chroma_collection = self.db_client.get_or_create_collection(
                name=self.collection_name
            )

        except Exception as err:
            self.LOGGER.error(err)
            sys.exit(1)
