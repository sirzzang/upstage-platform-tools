import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sample.db")

BLOCKED_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "REPLACE"}


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_schema() -> str:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()

    schema_parts = []
    for (table_name,) in tables:
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = cur.fetchall()
        col_defs = [f"  {col[1]} {col[2]}" for col in columns]

        cur.execute(f"PRAGMA foreign_key_list({table_name})")
        fks = cur.fetchall()
        fk_defs = [f"  FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]})" for fk in fks]

        parts = ",\n".join(col_defs + fk_defs)
        schema_parts.append(f"CREATE TABLE {table_name} (\n{parts}\n);")

    conn.close()
    return "\n\n".join(schema_parts)


def execute_query(sql: str) -> str:
    sql_upper = sql.strip().upper()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper.split():
            return f"[오류] {keyword} 쿼리는 허용되지 않습니다. SELECT만 사용 가능합니다."

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return "결과 없음"

        header = " | ".join(columns)
        separator = "-" * len(header)
        row_strs = [" | ".join(str(val) for val in row) for row in rows]

        return f"{header}\n{separator}\n" + "\n".join(row_strs)
    except Exception as e:
        return f"[SQL 오류] {e}"
