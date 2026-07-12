"""
setup_dirs.py — Create the project directory structure.

Called at the start of setup.sh. Safe to re-run: existing directories
are left untouched. More useful than .gitkeep files on a spot instance
where you're not necessarily working from a git clone.
"""

from pathlib import Path

DIRS = [
    "data",
    "vectors",
    "training",
    "tasks",
    "solvers",
    "scorers",
    "ablations",
    "logs",
    "adapters",
    "artifacts",
    "results",
]

if __name__ == "__main__":
    root = Path(__file__).parent
    for d in DIRS:
        path = root / d
        already_existed = path.exists()
        path.mkdir(exist_ok=True)
        label = "exists " if already_existed else "created"
        print(f"  {label}  {d}/")
    print("Directory structure ready.")
