from __future__ import annotations

import json
import pathlib
import sys


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python scripts/repair_notebook_stream_outputs.py <notebook.ipynb> [--clear-outputs]")
        return 1

    nb_path = pathlib.Path(sys.argv[1]).resolve()
    clear_outputs = len(sys.argv) == 3 and sys.argv[2] == "--clear-outputs"
    if not nb_path.exists():
        print(f"Notebook not found: {nb_path}")
        return 1

    with nb_path.open("r", encoding="utf-8") as f:
        nb = json.load(f)

    fixes = 0
    for cell in nb.get("cells", []):
        if clear_outputs and cell.get("cell_type") == "code":
            if cell.get("outputs"):
                fixes += 1
            cell["outputs"] = []
            cell["execution_count"] = None
            continue
        for output in cell.get("outputs", []):
            if output.get("output_type") == "stream" and "name" not in output:
                output["name"] = "stdout"
                fixes += 1
            if output.get("output_type") in {"display_data", "execute_result"} and "metadata" not in output:
                output["metadata"] = {}
                fixes += 1
            if output.get("output_type") == "execute_result" and "execution_count" not in output:
                output["execution_count"] = None
                fixes += 1

    with nb_path.open("w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"Repaired {fixes} stream outputs in {nb_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
