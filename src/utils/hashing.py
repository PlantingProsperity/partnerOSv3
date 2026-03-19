import hashlib
from pathlib import Path

def get_file_hash(file_path: Path) -> str:
    """
    Computes the SHA-256 hash of a file for deduplication.
    Reads in 64kb chunks to handle large files (like audio/video) efficiently.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 64K
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest()
