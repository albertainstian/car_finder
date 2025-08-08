import sys
# Try to call a main() defined in the package (or in cli.py if you later split it)
try:
    from . import main as _main
except Exception:
    try:
        from .cli import main as _main  # optional fallback
    except Exception:
        print("carfinder: no main() found. Define main(argv=None) in the package.", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    sys.exit(_main())
