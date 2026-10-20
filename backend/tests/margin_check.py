import csv, sys
sys.path.insert(0, "scripts")
from retrieval import _collection, check_scope

completed = ["lec1"]
rows = [r for r in csv.DictReader(open("tests/results_v2.csv", encoding="utf-8"))
        if r["setting"] == "completed = lec1" and r["gate"] == "ON"]

out = []
for r in rows:
    q = r["question"]
    a = _collection.query(query_texts=[q], n_results=1,
        where={"lecture_id": {"$in": completed}})["distances"][0][0]
    l = _collection.query(query_texts=[q], n_results=1,
        where={"lecture_id": {"$nin": completed}})["distances"][0][0]
    title = check_scope(q, completed)["scope"]
    out.append((round(l - a, 3), r["expected"], title, round(a, 3), round(l, 3), q[:50]))

print("margin | expected | title | allowed | locked | question")
for row in sorted(out):
    print(*row, sep=" | ")