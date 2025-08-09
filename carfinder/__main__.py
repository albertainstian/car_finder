from __future__ import annotations
import sys, runpy
try:
    from .cli import main as _main
except Exception:
    _main = None
def main(argv=None):
    if argv is None: argv = sys.argv[1:]
    if callable(_main):
        return _main(argv)
    sys.argv = [sys.argv[0]] + list(argv)
    runpy.run_module("carfinder.cli", run_name="__main__")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
