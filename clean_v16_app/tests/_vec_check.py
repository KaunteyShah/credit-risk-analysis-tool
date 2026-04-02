#!/usr/bin/env python3
"""Populate Lloyds reference revenue in main DB and recheck."""
import sqlite3, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

main_conn = sqlite3.connect('data/credit_risk.db')
mc = main_conn.cursor()

# Get Lloyds company_id
mc.execute("SELECT id FROM companies WHERE company_number = 'SC095000'")
row = mc.fetchone()
print(f"Lloyds company id: {row}")
if not row:
    print("ERROR: Lloyds not found in companies table")
    main_conn.close()
    exit(1)
company_id = row[0]

# Check if row already exists in company_financials
mc.execute("SELECT id FROM company_financials WHERE company_id = ?", (company_id,))
existing = mc.fetchone()

# Lloyds 2024 Annual Report: Net income £17.1bn → USD at 1.25 rate = ~21.375bn
if existing:
    mc.execute("""
        UPDATE company_financials
        SET sales_usd = 21375000000,
            latest_revenue = 17100000000,
            revenue_year = 2024,
            period_type = 'Annual',
            updated_at = datetime('now')
        WHERE company_id = ?
    """, (company_id,))
    print(f"Updated existing row (id={existing[0]}): {mc.rowcount} rows changed")
else:
    mc.execute("""
        INSERT INTO company_financials
            (company_id, sales_usd, latest_revenue, revenue_year, period_type, created_at, updated_at)
        VALUES (?, 21375000000, 17100000000, 2024, 'Annual', datetime('now'), datetime('now'))
    """, (company_id,))
    print(f"Inserted new row, rowid={mc.lastrowid}")

main_conn.commit()

# Verify
mc.execute("""
    SELECT c.company_number, c.company_name, cf.sales_usd, cf.latest_revenue, cf.revenue_year
    FROM company_financials cf
    JOIN companies c ON c.id = cf.company_id
    WHERE c.company_number = 'SC095000'
""")
print("Lloyds after change:", mc.fetchone())
main_conn.close()
print("Done — DB guidance anchor is now £17.1bn for Lloyds.")


main_conn = sqlite3.connect('data/credit_risk.db')
mc = main_conn.cursor()

# Lloyds 2024 Annual Report: Net income £17.1bn  → sales_usd at 1.25 rate = ~21.375bn USD
# Use latest_revenue (GBP pence-less) and sales_usd
mc.execute("""
    UPDATE company_financials
    SET sales_usd = 21375000000,
        latest_revenue = 17100000000,
        revenue_year = 2024,
        period_type = 'Annual',
        updated_at = datetime('now')
    WHERE company_id = (SELECT id FROM companies WHERE company_number = 'SC095000')
""")
main_conn.commit()
print(f"Rows updated: {mc.rowcount}")

mc.execute("""
    SELECT cf.sales_usd, cf.latest_revenue, cf.revenue_year
    FROM company_financials cf
    JOIN companies c ON c.id = cf.company_id
    WHERE c.company_number = 'SC095000'
""")
print("Lloyds after update:", mc.fetchone())
main_conn.close()
print("Done. DB guidance now has £17.1bn anchor for Lloyds.")


# === MAIN DB CHECK FOR LLOYDS REFERENCE REVENUE ===
main_conn = sqlite3.connect('data/credit_risk.db')
mc = main_conn.cursor()

mc.execute("PRAGMA table_info(company_financials)")
cols = [r[1] for r in mc.fetchall()]
print(f"company_financials columns: {cols}")

mc.execute("""
    SELECT c.id, c.company_number, c.company_name, cf.*
    FROM companies c
    LEFT JOIN company_financials cf ON c.id = cf.company_id
    WHERE c.company_number = 'SC095000'
""")
rows = mc.fetchall()
print(f"Lloyds DB row: {rows}")

# Also check what revenue columns contain for other companies that work (e.g. 03934555)
mc.execute("""
    SELECT c.company_number, c.company_name, cf.sales_usd, cf.revenue
    FROM companies c
    LEFT JOIN company_financials cf ON c.id = cf.company_id
    WHERE c.company_number IN ('03934555', 'SC095000', '03849958')
""")
rows2 = mc.fetchall()
print("Sample financials (Portsmouth, Lloyds, Admiral):")
for r in rows2:
    print(f"  {r}")
main_conn.close()

print("---")


db = 'data/vector_database.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# 1. Documents overview - using correct column names
c.execute("""
    SELECT company_name, company_number, document_type, filing_date, created_at
    FROM documents_v2
    ORDER BY created_at DESC
""")
docs = c.fetchall()
print(f"=== VECTORISED DOCUMENTS: {len(docs)} ===")
for d in docs:
    print(f"  Company: {d[0]} | CH#: {d[1]} | Type: {d[2]} | Filed: {d[3]} | Added: {str(d[4])[:10]}")

# 2. Distinct companies
c.execute("SELECT COUNT(DISTINCT company_number) FROM documents_v2")
print(f"\nDistinct companies (by CH number): {c.fetchone()[0]}")

c.execute("SELECT COUNT(DISTINCT company_name) FROM documents_v2")
print(f"Distinct companies (by name): {c.fetchone()[0]}")

# 3. Chunks breakdown
c.execute("SELECT COUNT(*) FROM document_chunks_v2")
print(f"\nTotal chunks: {c.fetchone()[0]}")

c.execute("""
    SELECT d.company_name, d.company_number, d.document_type, d.filing_date, COUNT(ch.chunk_id) as chunks
    FROM documents_v2 d
    JOIN document_chunks_v2 ch ON ch.document_id = d.document_id
    GROUP BY d.document_id
    ORDER BY chunks DESC
""")
print("\nChunks per document:")
for r in c.fetchall():
    print(f"  {r[0]} ({r[1]}) | {r[2]} | {r[3]} -> {r[4]} chunks")

# 4. Lloyds revenue context chunks - search for revenue/income/turnover
c.execute("""
    SELECT d.document_id FROM documents_v2 d WHERE d.company_number = 'SC095000'
""")
row = c.fetchone()
if row:
    doc_id = row[0]
    # Get chunks 1510-1515 (where the 28M was found)
    c.execute("""
        SELECT chunk_index, substr(content, 1, 600)
        FROM document_chunks_v2
        WHERE document_id = ? AND chunk_index BETWEEN 1510 AND 1516
        ORDER BY chunk_index
    """, (doc_id,))
    chunks = c.fetchall()
    print(f"\n=== LLOYDS REVENUE CONTEXT CHUNKS (1510-1516) ===")
    for ch in chunks:
        print(f"\n--- Chunk {ch[0]} ---\n{ch[1]}")

    # Also search for chunks containing 'income' or 'revenue'
    c.execute("""
        SELECT chunk_index, substr(content, 1, 500)
        FROM document_chunks_v2
        WHERE document_id = ? AND (
            lower(content) LIKE '%net income%'
            OR lower(content) LIKE '%total income%'
            OR lower(content) LIKE '%net interest income%'
            OR lower(content) LIKE '%17.9%' OR lower(content) LIKE '%17,9%'
            OR lower(content) LIKE '%12.4%' OR lower(content) LIKE '%12,4%'
        )
        LIMIT 5
    """, (doc_id,))
    chunks2 = c.fetchall()
    print(f"\n=== LLOYDS INCOME FIGURE CHUNKS ===")
    for ch in chunks2:
        print(f"\n--- Chunk {ch[0]} ---\n{ch[1]}")

conn.close()
