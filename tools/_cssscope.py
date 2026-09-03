# -*- coding: utf-8 -*-
"""サイトの style.css を #paper の中だけに効くように書き換える。"""
import re

def _split_commas(s):
    out=[]; depth=0; buf=""
    for c in s:
        if c=='(' or c=='[': depth+=1
        elif c==')' or c==']': depth-=1
        if c==',' and depth==0:
            out.append(buf); buf=""
        else:
            buf+=c
    out.append(buf)
    return out

def _split_rules(s):
    """トップレベルを (prelude, body) に分ける。"""
    rules=[]; buf=""; i=0; n=len(s)
    while i<n:
        c=s[i]
        if c=='{':
            prelude=buf; buf=""
            d=1; j=i+1
            while j<n and d>0:
                if s[j]=='{': d+=1
                elif s[j]=='}': d-=1
                j+=1
            rules.append((prelude.strip(), s[i+1:j-1]))
            i=j
            continue
        buf+=c; i+=1
    if buf.strip():
        rules.append((buf.strip(), None))   # ぶら下がり(通常は無い)
    return rules

def _scope_selector(prelude, sel):
    out=[]
    for p in _split_commas(prelude):
        p=p.strip()
        if not p: continue
        if p==':root' or p=='html' or p=='body':
            out.append(sel)
        elif p=='*':
            out.append(sel+' *')
        elif p.startswith(':root'):
            out.append(sel+p[5:])
        elif re.match(r'^html\b', p):
            out.append(sel+p[4:])
        elif re.match(r'^body\b', p):
            out.append(sel+p[4:])
        else:
            out.append(sel+' '+p)
    return ','.join(out)

def scope(css, sel='#paper'):
    css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
    parts=[]
    for prelude, body in _split_rules(css):
        if body is None: continue
        if prelude.startswith('@media') or prelude.startswith('@supports') or prelude.startswith('@container'):
            parts.append(prelude+'{'+scope(body, sel)+'}')
        elif prelude.startswith('@'):
            parts.append(prelude+'{'+body+'}')
        else:
            s=_scope_selector(prelude, sel)
            if s: parts.append(s+'{'+body.strip()+'}')
    return '\n'.join(parts)

if __name__=='__main__':
    import sys
    import os as _o; src=open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),'..','assets','css','style.css'),encoding='utf-8').read()
    out=scope(src)
    print('元:', len(src.encode())//1024, 'KB ->', len(out.encode())//1024, 'KB')
    # 検証: #paper が付いていないルールが残っていないか
    bad=[l for l in out.split('\n') if l and not l.startswith(('#paper','@','}')) and '{' in l]
    print('未スコープの行:', len(bad))
    for b in bad[:8]: print('   ', b[:100])
    open(r'C:/Users/ihfff/AppData/Local/Temp/claude/c--Users-ihfff-Desktop-ozu-life-memo/bc6835fa-fa1e-45d5-ac3b-a08aa5713c84/scratchpad/scoped.css','w',encoding='utf-8').write(out)
