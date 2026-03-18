import os
from pathlib import Path

# ── Directories ───────────────────────────────────────────────────────────────
directories = [
    "data/backups",
    "deals",
    "knowledge/pinneo",
    "knowledge/ccim",
    "knowledge/reference",
    "knowledge/outcomes",
    "staging/inbox/lists",
    "staging/inbox/unresolved",
    "src/brain",
    "src/graph/nodes",
    "src/firehouse",
    "src/database/migrations",
    "src/integrations",
    "src/ui/pages",
    "src/utils",
    "tests",
    "scripts",
]

def create_scaffold(base_path: Path):
    print(f"Scaffolding Partner OS v3.2 in: {base_path}")
    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  [+] Created: {directory}")
    print("Scaffold complete.")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.resolve()
    create_scaffold(BASE_DIR)
