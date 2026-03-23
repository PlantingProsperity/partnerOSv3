import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env before imports that might rely on it
load_dotenv()

# Force unbuffered output so we see logs immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from src.graph.nodes.librarian import Librarian
from src.utils.logger import get_logger

log = get_logger("audio_script")

try:
    lib = Librarian()
    files = list(Path("staging/inbox").glob("*.m4a"))
    log.info("found_files", count=len(files))
    
    for f in files:
        log.info("starting_standalone_transcription", file=f.name)
        lib._transcribe_audio(f)
        
except Exception as e:
    log.error("script_crashed", error=str(e))
