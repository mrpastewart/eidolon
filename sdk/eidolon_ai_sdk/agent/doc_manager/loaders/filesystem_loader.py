import hashlib
import os
from pathlib import Path
from typing import AsyncIterator

from eidolon_ai_sdk.agent.doc_manager.loaders.base_loader import (
    DocumentLoader,
    FileInfo,
    DocumentLoaderSpec,
    FileChange,
    ModifiedFile,
    AddedFile,
    RemovedFile, LoaderMetadata,
)
from eidolon_ai_sdk.agent.doc_manager.parsers.base_parser import DataBlob
from eidolon_ai_sdk.system.specable import Specable


def hash_file(file_path, chunk_size=8192):
    """
    Hash the contents of a file using SHA-256.

    :param file_path: Path to the file to be hashed.
    :param chunk_size: Size of each chunk to read. Default is 8192 bytes.
    :return: Hexadecimal string of the hash.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as file:
        chunk = file.read(chunk_size)
        while chunk:
            hasher.update(chunk)
            chunk = file.read(chunk_size)
    return hasher.hexdigest()


class FilesystemLoaderSpec(DocumentLoaderSpec):
    root_dir: str
    pattern: str = "**/*"


# noinspection PyShadowingNames
class FilesystemLoader(DocumentLoader, Specable[FilesystemLoaderSpec]):
    def __init__(self, spec: FilesystemLoaderSpec, **kwargs: object):
        super().__init__(spec, **kwargs)
        root_dir = os.path.expanduser(os.path.expandvars(self.spec.root_dir))
        self.root_path = Path(root_dir).absolute()
        self.root_dir = str(self.root_path)
        if not self.root_path.exists():
            raise ValueError(f"Root directory {self.root_dir} does not exist")

    async def get_changes(self, metadata: LoaderMetadata) -> AsyncIterator[FileChange]:
        metadata = {doc.path: doc.metadata async for doc in metadata.doc_metadata()}
        # iterate over all python files in the root_dir
        for file in self.root_path.glob(self.spec.pattern):
            if file.is_file():
                # get the file path relative to the root_dir
                file_path = str(file.relative_to(self.root_dir))
                # first check the timestamp to see if it changed.  If not, skip the file
                timestamp = os.path.getmtime(file)
                if file_path in metadata:
                    file_metadata = metadata[file_path]
                    if "timestamp" not in file_metadata or timestamp != file_metadata["timestamp"]:
                        # create a hash of the file at file path
                        file_hash = hash_file(file)
                        # if the file exists in symbolic memory, check if the hashes are different
                        if "hash" not in file_metadata or file_hash != file_metadata:
                            new_metadata = {"timestamp": timestamp, "file_hash": file_hash}
                            yield ModifiedFile(
                                FileInfo(file_path, new_metadata, DataBlob.from_path(str(self.root_path / file_path)))
                            )
                    del metadata[file_path]
                else:
                    timestamp = os.path.getmtime(file)
                    file_hash = hash_file(file)
                    new_metadata = {"timestamp": timestamp, "file_hash": file_hash}
                    yield AddedFile(
                        FileInfo(file_path, new_metadata, DataBlob.from_path(str(self.root_path / file_path)))
                    )

        for not_found in metadata.keys():
            yield RemovedFile(not_found)
