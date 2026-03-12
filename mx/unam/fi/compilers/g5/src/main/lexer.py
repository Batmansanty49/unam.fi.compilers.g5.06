import re

kw = set("""auto break case char const continue default do double else enum extern 
float for goto if inline int long register restrict return short signed sizeof 
static struct switch typedef union unsigned void volatile while _Alignas _Alignof 
_Atomic _Bool _Complex _Generic _Noreturn _Static_assert _Thread_local 
print printf""".split())

ops=["<<="," >>=","<<",">>","<=",">=","==","!=","&&","||","++","--","+=","-=","*=","/=","%=","&=","|=","^=","->","=","+","-","*","/","%","<",">","!","~","&","|","^","? ",":"]
ops=sorted([o.strip() for o in ops],key=len,reverse=True)
op_pat="|".join(re.escape(o) for o in ops)
puncts=[r'\,',r';',r'\(',r'\)',r'\{',r'\}',r'\[',r'\]',r'\.']
pun_pat="|".join(puncts)
patterns=[
 ("comment",re.compile(r'^(//[^\n]*|/\*[\s\S]*?\*/)')),
 ("ws",re.compile(r'^\s+')),
 ("string",re.compile(r'^"([^"\\]|\\.)*"')),
 ("char",re.compile(r"^'([^'\\]|\\.)*'")),
 ("hex",re.compile(r'^0[xX][0-9A-Fa-f]+')),
 ("float",re.compile(r'^(\d+\.\d*|\.\d+)([eE][+-]?\d+)?')),
 ("int",re.compile(r'^\d+')),
 ("ident",re.compile(r'^[A-Za-z_][A-Za-z0-9_]*')),
 ("op",re.compile(r'^('+op_pat+')')),
 ("punct",re.compile(r'^('+pun_pat+')')),
 ("other",re.compile(r'^.'))
]
s=open("input.txt","r",encoding="utf-8").read()
i=0
types=[]
while i<len(s):
 for name,pat in patterns:
  m=pat.match(s[i:])
  if not m: continue
  tok=m.group(0)
  i+=len(tok)
  if name in ("comment","ws"): break
  if name=="string" or name=="char":
   types.append("literal")
  elif name in ("hex","float","int"):
   types.append("constant")
  elif name=="ident":
   types.append("keyword" if tok in kw else "identifier")
  elif name=="op":
   types.append("operator")
  elif name=="punct":
   types.append("punctuation")
  else:
   types.append("punctuation")
  break
print(" ".join(types))
print(f"Total of tokens: {len(types)}")