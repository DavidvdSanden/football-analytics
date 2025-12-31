import ast
import json
import pandas as pd


def parse_json_field(s):
    if pd.isna(s):
        return None
    if isinstance(s, (dict, list)):
        return s
    if isinstance(s, bytes):
        s = s.decode()
    try:
        out = json.loads(s)
        if isinstance(out, str):
            out = json.loads(out)
        return out
    except (json.JSONDecodeError, TypeError):
        return ast.literal_eval(s)
