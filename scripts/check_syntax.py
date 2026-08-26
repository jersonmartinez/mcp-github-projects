"""Check Python syntax for all .py files in the MCP tree."""

import ast
import os
import sys

errors: list[str] = []

for root, dirs, files in os.walk("/app"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                ast.parse(open(path).read())
            except SyntaxError as e:
                errors.append(f"{path}: {e.msg} (line {e.lineno})")

if errors:
    print(f"❌ {len(errors)} syntax error(s):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    total = sum(
        1
        for r, d, fs in os.walk("/app")
        if "__pycache__" not in r
        for f in fs
        if f.endswith(".py")
    )
    print(f"✅ All {total} Python files parse cleanly")
