"""Default universe + sector mapping helpers.

When the user does not supply an explicit ticker list we use the
constituents of the sector ETFs in :mod:`config`. We keep a small
pre-canned mid-cap focused list so the scanner is runnable out of the
box without requiring an external constituent feed.
"""

from __future__ import annotations

# Curated mid-cap focused starting universe ($500M–$3B band is volatile, so
# the runtime market-cap filter still applies). These names span all 11 GICS
# sectors and are liquid enough to typically have listed options.
DEFAULT_MID_CAP_UNIVERSE: list[str] = [
    # Technology
    "AMBA", "ASAN", "BL", "BOX", "CRDO", "DOMO", "EVBG", "FROG", "PD", "PLUS",
    "RPD", "SMAR", "SMCI", "SPSC", "VRNS", "YEXT",
    # Communications
    "CARG", "EVER", "IAC", "VMEO", "YELP",
    # Consumer Discretionary
    "BOOT", "CAKE", "CRI", "CWH", "FIVE", "FL", "GOLF", "HIBB", "OLLI",
    "PLAY", "SCVL", "SHAK", "TXRH", "WING",
    # Consumer Staples
    "CALM", "CENT", "FRPT", "JJSF", "SMPL", "USFD", "WDFC",
    # Energy
    "CRC", "DEN", "GPOR", "MGY", "MUR", "NOG", "PUMP", "REI", "RES", "SM",
    "TALO", "VTLE",
    # Financials
    "AX", "BANC", "CADE", "CATY", "EWBC", "FBP", "GBCI", "HOMB", "INDB",
    "OZK", "PB", "TBBK", "TFIN", "VLY", "WAL", "WSBC",
    # Healthcare
    "AMRX", "ANIK", "ATEC", "AXNX", "BLFS", "CCRN", "CDMO", "CRVL", "EVH",
    "HSTM", "ICUI", "IRTC", "OMCL", "PRGO", "SLP", "TMCI",
    # Industrials
    "AAON", "ALG", "ARCB", "ATKR", "BLBD", "CECO", "CSWI", "DY", "EME",
    "ESE", "GVA", "HEES", "MRCY", "MTRN", "NPO", "PRIM", "SPXC", "TGI",
    # Materials
    "AMRK", "ASIX", "CC", "CMP", "ESI", "GEF", "HCC", "KRO", "MEOH", "MTX",
    "NGVT", "OEC", "TROX", "WLK",
    # Real Estate
    "ALEX", "BRX", "CPT", "EPRT", "FCPT", "ROIC", "SAFE", "SBRA", "STAG",
    "UE", "WPC",
    # Utilities
    "ALE", "AVA", "BKH", "IDA", "MGEE", "NJR", "NWE", "OGS", "POR", "SR", "SWX",
]


def resolve_universe(
    explicit: list[str] | None,
    config_default: list[str] | None,
) -> list[str]:
    """Resolve the candidate universe in priority order.

    1. Explicit caller list (e.g. CLI ``--tickers``).
    2. Config-file ``universe.default_tickers``.
    3. Built-in :data:`DEFAULT_MID_CAP_UNIVERSE`.
    """
    if explicit:
        return _dedupe_upper(explicit)
    if config_default:
        return _dedupe_upper(config_default)
    return list(DEFAULT_MID_CAP_UNIVERSE)


def _dedupe_upper(tickers: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tickers:
        t = raw.strip().upper()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out
