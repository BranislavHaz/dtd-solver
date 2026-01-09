# dtd_solver/__main__.py
# Package entrypoint so you can run:
#   python -m dtd_solver --help
# and it will delegate to the JSON runner by default (most useful in your workflow).
#
# Examples:
#   python -m dtd_solver --job data.json
#   python -m dtd_solver --job data.json --out out/ --time 30 --cut_weight 2

from __future__ import annotations

from .run_json import main

if __name__ == "__main__":
    main()
