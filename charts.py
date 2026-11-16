import pandas as pd
import plotly.express as px

def make_chart(df: pd.DataFrame):
    if df.empty or len(df.columns) < 2 or len(df) < 2:
        return None
    num = df.select_dtypes("number").columns.tolist()
    other = [c for c in df.columns if c not in num]
    if not num or not other:
        return None
    x, y = other[0], num[0]
    if pd.api.types.is_datetime64_any_dtype(df[x]) or "month" in x.lower() or "date" in x.lower():
        return px.line(df, x=x, y=y, markers=True)
    if len(df) <= 30:
        return px.bar(df, x=x, y=y)
    return None