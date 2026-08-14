from pathlib import Path

SKIP = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "logs",
    "reports",
    "data",
}


def tree(path: Path, prefix: str = ""):
    items = [p for p in sorted(path.iterdir()) if p.name not in SKIP]

    for i, item in enumerate(items):
        last = i == len(items) - 1
        connector = "└── " if last else "├── "
        print(prefix + connector + item.name)

        if item.is_dir():
            extension = "    " if last else "│   "
            tree(item, prefix + extension)


root = Path(".")
print(root.resolve().name)
tree(root)