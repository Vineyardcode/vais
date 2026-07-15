#!/usr/bin/env python3
"""VAIS sanity-check suite: hand-verified expectations for every core helper.

    python sanity_checks/run_all.py     (exit 0 = all pass)

Expected values are derived independently in the check modules' comments,
never by calling the function under test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "webui"))

import checks_math      # noqa: E402
import checks_fingerprint  # noqa: E402
import checks_ivtff  # noqa: E402
import checks_parsing   # noqa: E402
import checks_webui     # noqa: E402

sys.path.insert(0, str(ROOT / "sanity_checks"))


def main():
    total_fails = []
    for mod in (checks_math, checks_parsing, checks_webui, checks_fingerprint,
                checks_ivtff):
        fails = mod.run()
        status = "OK" if not fails else f"{len(fails)} FAIL"
        print(f"  {mod.__name__:<18} {status}")
        for f in fails:
            print(f"    FAIL: {f}")
        total_fails += fails
    print(f"\n{'ALL SANITY CHECKS PASS' if not total_fails else f'{len(total_fails)} FAILURES'}")
    return 1 if total_fails else 0


if __name__ == "__main__":
    sys.exit(main())
