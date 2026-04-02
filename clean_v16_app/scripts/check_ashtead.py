import sqlite3
conn = sqlite3.connect("data/credit_risk.db")
cur = conn.cursor()

cur.execute("SELECT id, company_name, company_number FROM companies WHERE company_name LIKE '%shtead%'")
companies = cur.fetchall()
print("=== Companies matching Ashtead ===")
for c in companies:
    print(f"  id={c[0]}, name={c[1]}, number={c[2]}")

if companies:
    cid = companies[0][0]
    cur.execute("SELECT * FROM company_financials WHERE company_id=?", (cid,))
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"\n=== company_financials for id={cid} ===")
    for row in rows:
        for col, val in zip(cols, row):
            if val is not None and val != 0 and val != "":
                print(f"  {col}: {val}")

    # Also check SIC history for any stored revenue info
    cur.execute("SELECT company_name, predicted_sic_code, prediction_method, prediction_timestamp FROM sic_prediction_history WHERE company_id=?", (cid,))
    h = cur.fetchone()
    if h:
        print(f"\n=== SIC history ===")
        print(f"  name={h[0]}, sic={h[1]}, method={h[2]}, timestamp={h[3]}")

conn.close()
