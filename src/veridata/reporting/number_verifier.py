"""Number verifier — every number in user-facing text must match a registered fact (Phase 5, Section 6).

No LLM is ever called here (AGENTS.md rule 2).

Matching (Section 6.2): a number token is allowed when it equals a fact's display string after
normalisation (``.42`` == ``0.42``, ``1338`` == ``1,338``), or lies within half a unit of the
fact's displayed precision (fact shown as ``0.42`` accepts 0.415..0.425, so ``0.43`` fails).
Percentages convert both ways (``12.3%`` <-> ``0.123``). ``<0.001`` matches a fact displayed as
``<0.001``. Number words ("two", "twice", "half") are violations in strict mode.

Ignored on purpose: markdown list numbers at line start, numbered headings, link/image targets,
exact string facts that contain digits (column names such as ``v07``, levels such as ``65+``),
a bare token equal to a numeric-looking level label, and digits inside identifiers (``log1p``).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field

from veridata.reporting.facts import AllowedNumber, FactRegistry

NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "hundreds", "thousand", "thousands", "million", "millions", "billion", "dozen", "dozens", "half", "halves", "twice", "thrice", "double", "doubled", "triple", "tripled", "quadruple", "fourfold", "threefold", "twofold", "tenfold"]
_WORD_RE = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", re.IGNORECASE)
_NUM_RE = re.compile(
    r"(?<![A-Za-z_\d.,])"
    r"(?P<pre>[<>≤≥]\s*)?"
    r"(?P<cur>[$€£])?"
    r"(?P<sign>[-+−])?"
    r"(?P<num>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
    r"(?P<sci>[eE][-+−]?\d+|\s*[×x]\s*10\^?[-+−]?\d+)?"
    r"(?P<pct>\s*%|\s+percent\b)?"
)
_LIST_RE = re.compile(r"^(\s*)(\d+)(\.)(\s)", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6}\s+)([\d.]+)(\s)", re.MULTILINE)
_LINK_TARGET_RE = re.compile(r"\]\(([^)]*)\)")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*)?/?>")  # HTML tags only; '<0.001' is not a tag
_DERIVED_CTX = re.compile(r"^\s*(?:times|x\b|×|fold|-fold)", re.IGNORECASE)


@dataclass
class Violation:
    token: str
    span: tuple[int, int]
    reason: str  # not_in_registry | precision_mismatch | derived_number | number_word | non_ascii_digit

    def as_dict(self) -> dict[str, object]:
        return {"token": self.token, "span": list(self.span), "reason": self.reason}


@dataclass
class VerificationResult:
    ok: bool
    violations: list[Violation] = field(default_factory=list)
    extracted: list[str] = field(default_factory=list)

    def message(self) -> str:
        return "; ".join(f"'{v.token}' ({v.reason})" for v in self.violations)


def _blank(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


def _mask(text: str, string_facts: Iterable[str]) -> str:
    text = _COMMENT_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _TAG_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _LINK_TARGET_RE.sub(lambda m: "](" + " " * len(m.group(1)) + ")", text)
    text = _LIST_RE.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3) + m.group(4), text)
    text = _HEADING_RE.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), text)
    for s in sorted(set(string_facts), key=len, reverse=True):
        has_digit = any(ch.isdigit() for ch in s)
        if (not has_digit and not _WORD_RE.search(s)) or s.replace(".", "", 1).replace("-", "", 1).isdigit():
            continue  # nothing to hide, or a pure-number label (handled token by token)
        start = 0
        while True:
            i = text.find(s, start)
            if i < 0:
                break
            before = text[i - 1] if i > 0 else " "
            after = text[i + len(s)] if i + len(s) < len(text) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                text = _blank(text, i, i + len(s))
            start = i + len(s)
    return text


def _norm_display(s: str) -> str:
    s = s.strip().replace(",", "").replace("−", "-").replace(" ", "")
    s = s.removeprefix("+")
    s = re.sub(r"^(-?)\.", r"\g<1>0.", s)
    s = re.sub(r"^(<|>)(-?)\.", r"\1\g<2>0.", s)
    return s


def _parse(m: re.Match[str]) -> float:
    num = m.group("num").replace(",", "")
    v = float(num)
    if m.group("sign") in {"-", "−"}:
        v = -v
    sci = m.group("sci")
    if sci:
        e = re.search(r"[-+−]?\d+$", sci.replace(" ", ""))
        if e:
            v = v * 10 ** int(e.group(0).replace("−", "-"))
    return v


def _matches(tok: str, value: float, is_pct: bool, has_lt: bool, allowed: list[AllowedNumber]) -> tuple[bool, bool]:
    """(matched, near_miss).

    Conservative rules (decision P5-04):
    - equal to a fact's display (after removing commas / unicode minus), or
    - numerically within half a unit of the last shown digit. If the token shows *more* decimals
      than the fact's display, it must be the correct rounding of the fact's real value at the
      token's precision (so "0.121" is not accepted for a fact shown as "0.12" whose value is 0.12).
    - percent tokens only match percent facts and plain tokens only match plain facts: there is no
      fraction <-> percent conversion, so "0.95" can never borrow the "95%" confidence level.
    - "<0.001" style facts only match tokens written with "<".
    """
    norm_tok = _norm_display(tok)
    tok_dec = _decimals(tok)
    near = False
    for a in allowed:
        disp = _norm_display(a.display)
        if a.is_percent != is_pct:
            continue
        if norm_tok == disp or (is_pct and norm_tok.rstrip("%") == disp.rstrip("%")):
            return True, False
        if a.is_upper_bound or has_lt:
            continue
        tol = 0.5 * 10 ** (-max(a.decimals, tok_dec)) + 1e-12
        diff = abs(value - a.value)
        if diff <= tol:
            return True, False
        if diff <= max(10 * tol, 0.5 * 10 ** (-a.decimals) * 10):
            near = True
    return False, near


def _decimals(tok: str) -> int:
    m = re.search(r"\.(\d+)", tok)
    return len(m.group(1)) if m else 0


def verify_text(
    text: str,
    registry: FactRegistry,
    finding_ids: Iterable[str] | None = None,
    *,
    whitelist: Iterable[str] = (),
    strict: bool = True,
    allow_years: bool = False,
    extra_strings: Iterable[str] = (),
) -> VerificationResult:
    """Check every number in ``text`` against the facts of ``finding_ids`` (plus report/method/summary facts)."""
    ids = list(finding_ids) if finding_ids is not None else None
    allowed = registry.allowed_numbers(ids)
    strings = registry.string_facts(ids)
    numeric_labels = {s for s in strings if re.fullmatch(r"-?\d+(\.\d+)?", s)}
    wl = {_norm_display(w) for w in whitelist}
    masked = _mask(text, [*strings, *sorted(extra_strings, key=len, reverse=True)])
    res = VerificationResult(ok=True)

    for m in _NUM_RE.finditer(masked):
        tok = m.group(0).strip()
        res.extracted.append(tok)
        raw_num = (m.group("sign") or "") + m.group("num")
        if raw_num in numeric_labels or m.group("num") in numeric_labels and not m.group("pct"):
            continue
        if _norm_display(tok) in wl:
            continue
        value = _parse(m)
        if allow_years and re.fullmatch(r"(19|20)\d{2}", m.group("num")):
            continue
        tail = masked[m.end() : m.end() + 8]
        if _DERIVED_CTX.match(tail):
            res.violations.append(Violation(tok, m.span(), "derived_number"))
            continue
        is_pct = bool(m.group("pct"))
        has_lt = bool(m.group("pre"))
        ok, near = _matches(tok, value, is_pct, has_lt, allowed)
        if not ok:
            res.violations.append(Violation(tok, m.span(), "precision_mismatch" if near else "not_in_registry"))
    if strict:
        for m in _WORD_RE.finditer(masked):
            res.violations.append(Violation(m.group(0), m.span(), "number_word"))
    for i, ch in enumerate(masked):
        if unicodedata.category(ch) == "Nd" and not ch.isascii():
            res.violations.append(Violation(ch, (i, i + 1), "non_ascii_digit"))
    res.violations.sort(key=lambda v: v.span)
    res.ok = not res.violations
    return res
