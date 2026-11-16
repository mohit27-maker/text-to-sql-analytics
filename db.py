import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

def run_query(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        conn.execute(text("SET SESSION MAX_EXECUTION_TIME=5000"))
        return pd.read_sql(text(sql), conn)

if __name__ == "__main__":
    print(run_query("SHOW TABLES"))