"""Name-based user resolution helpers.

Resolution strategy (in order of preference):
  1. Exact match against full_name / username / email
  2. Substring / token match against full_name parts
  3. Fuzzy (typo-tolerant) match, e.g. "Pranish" -> "Pranesh"
"""

from difflib import SequenceMatcher


def match_user(users: list[dict], name: str) -> dict | None:
    """Match a user dict by name/email/username with exact, substring, then fuzzy matching."""
    target = name.lower().strip()
    if not target:
        return None
    target_tokens = [t for t in target.replace(".", " ").split() if len(t) > 1]

    def candidates(u: dict) -> list[str]:
        return [
            u.get("full_name") or "",
            u.get("username") or "",
            u.get("email") or "",
            (u.get("full_name") or "").replace(".", " "),
        ]

    # 1. Exact match
    for u in users:
        for cand in candidates(u):
            if cand.strip().lower() == target:
                return u

    # 2. Substring / token match
    for u in users:
        for cand in candidates(u):
            cl = cand.lower()
            if not cl:
                continue
            if target in cl:
                return u
            if any(tok in cl for tok in target_tokens):
                return u

    # 3. Fuzzy match (handles typos like Pranish -> Pranesh)
    best_u, best_score = None, 0.0
    for u in users:
        for cand in candidates(u):
            cl = cand.lower().strip()
            if not cl:
                continue
            for cmp_name in [cl] + [t for t in cl.split() if len(t) > 2]:
                ratio = SequenceMatcher(None, target, cmp_name).ratio()
                if ratio > best_score:
                    best_score, best_u = ratio, u
    if best_u is not None and best_score >= 0.75:
        return best_u
    return None
