import re, json, glob, os
from collections import Counter
import docx

UPLOADS = os.path.dirname(os.path.abspath(__file__))

def parse_module(path):
    m = re.search(r"Module(\d+)_(.+)\.docx", os.path.basename(path))
    mod_no, mod_name = int(m.group(1)), m.group(2).replace("_", " ")
    d = docx.Document(path)
    out, set_no, set_title, cur = [], None, None, None
    def flush():
        nonlocal cur
        if cur: out.append(cur); cur = None
    for p in d.paragraphs:
        t = p.text.strip()
        if not t: continue
        hs = re.match(r"Set (\d+): (.+)$", t)
        if hs and p.style.name.lower().startswith("heading"):
            flush(); set_no, set_title = int(hs.group(1)), hs.group(2).strip(); continue
        qm = re.match(r"Q(\d+)\.\s*(.*)$", t, flags=re.S)
        if qm and set_no:
            flush()
            rest = qm.group(2)
            tm = re.search(r"\s*\[([^\[\]]+)\]\s*$", rest)
            cur = {"id": f"M{mod_no:02d}-S{set_no:02d}-Q{int(qm.group(1)):02d}",
                   "module_no": mod_no, "module": mod_name,
                   "set_no": set_no, "set_title": set_title, "q_no": int(qm.group(1)),
                   "stem": rest[:tm.start()].strip() if tm else rest.strip(),
                   "concept_tag": tm.group(1).strip() if tm else None,
                   "options": {}, "answer": None, "explanation": None}
            continue
        if not cur: continue
        om = re.match(r"([A-D])\.\s+(.*)$", t, flags=re.S)
        if om and cur["answer"] is None: cur["options"][om.group(1)] = om.group(2).strip(); continue
        am = re.match(r"Correct answer:\s*([A-D])\.", t)
        if am: cur["answer"] = am.group(1); continue
        em = re.match(r"Explanation:\s*(.*)$", t, flags=re.S)
        if em: cur["explanation"] = em.group(1).strip(); continue
    flush()
    return out

if __name__ == "__main__":
    allq = []
    for f in sorted(glob.glob(os.path.join(UPLOADS, "Java_MCQ_Module*.docx"))):
        qs = parse_module(f)
        print(os.path.basename(f), len(qs), "questions")
        allq += qs
    print("TOTAL", len(allq))
    with open(os.path.join(UPLOADS, "static_questions.json"), "w", encoding="utf-8") as fh:
        json.dump(allq, fh, indent=1, ensure_ascii=False)