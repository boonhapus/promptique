import sys

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    # AVAILABLE IN PYTHON 3.11
    from typing import Self
