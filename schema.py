import os
from sqlalchemy import text
from db import engine

def get_schema(sample_rows=2) -> str:
    db = os.getenv("DB_NAME")
    out = []
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema=:db ORDER BY table_name"), {"db": db}).fetchall()

        for name, ttype in tables:
            kind = "VIEW" if ttype == "VIEW" else "TABLE"
            out.append(f"{kind} {name}")

            cols = conn.execute(text(
                "SELECT column_name, data_type, column_key "
                "FROM information_schema.columns "
                "WHERE table_schema=:db AND table_name=:t "
                "ORDER BY ordinal_position"), {"db": db, "t": name}).fetchall()
            for c, dtype, key in cols:
                out.append(f"  {c} {dtype}" + (" PK" if key == "PRI" else ""))

            fks = conn.execute(text(
                "SELECT column_name, referenced_table_name, referenced_column_name "
                "FROM information_schema.key_column_usage "
                "WHERE table_schema=:db AND table_name=:t "
                "AND referenced_table_name IS NOT NULL"), {"db": db, "t": name}).fetchall()
            for c, rt, rc in fks:
                out.append(f"  FK: {c} -> {rt}.{rc}")

            rows = conn.execute(text(f"SELECT * FROM `{name}` LIMIT {sample_rows}")).fetchall()
            for r in rows:
                out.append(f"  sample: {tuple(r)}")
            out.append("")
    return "\n".join(out)

if __name__ == "__main__":
    print(get_schema())