"""Allow `python3 -m dynamitejobs ...` invocation."""
from .dj import main
import sys

if __name__ == "__main__":
    sys.exit(main())
