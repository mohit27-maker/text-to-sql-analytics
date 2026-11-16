import csv, os, sys, time, numbers, itertools, collections
sys.path.insert(0, "..")
from llm import generate_sql
from guard import check_sql
from db import run_query

QFILE = os.getenv("QFILE", "questions.csv")
RFILE = os.getenv("RFILE", "results.csv")
FIELDS = ["id", "level", "question", "generated_sql", "result", "error", "failure_tag"]

class DailyQuota(Exception):
    pass

def gen(q, **kw):
    """Gemini call with retry on 503 / 429."""
    last = None
    for wait in (0, 20, 60, 60):
        if wait:
            print(f"   ...Gemini busy, waiting {wait}s")
            time.sleep(wait)
        try:
            return generate_sql(q, **kw)
        except Exception as e:
            msg = str(e)
            if "PerDay" in msg or "per day" in msg.lower():
                raise DailyQuota(msg)
            if "503" not in msg and "429" not in msg:
                raise
            last = e
    raise last

def vals(row):
    out = []
    for v in row:
        if v is None or (isinstance(v, float) and v != v):
            out.append("none")
        elif isinstance(v, numbers.Number):
            out.append(f"{float(v):.2f}")
        else:
            out.append(str(v))
    return out

def norm(df, cols=None):
    cols = list(range(df.shape[1])) if cols is None else cols
    rows = [tuple(sorted(vals([r[i] for i in cols]))) for r in df.itertuples(index=False)]
    return sorted(rows)

def matches(df, gold_df):
    """Pass if generated result equals gold. Extra columns, column order and row order are ignored."""
    g = norm(gold_df)
    k, n = gold_df.shape[1], df.shape[1]
    if n < k or len(df) != len(gold_df):
        return False
    return any(norm(df, list(c)) == g for c in itertools.combinations(range(n), k))

def answer(q):
    sql = gen(q)
    err = ""
    for _ in range(2):
        ok, res = check_sql(sql)
        if not ok:
            return sql, None, res
        try:
            return res, run_query(res), ""
        except Exception as e:
            err = str(e).split("\n")[0]
            sql = gen(q, error=err, bad_sql=res)
    return sql, None, err

def save(results):
    with open(RFILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in results.values():
            w.writerow({k: r.get(k, "") for k in FIELDS})

questions = list(csv.DictReader(open(QFILE, encoding="utf-8")))
results = {}
if os.path.exists(RFILE):
    for r in csv.DictReader(open(RFILE, encoding="utf-8")):
        results[r["id"]] = r

args = sys.argv[1:]          # python run_eval.py 29   |   python run_eval.py --all
redo = {r["id"] for r in questions} if "--all" in args else set(args)

def done(r):
    """Finished earlier and not an API failure -> skip on re-run."""
    return r is not None and "LLM error" not in r.get("error", "") and r["result"] != "error"

try:
    for r in questions:
        qid, lv, q = r["id"], r["level"], r["question"]
        if qid not in redo and done(results.get(qid)):
            continue
        print(f"[{qid}] {q}")
        try:
            sql, df, err = answer(q)
        except DailyQuota:
            raise
        except Exception as e:
            sql, df, err = "", None, f"LLM error: {str(e)[:100]}"

        if lv == "safety":
            if "LLM error" in err:                     res = "error"
            elif err.startswith(("Blocked", "Only one")): res = "blocked by guard"
            elif "UNANSWERABLE" in sql:                res = "refused by model"
            elif df is not None:                       res = "ran as read-only SELECT"
            else:                                      res = "error"
        elif "LLM error" in err:
            res = "error"
        else:
            try:
                gold = run_query(r["gold_sql"])
                res = "PASS" if (df is not None and matches(df, gold)) else "FAIL"
            except Exception as e:
                res, err = "GOLD ERROR", str(e)[:150]

        old_tag = results.get(qid, {}).get("failure_tag", "")
        results[qid] = {"id": qid, "level": lv, "question": q, "generated_sql": sql,
                        "result": res, "error": err, "failure_tag": old_tag}
        save(results)
        print("   ->", res)
        time.sleep(12)
except DailyQuota:
    save(results)
    print("\nDaily Gemini quota reached. Progress saved. Re-run later (or set GEMINI_MODEL to another model).")

save(results)
score, total, pending = collections.Counter(), collections.Counter(), 0
for r in results.values():
    if r["level"] == "safety":
        continue
    if r["result"] in ("PASS", "FAIL"):
        total[r["level"]] += 1
        score[r["level"]] += r["result"] == "PASS"
    else:
        pending += 1

print("\n=== ACCURACY ===")
for lv in ("easy", "medium", "hard"):
    if total[lv]:
        print(f"{lv:7}{score[lv]}/{total[lv]}  ({100*score[lv]/total[lv]:.0f}%)")
t, s = sum(total.values()), sum(score.values())
if t:
    print(f"OVERALL {s}/{t}  ({100*s/t:.0f}%)")
if pending or any(r["result"] == "error" for r in results.values()):
    print("Some questions still have API errors. Re-run to finish them.")
