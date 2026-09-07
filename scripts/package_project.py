"""
Package NyayaSetu into a clean, complete, and reproducible ZIP archive.
Ensures no source code, data, benchmark, config, or documentation file is missed,
while omitting transient machine-specific binaries (node_modules, venv, .git, __pycache__).
"""

import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP_1 = ROOT_DIR.parent / "NyayaSetu-Full-Project.zip"
OUTPUT_ZIP_2 = Path(r"C:\Users\Yuvraj Singh\.gemini\antigravity-ide\brain\fa3e5cb3-4fd7-43c6-89bd-c295b871eba4\NyayaSetu-Full-Project.zip")

EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
}

def should_exclude(rel_path_parts):
    for part in rel_path_parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def package_project():
    print(f"Packaging NyayaSetu from: {ROOT_DIR}")
    
    file_count = 0
    total_uncompressed_bytes = 0

    files_to_zip = []

    for root, dirs, files in os.walk(ROOT_DIR):
        # Modify dirs in-place to avoid recursing into excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(ROOT_DIR)

            if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
                continue

            if should_exclude(rel_path.parts):
                continue

            files_to_zip.append((file_path, rel_path))
            file_count += 1
            total_uncompressed_bytes += file_path.stat().st_size

    print(f"Total eligible files: {file_count} ({total_uncompressed_bytes / (1024*1024):.2f} MB uncompressed)")

    for out_zip in [OUTPUT_ZIP_1, OUTPUT_ZIP_2]:
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing zip archive to: {out_zip}")
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for file_path, rel_path in files_to_zip:
                # Store under NyayaSetu/ relative prefix
                archive_name = Path("NyayaSetu") / rel_path
                zf.write(file_path, str(archive_name))
        
        compressed_size = out_zip.stat().st_size / (1024 * 1024)
        print(f"Finished {out_zip.name}: {compressed_size:.2f} MB compressed.")

if __name__ == "__main__":
    package_project()
