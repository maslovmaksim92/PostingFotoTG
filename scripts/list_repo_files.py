import os
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "env", ".idea", "node_modules"}

def describe_file(file_path: Path):
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()
        return len(lines)
    except Exception as e:
        return f"Error: {e}"

def scan_directory(base_path: Path):
    result = []
    for root, dirs, files in os.walk(base_path):
        # Ignore excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            full_path = Path(root) / file
            relative_path = full_path.relative_to(base_path)
            lines = describe_file(full_path)
            result.append((str(relative_path), lines))

    return result

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    scanned = scan_directory(repo_root)
    for path, count in scanned:
        print(f"{path}\t{count}")