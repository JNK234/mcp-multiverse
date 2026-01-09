# mcpx module entry point
# ABOUTME: Enables `python -m mcpx` command
from mcpx.cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
