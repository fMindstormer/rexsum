"""Copy what GitHub Pages serves into one directory: the demo page, the examples, the generator with
its compiler, and patterns.json (the generator fetches it).
    python site/publish.py _site"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {"index.html": "site/index.html", "generator.html": "site/generator.html",
         "generator-worker.mjs": "site/generator-worker.mjs", "compile.mjs": "js/compile.mjs",
         "patterns.json": "patterns.json"}


def publish(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for dest, src in FILES.items():
        shutil.copyfile(ROOT / src, out / dest)
    shutil.copytree(ROOT / "site" / "examples", out / "examples", dirs_exist_ok=True)
    return out


if __name__ == "__main__":
    print(publish(sys.argv[1]))
