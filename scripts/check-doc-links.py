from __future__ import annotations

import pathlib
import re
import sys


def main() -> None:
    bad_links: list[str] = []
    skip_parts = {".venv", "node_modules", "dist"}

    for path in pathlib.Path(".").rglob("*.md"):
        if set(path.parts) & skip_parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1)
            if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                continue
            relative_path = pathlib.Path(target.split("#", 1)[0])
            if relative_path == pathlib.Path(""):
                continue
            resolved = (path.parent / relative_path).resolve()
            if not resolved.exists():
                bad_links.append(f"{path}:{target}")

    if bad_links:
        print("\n".join(bad_links))
        sys.exit(1)

    print("markdown links ok")


if __name__ == "__main__":
    main()
