"""Debug scripts package.

Each module in this package was previously a root-level ad-hoc debug_*.py script.
They were consolidated here for organization. These scripts are NOT imported by
production code and are intended for manual, local diagnostics.

Guidelines:
 - Keep side effects behind `if __name__ == '__main__':` blocks.
 - Avoid adding heavy dependencies not already in requirements.
 - Prefer small focused scripts over large monoliths.
"""

__all__ = []
