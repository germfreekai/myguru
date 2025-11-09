"""
RAG Builder.

Create RAG DB. Handle indexing and updating operations.
"""

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.storage.storage_context import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from myguru.cls.rag_base import RAGBase
from myguru.utils import walk_directory, md5, write_hash_file, read_hash_file
from llama_index.readers.file import FlatReader
import os
import sys
from pathlib import Path

class RAGBuilder(RAGBase):
    """RAG Builder Class."""

    def __init__(self, tool_name, src_path, db_path, llm, cle, base_url):
        """
        Init RAG Builder Class.
        
        Arguments:
            - tool_name (str): Tool's name
            - src_path  (str): Src path.
            - db_path   (str): ChromaDB path.
            - llm       (str): LLM model for code analysis and generation.
            - cle       (str): Embedding model.
            - base_url  (str): Ollama base url. url:port
        """
        super().__init__(tool_name, src_path, db_path, llm, cle, base_url)

        self.vector_store = ChromaVectorStore(chroma_collection = self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store = self.vector_store)

    def setup_index(self, hash_file, exclude, exclude_all, exclude_ext):
        """
        Create persistent VectorStoreIndex.

        Arguments:
            - hash_file   (str): Hash File path.
            - exclude     (list): List of files or directories to exclude.
            - exclude_all (list): List of files or directories to exclude in all subpaths.
            - exclude_ext (list): List of extensions to exclude in all subpaths.

        """
        if self.chroma_collection.count() == 0:
            self.LOGGER.info(f"Starting indexing || src: {self.src_path} || DB: {self.db_path} ...")

            all_files = []
            all_documents = []

            text_parser = FlatReader()

            # walk src
            try:
                all_files.extend(walk_directory(self.src_path, exclude, exclude_all, exclude_ext))
                for file in all_files:
                    self.LOGGER.info(f"Parsing file: {file} ...")

                    file_path_obj = Path(file)
                    docs = text_parser.load_data(file = file_path_obj)

                    for doc in docs:
                        doc.metadata['file_path'] = file
                        doc.doc_id = doc.metadata['file_path']
                        doc.set_content(f"File Path: {doc.doc_id}\n\n{doc.text}")
                        all_documents.append(doc)

                _ = VectorStoreIndex.from_documents(
                    all_documents,
                    storage_context = self.storage_context
                )
            except (FileNotFoundError, PermissionError, Exception) as err:
                self.LOGGER.error(err)
                sys.exit(1)
            self.LOGGER.info("Indexing completed! ...")
            self._create_project_hash_file(hash_file, all_files)
        else:
            self.LOGGER.error("DB already exists, use update operation.")
            sys.exit(0)


    def _create_project_hash_file(self, hash_file, all_files):
        """
        Create project's hash file.
        
        Creates a md5 hash file with current project's files status.
        This will be usefull to furhter update the changed files.
        
        Arguments:
            - hash_file (str): Hash File path.
            - all_files (list): List of indexed files.
        """
        self.LOGGER.info(f"Creating hash file: {hash_file} ...")
        hashes = {}
        try:
            for file in all_files:
               if file == os.path.normpath(hash_file):
                  continue
               hash = md5(file)
               hashes[file] = hash
            write_hash_file(hash_file, hashes)
        except (FileNotFoundError, PermissionError, Exception) as err:
            self.LOGGER.error(err)
            sys.exit(1)


    def get_index(self):
        """
        Retrieve VectorStoreIndex index.
        
        Returns:
            - index (VectorStoreIndex): Index object.
        """
        self.LOGGER.info(f"Loading existing Vector Index from disk: {self.db_path} ...")

        try:
            index = VectorStoreIndex.from_vector_store(
                vector_store = self.vector_store,
            )
            return index
        except (FileNotFoundError, PermissionError, Exception) as err:
            self.LOGGER.error(err)
            sys.exit(1)


    def update_index(self, hash_file):
        """
        Update persistent VectorStoreIndex.
        
        Use hash file to figure out whhich files where updated.
        Upated VectorStoreIndex and hash file.
        
        Arguments:
            - hash_file   (str): Hash File path.
        """
        update_files = self._update_project_hash_file(hash_file)
        if len(update_files) == 0:
            self.LOGGER.info("Nothing to update ...")
            sys.exit(0)
        
        index = self.get_index()
        text_parser = FlatReader()

        for file in update_files:
            file_path_obj = Path(file)
            docs = text_parser.load_data(file = file_path_obj)

            for doc in docs:
                doc.metadata['file_path'] = file
                doc.doc_id = doc.metadata['file_path']
                doc.set_content(f"File Path: {doc.doc_id}\n\n{doc.text}")
            
            self.LOGGER.info(f"Updating index for file: {file} ...")

            self.LOGGER.info(f"Deleting old index.")
            index.delete_ref_doc(doc.doc_id, delete_from_docstore=True)
            self.LOGGER.info(f"Deletion successful.")

            self.LOGGER.info("Insert new version.")
            index.insert(doc)

            index.storage_context.persist(self.db_path)

            self.LOGGER.info("Successfull Update.")
            
    
    def _update_project_hash_file(self, hash_file):
        """
        Update project's hash file.
        
        Get list of files to update indexing.
        
        Arguments:
            - hash_file (str): Hash file path.
        
        Returns:
            - update_files (list): List of file paths to update indexing.
        """
        try:
            hashes = read_hash_file(hash_file)
            new_hashes = {}
            update_files = []

            if len(hashes) == 0:
                self.LOGGER.error(f"Hash file {hash_file} is empty, use create operation.")
                sys.exit(1)

            review_files = [file_path for file_path, _ in hashes.items()]
            for file in review_files:
                new_hash = md5(file)
                if new_hash != hashes[file]:
                    update_files.append(file)
                new_hashes[file] = new_hash

            if len(update_files) != 0:
                self.LOGGER.info(f"Updating hash file: {hash_file} ...")
                write_hash_file(hash_file, new_hashes)

            return update_files
        except Exception as err:
            self.LOGGER.error(err)
            sys.exit(1)