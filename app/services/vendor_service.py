"""MAC-address vendor lookup from the bundled OUI table (app/data/oui.tsv)."""
from __future__ import annotations

from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "oui.tsv"

# Keyed by prefix length in hex nibbles: 9 = 36-bit, 7 = 28-bit, 6 = 24-bit.
_TABLES: dict[int, dict[str, str]] = {9: {}, 7: {}, 6: {}}
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                prefix, _, vendor = line.partition("\t")
                table = _TABLES.get(len(prefix))
                if table is not None and vendor:
                    table[prefix] = vendor
    except OSError:
        pass


def lookup_vendor(mac: str) -> str | None:
    _load()

    hexmac = mac.replace(":", "").replace("-", "").upper()
    if len(hexmac) < 9:
        return None

    try:
        first_octet = int(hexmac[0:2], 16)
    except ValueError:
        return None

    if first_octet & 0x02:
        return "Randomized/private address"

    for nibbles in (9, 7, 6):
        vendor = _TABLES[nibbles].get(hexmac[:nibbles])
        if vendor:
            return vendor
    return None
