import plotly.express as px
import pandas as pd

def auto_chart(df: pd.DataFrame):
    if df.shape[1] < 2:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    first_col = df.columns[0]
    y_col = numeric_cols[0]

    if "date" in first_col.lower():
        return px.line(df, x=first_col, y=y_col)

    return px.bar(df, x=first_col, y=y_col)
