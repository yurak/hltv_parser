"""
latex_omml.py — minimal, dependency-free LaTeX → OMML (Office Math) converter.

Purpose: render the closed set of LaTeX constructs used in paper/manuscript.md
(§3 Матеріали та методи) into native Word equations (OMML / MS Equation), so the
exported DOCX shows real formulas instead of raw `$...$` source. Journal №47
requires formulas in MS Equation format.

Scope (intentionally narrow — only what the manuscript uses):
  subscripts _x / _{...}, superscripts ^x / ^{...},
  \frac{}{}, \sum with lower limit, \hat{}, \bar{}, \mathbb{...}, \mathbf{...},
  \varphi and a handful of symbols (\in \to \subset \cdot \dots \{ \} \times \le \ge),
  a small Greek fallback table.

The converter returns an OMML XML string WITHOUT namespace declarations; callers
wrap it with docx.oxml.parse_xml(..nsdecls('m','w')..) and append it to a paragraph.
Use latex_to_omml(src) for inline math and latex_to_omml(src, display=True) for a
centered display equation (m:oMathPara).
"""

M = "m"  # OMML namespace prefix (declared by the caller via nsdecls)

# --- symbol maps -------------------------------------------------------------
SYMBOLS = {
    r"\in": "∈", r"\to": "→", r"\subset": "⊂",
    r"\cdot": "⋅", r"\dots": "…", r"\ldots": "…",
    r"\times": "×", r"\le": "≤", r"\leq": "≤",
    r"\ge": "≥", r"\geq": "≥", r"\{": "{", r"\}": "}",
    r"\varphi": "φ", r"\phi": "φ",
    r"\lambda": "λ", r"\alpha": "α", r"\beta": "β",
    r"\mu": "μ", r"\sigma": "σ", r"\eta": "η",
    r"\chi": "χ", r"\pi": "π",
}
# double-struck (blackboard bold) letters for \mathbb{...}
MATHBB = {
    "R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ",
    "C": "ℂ", "P": "ℙ", "E": "\U0001d53c",
}
ACCENTS = {r"\hat": "̂", r"\bar": "̄", r"\tilde": "̃",
           r"\vec": "⃗", r"\dot": "̇"}


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run(text: str, bold: bool = False) -> str:
    """A math run <m:r>; bold=True marks upright bold (\\mathbf)."""
    rpr = f"<{M}:rPr><{M}:sty {M}:val=\"b\"/></{M}:rPr>" if bold else ""
    return (f"<{M}:r>{rpr}"
            f"<{M}:t xml:space=\"preserve\">{_esc(text)}</{M}:t></{M}:r>")


def _acc(chr_: str, base: str) -> str:
    return (f"<{M}:acc><{M}:accPr><{M}:chr {M}:val=\"{chr_}\"/></{M}:accPr>"
            f"<{M}:e>{base}</{M}:e></{M}:acc>")


def _ssub(base: str, sub: str) -> str:
    return (f"<{M}:sSub><{M}:e>{base}</{M}:e>"
            f"<{M}:sub>{sub}</{M}:sub></{M}:sSub>")


def _ssup(base: str, sup: str) -> str:
    return (f"<{M}:sSup><{M}:e>{base}</{M}:e>"
            f"<{M}:sup>{sup}</{M}:sup></{M}:sSup>")


def _frac(num: str, den: str) -> str:
    return (f"<{M}:f><{M}:num>{num}</{M}:num>"
            f"<{M}:den>{den}</{M}:den></{M}:f>")


def _nary_sum(sub: str, operand: str) -> str:
    """n-ary summation ∑ with a lower limit and an operand."""
    pr = (f"<{M}:naryPr><{M}:chr {M}:val=\"∑\"/>"
          f"<{M}:limLoc {M}:val=\"undOvr\"/>"
          f"<{M}:subHide {M}:val=\"0\"/><{M}:supHide {M}:val=\"1\"/></{M}:naryPr>")
    return (f"<{M}:nary>{pr}<{M}:sub>{sub}</{M}:sub><{M}:sup/>"
            f"<{M}:e>{operand}</{M}:e></{M}:nary>")


