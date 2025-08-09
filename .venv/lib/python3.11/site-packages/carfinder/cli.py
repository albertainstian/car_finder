import sys

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        # Prefer a real entry in your core module if it exists
        from .core import main as core_main  # type: ignore
        return core_main(argv)  # your existing main(argv) can live here
    except Exception:
        print("carfinder CLI installed. Expose `main(argv)` in carfinder/core.py for full CLI.")
        return 0
