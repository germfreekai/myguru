"""
RAG Builder.

Create RAG DB. Handle indexing and updating operations.

The hash file written by this module uses the following JSON structure:
  {
    "files": { "<path>": "<md5>", ... },
    "meta":  { "src_path": "<abs-path>", "exclude": [...],
             "exclude_all": [...], "exclude_ext": [...] }
  }

Legacy hash files (flat dict of path→hash) are read transparently; new-file
detection is unavailable for those because the original exclude parameters
were not stored.
"""

import os
import sys
from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.storage.storage_context import StorageContext
from llama_index.readers.file import FlatReader
from llama_index.vector_stores.chroma import ChromaVectorStore

from myguru.cls.rag_base import RAGBase
from myguru.utils import md5, read_hash_file, walk_directory, write_hash_file


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

        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

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

            try:
                all_files.extend(walk_directory(self.src_path, exclude, exclude_all, exclude_ext))
                for file in all_files:
                    self.LOGGER.info(f"Parsing file: {file} ...")

                    file_path_obj = Path(file)
                    docs = text_parser.load_data(file=file_path_obj)

                    for doc in docs:
                        doc.metadata["file_path"] = file
                        doc.doc_id = doc.metadata["file_path"]
                        doc.set_content(f"File Path: {doc.doc_id}\n\n{doc.text}")
                        all_documents.append(doc)

                _ = VectorStoreIndex.from_documents(
                    all_documents, storage_context=self.storage_context
                )
            except Exception as err:
                self.LOGGER.error(err)
                sys.exit(1)

            self.LOGGER.info("Indexing completed! ...")
            self._create_project_hash_file(hash_file, all_files, exclude, exclude_all, exclude_ext)
        else:
            self.LOGGER.error("DB already exists, use update operation.")
            sys.exit(0)

    def _create_project_hash_file(self, hash_file, all_files, exclude, exclude_all, exclude_ext):
        """
        Create project's hash file.

        Writes an MD5 hash of every indexed file plus the exclude parameters
        used during indexing, so future update runs can apply the same filters
        when scanning for new files.

        Arguments:
            - hash_file   (str): Hash File path.
            - all_files   (list): List of indexed files.
            - exclude     (list): Path-based excludes passed to learning -c.
            - exclude_all (list): Name-based global excludes.
            - exclude_ext (list): Extension excludes.
        """
        self.LOGGER.info(f"Creating hash file: {hash_file} ...")
        hashes = {}
        try:
            for file in all_files:
                if file == os.path.normpath(hash_file):
                    continue
                hashes[file] = md5(file)

            data = {
                "files": hashes,
                "meta": {
                    "src_path": os.path.abspath(self.src_path),
                    "exclude": exclude,
                    "exclude_all": exclude_all,
                    "exclude_ext": exclude_ext,
                },
            }
            write_hash_file(hash_file, data)
        except Exception as err:
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
                vector_store=self.vector_store,
            )
            return index
        except Exception as err:
            self.LOGGER.error(err)
            sys.exit(1)

    def update_index(self, hash_file):
        """
        Update persistent VectorStoreIndex.

        Computes MD5 hashes for all tracked files and compares them to the
        stored values. Changed files are deleted from the index and re-inserted.
        New files discovered by walking the source directory (using the exclude
        parameters stored in the hash file) are inserted without a prior delete.

        Arguments:
            - hash_file (str): Hash File path.
        """
        changed_files, new_files = self._update_project_hash_file(hash_file)

        if not changed_files and not new_files:
            self.LOGGER.info("Nothing to update ...")
            sys.exit(0)

        index = self.get_index()
        text_parser = FlatReader()

        for file in changed_files:
            file_path_obj = Path(file)
            docs = text_parser.load_data(file=file_path_obj)

            for doc in docs:
                doc.metadata["file_path"] = file
                doc.doc_id = doc.metadata["file_path"]
                doc.set_content(f"File Path: {doc.doc_id}\n\n{doc.text}")

                self.LOGGER.info(f"Updating index for file: {file} ...")
                self.LOGGER.info("Deleting old index entry.")
                index.delete_ref_doc(doc.doc_id, delete_from_docstore=True)
                self.LOGGER.info("Inserting new version.")
                index.insert(doc)

        for file in new_files:
            file_path_obj = Path(file)
            docs = text_parser.load_data(file=file_path_obj)

            for doc in docs:
                doc.metadata["file_path"] = file
                doc.doc_id = doc.metadata["file_path"]
                doc.set_content(f"File Path: {doc.doc_id}\n\n{doc.text}")

                self.LOGGER.info(f"Adding new file to index: {file} ...")
                index.insert(doc)

        index.storage_context.persist(self.db_path)
        self.LOGGER.info("Update successful.")

    def _update_project_hash_file(self, hash_file):
        """
        Compute which files need to be re-indexed.

        Reads the hash file, recomputes MD5 for every tracked file, and walks
        the source directory to find files added since the last create/update.

        New-file detection uses the exclude parameters stored in the hash file
        meta block. Legacy hash files (flat path→hash dicts without a 'meta'
        key) skip new-file detection because those parameters were not recorded.

        Arguments:
            - hash_file (str): Hash file path.

        Returns:
            - changed_files (list): Files whose MD5 has changed.
            - new_files     (list): Files present in the source tree but not yet indexed.
        """
        try:
            raw = read_hash_file(hash_file)

            if "files" in raw and "meta" in raw:
                hashes = raw["files"]
                meta = raw["meta"]
                exclude = meta.get("exclude") or None
                exclude_all = meta.get("exclude_all") or None
                exclude_ext = meta.get("exclude_ext") or None
            else:
                # Legacy flat format: new-file detection unavailable
                hashes = raw
                meta = None
                exclude = exclude_all = exclude_ext = None

            if not hashes:
                self.LOGGER.error(f"Hash file {hash_file} is empty, use create operation.")
                sys.exit(1)

            new_hashes = {}
            changed_files = []

            for file_path, old_hash in hashes.items():
                new_hash = md5(file_path)
                if new_hash != old_hash:
                    changed_files.append(file_path)
                new_hashes[file_path] = new_hash

            # Detect files added to the source tree since last index/update
            new_files = []
            if meta is not None:
                walked = walk_directory(
                    self.src_path,
                    list(exclude) if exclude else None,
                    list(exclude_all) if exclude_all else None,
                    list(exclude_ext) if exclude_ext else None,
                )
                for file_path in walked:
                    if file_path not in new_hashes:
                        new_files.append(file_path)
                        new_hashes[file_path] = md5(file_path)

            if changed_files or new_files:
                self.LOGGER.info(f"Updating hash file: {hash_file} ...")
                updated_meta = (
                    meta
                    if meta is not None
                    else {
                        "src_path": os.path.abspath(self.src_path),
                        "exclude": None,
                        "exclude_all": None,
                        "exclude_ext": None,
                    }
                )
                write_hash_file(hash_file, {"files": new_hashes, "meta": updated_meta})

            return changed_files, new_files

        except Exception as err:
            self.LOGGER.error(err)
            sys.exit(1)
