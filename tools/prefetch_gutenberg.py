#!/usr/bin/env python3
"""Populate data/gutenberg_cache/ so every network test runs offline.

IDs = the union of every fetch_gutenberg() call across the suite:
  phase58-65 reference set + phase72/73 source texts (incl. the English
  fallback pair 10/100 so the fallback path is offline too).
Roughly 16 MB total. Safe to re-run: cached files are skipped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from common import DATA_DIR, fetch_gutenberg  # noqa: E402

IDS = {
    11: "Alice in Wonderland (English)",
    1012: "Dante, Inferno (Italian)",
    2000: "Don Quixote (Spanish)",
    2229: "Goethe, Faust (German)",
    7000: "Kalevala (Finnish)",
    7028: "Virgil, Aeneid (Latin)",
    10657: "Caesar, De Bello Gallico (Latin)",
    17489: "Hugo, Les Miserables (French)",
    10: "KJV Bible (English, phase72 primary)",
    100: "Complete Shakespeare (English, phase72 fallback)",
}

if __name__ == "__main__":
    cache = DATA_DIR / "gutenberg_cache"
    for ebook_id, label in IDS.items():
        cached = (cache / f"pg{ebook_id}.txt").exists()
        text = fetch_gutenberg(ebook_id)
        print(f"  #{ebook_id:<6} {'cached' if cached else 'fetched':7s} "
              f"{len(text):>9,} chars  {label}")
    total = sum(p.stat().st_size for p in cache.glob("pg*.txt"))
    print(f"\ncache: {len(list(cache.glob('pg*.txt')))} files, "
          f"{total/1e6:.1f} MB in {cache}")
