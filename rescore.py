# Re-scores results.csv with the current questions.csv and matching rules. No Gemini calls.
import csv, sys, numbers, itertools, collections
sys.path.insert(0, "..")
from db import run_query

def vals(row):
    out = []
    for v in row:
        if v is None or (isinstance(v, float) and v != v): out.append("none")
        elif isinstance(v, numbers.Number): out.append(f"{float(v):.2f}")
        else: out.append(str(v))
    return out

def norm(df, cols=None):
    cols = list(range(df.shape[1])) if cols is None else cols
    return sorted(tuple(sorted(vals([r[i] for i in cols]))) for r in df.itertuples(index=False))

def matches(df, gold_df):
    g, k, n = norm(gold_df), gold_df.shape[1], df.shape[1]
    if n < k or len(df) != len(gold_df): return False
    return any(norm(df, list(c)) == g for c in itertools.combinations(range(n), k))

gold = {r["id"]: r["gold_sql"] for r in csv.DictReader(open("questions.csv", encoding="utf-8"))}
rows = list(csv.DictReader(open("results.csv", encoding="utf-8")))
for r in rows:
    if r["level"] == "safety" or r["result"] not in ("PASS", "FAIL") or not r["generated_sql"]:
        continue
    try:
        ok = matches(run_query(r["generated_sql"]), run_query(gold[r["id"]]))
        new = "PASS" if ok else "FAIL"
    except Exception as e:
        new = "FAIL"
    if new != r["result"]:
        print(f"[{r['id']}] {r['result']} -> {new}")
    r["result"] = new

with open("results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

sc, tot = collections.Counter(), collections.Counter()
for r in rows:
    if r["result"] in ("PASS", "FAIL"):
        tot[r["level"]] += 1; sc[r["level"]] += r["result"] == "PASS"
for lv in ("easy", "medium", "hard"):
    print(f"{lv:7}{sc[lv]}/{tot[lv]}")
print(f"OVERALL {sum(sc.values())}/{sum(tot.values())}")
