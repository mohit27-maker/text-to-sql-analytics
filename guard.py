import sqlglot
from sqlglot import exp

BLOCKED = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
           exp.Alter, exp.Command, exp.Into, exp.Merge)
BAD_FUNCS = {"SLEEP", "LOAD_FILE", "BENCHMARK"}

def check_sql(sql: str, max_rows: int = 500):
    """Returns (True, safe_sql) or (False, reason)."""
    try:
        trees = sqlglot.parse(sql, read="mysql")
    except Exception:
        return False, "Could not parse the SQL."
    if len(trees) != 1 or trees[0] is None:
        return False, "Only one statement is allowed."
    tree = trees[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        return False, "Blocked: only SELECT is allowed."
    if any(tree.find(b) for b in BLOCKED):
        return False, "Blocked: only SELECT is allowed."
    for f in tree.find_all(exp.Anonymous):
        if f.name.upper() in BAD_FUNCS:
            return False, f"Blocked function: {f.name}"
    if not tree.args.get("limit"):
        tree = tree.limit(max_rows)
    return True, tree.sql(dialect="mysql")

if __name__ == "__main__":
    tests = [
        "SELECT COUNT(*) FROM customers",
        "DROP TABLE customers",
        "DELETE FROM customers",
        "SELECT 1; DROP TABLE customers",
        "UPDATE customers SET plan='x'",
        "WITH a AS (SELECT * FROM customers) SELECT * FROM a",
    ]
    for t in tests:
        print(check_sql(t), "<-", t)