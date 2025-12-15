import os
import sqlite3

DB_PATH = os.path.join("instance", "ctf.db")

def ensure_column(cur, table, col, ddl):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        cur.execute(ddl)
        print(f"[ADD] {table}.{col}")
    else:
        print(f"[OK ] {table}.{col}")

def main():
    if not os.path.exists(DB_PATH):
        print("DB not found:", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # user 테이블에 필요한 컬럼들(없으면 추가)
    ensure_column(cur, "user", "role",
                  "ALTER TABLE user ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
    ensure_column(cur, "user", "owner_id",
                  "ALTER TABLE user ADD COLUMN owner_id INTEGER")
    ensure_column(cur, "user", "game1_done",
                  "ALTER TABLE user ADD COLUMN game1_done INTEGER NOT NULL DEFAULT 0")
    ensure_column(cur, "user", "game2_done",
                  "ALTER TABLE user ADD COLUMN game2_done INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
