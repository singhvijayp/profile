#!/usr/bin/env python3
"""
Generates the section-heading images (hd-*.svg). These don't need any API
data, just re-run this whenever you want to rename a section.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svg_builders import heading

OUT_DIR = os.path.join(os.path.dirname(__file__), "..")

HEADINGS = {
    "hd-about.svg": "about",
    "hd-stack.svg": "stack",
    "hd-projects.svg": "projects",
    "hd-stats.svg": "stats",
    "hd-about-this-page.svg": "about this page",
}


def main():
    for filename, label in HEADINGS.items():
        path = os.path.join(OUT_DIR, filename)
        with open(path, "w") as f:
            f.write(heading(label))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
