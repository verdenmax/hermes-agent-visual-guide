import re, sys, unicodedata

def extract_sections(path):
    src = open(path, encoding='utf-8').read()
    # Find LESSON_XX = { ... "zh": r""" ... """, "en": r""" ... """ }
    sections = {}
    # split by LESSON_
    for m in re.finditer(r'LESSON_(\d+)\s*=\s*\{', src):
        name = 'LESSON_'+m.group(1)
        start = m.end()
        # find next LESSON_ or EOF
        nxt = re.search(r'\nLESSON_\d+\s*=\s*\{', src[start:])
        end = start+nxt.start() if nxt else len(src)
        block = src[start:end]
        # extract zh and en
        zh = re.search(r'"zh":\s*r"""(.*?)"""', block, re.DOTALL)
        en = re.search(r'"en":\s*r"""(.*?)"""', block, re.DOTALL)
        sections[name] = {
            'zh': zh.group(1) if zh else None,
            'en': en.group(1) if en else None,
        }
    return sections

for path in ['src/part7.py','src/part8.py']:
    secs = extract_sections(path)
    for name, d in secs.items():
        en = d['en']
        if en is None:
            print(f"{path} {name}: NO EN SECTION")
            continue
        # 1. CJK chars in en
        cjk = [(i,c) for i,c in enumerate(en) if '\u4e00'<=c<='\u9fff']
        # 2. U+3000 ideographic space
        u3000 = [i for i,c in enumerate(en) if c=='\u3000']
        # 3. doubled em-dash
        emdash = [m.start() for m in re.finditer('——', en)]
        if cjk:
            # show context
            ctxs = set()
            for i,c in cjk[:20]:
                ctxs.add(en[max(0,i-40):i+10].replace('\n',' '))
            print(f"\n{path} {name} EN: {len(cjk)} CJK chars")
            for ct in list(ctxs)[:12]:
                print("   …"+ct)
        if u3000:
            print(f"\n{path} {name} EN: {len(u3000)} U+3000 ideographic-space")
            for i in u3000[:8]:
                print("   …"+repr(en[max(0,i-40):i+10]))
        if emdash:
            print(f"\n{path} {name} EN: {len(emdash)} doubled em-dash ——")
            for i in emdash[:8]:
                print("   …"+en[max(0,i-40):i+12].replace('\n',' '))
print("\n=== scan done ===")
