import re

kw = set("""auto break case char const continue default do double else enum extern 
float for goto if inline int long register restrict return short signed sizeof 
static struct switch typedef union unsigned void volatile while _Alignas _Alignof 
_Atomic _Bool _Complex _Generic _Noreturn _Static_assert _Thread_local 
print printf""".split())

ops = ["<<=", ">>=", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||", "++", "--",
       "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "->",
       "=", "+", "-", "*", "/", "%", "<", ">", "!", "~", "&", "|", "^", "?", ":"]
ops = sorted([o.strip() for o in ops], key=len, reverse=True)
op_pat = "|".join(re.escape(o) for o in ops)

puncts = [r'\,', r';', r'\(', r'\)', r'\{', r'\}', r'\[', r'\]', r'\.']
pun_pat = "|".join(puncts)

patterns = [
    ("comment", re.compile(r'^(//[^\n]*|/\*[\s\S]*?\*/)')),
    ("ws",      re.compile(r'^\s+')),
    ("string",  re.compile(r'^"([^"\\]|\\.)*"')),
    ("char",    re.compile(r"^'([^'\\]|\\.)*'")),
    ("hex",     re.compile(r'^0[xX][0-9A-Fa-f]+')),
    ("float",   re.compile(r'^(\d+\.\d*|\.\d+)([eE][+-]?\d+)?')),
    ("int",     re.compile(r'^\d+')),
    ("ident",   re.compile(r'^[A-Za-z_][A-Za-z0-9_]*')),
    ("op",      re.compile(r'^(' + op_pat + ')')),
    ("punct",   re.compile(r'^(' + pun_pat + ')')),
    ("other",   re.compile(r'^.'))
]


def tokenize(source: str) -> list:
    tokens = []
    i = 0
    while i < len(source):
        for name, pat in patterns:
            m = pat.match(source[i:])
            if not m:
                continue
            tok = m.group(0)
            i += len(tok)
            if name in ("comment", "ws"):
                break
            if name in ("string", "char"):
                tokens.append(("literal", tok))
            elif name in ("hex", "float", "int"):
                tokens.append(("constant", tok))
            elif name == "ident":
                tokens.append(("keyword" if tok in kw else "identifier", tok))
            elif name == "op":
                tokens.append(("operator", tok))
            elif name in ("punct", "other"):
                tokens.append(("punctuation", tok))
            break
    return tokens


if __name__ == "__main__":
    import os
    input_file = os.path.join(os.path.dirname(__file__), "input.txt")
    with open(input_file, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = tokenize(source)

    print("=" * 45)
    print(f"{'TOKEN TYPE':<15} {'VALUE'}")
    print("=" * 45)
    for ttype, tval in tokens:
        print(f"{ttype:<15} {repr(tval)}")
    print("=" * 45)
    print(" ".join(t for t, _ in tokens))
    print(f"Total of tokens: {len(tokens)}")