# --- tokenizer ---------------------------------------------------------------
def _tokenize(s: str):
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            j = i + 1
            if j < n and (s[j].isalpha()):
                while j < n and s[j].isalpha():
                    j += 1
                toks.append(s[i:j]); i = j
            elif j < n:  # escaped single char like \{ \} \,
                toks.append(s[i:j + 1]); i = j + 1
            else:
                i = j
        elif c in "{}^_":
            toks.append(c); i += 1
        elif c.isspace():
            i += 1  # math ignores literal spacing
        else:
            toks.append(c); i += 1
    return toks


class _Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.t[self.i]; self.i += 1; return tok

    def parse_group(self):
        """Parse the argument of a command / a {..} group → OMML string."""
        if self.peek() == "{":
            self.next()
            out = []
            while self.peek() is not None and self.peek() != "}":
                out.append(self.parse_factor())
            if self.peek() == "}":
                self.next()
            return "".join(out)
        # single-token argument
        return self.parse_factor()

    def parse_primary(self):
        tok = self.next()
        if tok == "{":
            self.i -= 1
            return self.parse_group()
        if tok in ACCENTS:
            return _acc(ACCENTS[tok], self.parse_group())
        if tok == "\\frac":
            return _frac(self.parse_group(), self.parse_group())
        if tok == "\\mathbb":
            g = self.parse_group_raw()
            return _run("".join(MATHBB.get(ch, ch) for ch in g))
        if tok == "\\mathbf":
            return _run(self.parse_group_raw(), bold=True)
        if tok == "\\sum":
            sub = ""
            if self.peek() == "_":
                self.next()
                sub = self.parse_group()
            operand = self.parse_factor()
            return _nary_sum(sub, operand)
        if tok in SYMBOLS:
            return _run(SYMBOLS[tok])
        if tok.startswith("\\"):
            return _run(tok[1:])  # unknown command: drop backslash, keep name
        return _run(tok)

    def parse_group_raw(self):
        """Return the raw text of a {..} group (for \\mathbb / \\mathbf)."""
        if self.peek() == "{":
            self.next()
            out = []
            depth = 1
            while self.peek() is not None:
                tk = self.next()
                if tk == "{":
                    depth += 1
                elif tk == "}":
                    depth -= 1
                    if depth == 0:
                        break
                out.append(tk[1:] if tk.startswith("\\") and len(tk) == 2 else tk)
            return "".join(out)
        tk = self.next()
        return tk

    def parse_factor(self):
        """A primary plus any trailing _ / ^ scripts."""
        base = self.parse_primary()
        while self.peek() in ("_", "^"):
            op = self.next()
            arg = self.parse_group()
            base = _ssub(base, arg) if op == "_" else _ssup(base, arg)
        return base

    def parse_all(self):
        out = []
        while self.peek() is not None:
            out.append(self.parse_factor())
        return "".join(out)


def _body(latex: str) -> str:
    return _Parser(_tokenize(latex.strip())).parse_all()


def latex_to_omml(latex: str, display: bool = False) -> str:
    """Convert a LaTeX math string to an OMML XML string (no namespace decls)."""
    inner = _body(latex)
    omath = f"<{M}:oMath>{inner}</{M}:oMath>"
    if display:
        return (f"<{M}:oMathPara><{M}:oMathParaPr>"
                f"<{M}:jc {M}:val=\"center\"/></{M}:oMathParaPr>{omath}</{M}:oMathPara>")
    return omath


if __name__ == "__main__":
    tests = [
        r"T = \{t_1, t_2, \dots, t_N\}",
        r"\varphi: T \to \mathbb{R}^m",
        r"\mathbf{x}_i = \varphi(t_i)",
        r"y_i \in \{0, 1\}",
        r"F_k \subset \varphi",
        r"\hat{p}_B = \frac{\sum_{i : c_i \in B} y_i + k \cdot \bar{y}}{n_B + k}",
    ]
    for t in tests:
        print(t)
        print("  ->", latex_to_omml(t)[:200], "...\n")
