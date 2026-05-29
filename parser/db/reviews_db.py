# pyright: standard
"""
  Create reviews database and fill it
"""
import json
import sqlite3
from glob import glob

json_paths = glob("reviews/*/*.json")

conn = sqlite3.connect("reviews.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    branch_id TEXT,
    user_id TEXT,
    user_name TEXT,
    text TEXT,
    clean_text TEXT,
    rating INTEGER,
    date_created TEXT,
    is_hidden BOOLEAN,
    official_reply TEXT,
    topics TEXT,
    firm_name TEXT,
    firm_address TEXT,
    firm_rubrics TEXT
)
""")
conn.commit()

for path in json_paths:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        reviews = data.get("body", {}).get("reviews", [])
        for review in reviews:
            # print(review)
            review_id = review["id"]
            branch_id = review["object"]["id"]
            user_id = review["user"]["id"]
            user_name = review["user"]["name"]
            text = review.get("text", "")
            rating = review.get("rating", None)
            date_created = review.get("date_created", "")
            is_hidden = review.get("is_hidden", False)
            official_answer = review.get("official_answer", {})
            official_reply = ""
            if official_answer:
              official_reply = official_answer.get("text", None)

            cursor.execute("""
            INSERT OR IGNORE INTO reviews (
                id, branch_id, user_id, user_name, text, rating, date_created,
                is_hidden, official_reply
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review_id, branch_id, user_id, user_name, text, rating,
                date_created, is_hidden, official_reply
            ))

        print(f"✓ Processed: {path}")

    except Exception as e:
        print(f"⚠️ Failed to process {path}: {e}")
        input()

conn.commit()
conn.close()

"""
  Clean reviews
"""
import re

def clean_text(text: str):
    text = re.sub(r"\s+", " ", text)  # many spaces in one
    text = re.sub(r"[^\w\s.,!?–—-]", "", text)  # delete other characters than letters, numbers
    return text.strip()

import sqlite3

conn = sqlite3.connect("reviews.db")
cursor = conn.cursor()

cursor.execute("SELECT id, text FROM reviews")
rows = cursor.fetchall()

for review_id, text in rows:
    cleaned = clean_text(text)
    cursor.execute("UPDATE reviews SET clean_text = ? WHERE id = ?", (cleaned, review_id))

conn.commit()
conn.close()


"""
  Set firms data for reviews
"""

conn_review = sqlite3.connect("reviews.db")
conn_firm = sqlite3.connect("firms.db")
cursor_firm = conn_firm.cursor()
cursor_review = conn_review.cursor()
cursor_review.execute("SELECT id, branch_id FROM reviews where firm_name is null;")
reviews = cursor_review.fetchall()
cursor_firm.execute("select id, name, address_name, rubrics from firms;")
firms_arr = cursor_firm.fetchall()
conn_firm.close()
firms = {}
for id_, name, address_name, rubrics in firms_arr:
  firms[id_] = (name, address_name, rubrics)

# Process in batches (much faster)
BATCH_SIZE = 1000

try:
    for i in range(0, len(reviews), BATCH_SIZE):
        batch = reviews[i:i+BATCH_SIZE]
        updates = []

        for id_, firm_id in batch:
            if firm_id in firms:
                name, address_name, rubrics = firms[firm_id]
                updates.append((name, address_name, str(rubrics), id_))

        if updates:
            cursor_review.executemany("""
                UPDATE reviews SET
                    firm_name = ?,
                    firm_address = ?,
                    firm_rubrics = ?
                WHERE id = ?;""", updates)
            conn_review.commit()
            print(f"Processed {i+BATCH_SIZE if i+BATCH_SIZE < len(reviews) else len(reviews)}/{len(reviews)} reviews")
finally:
    conn_review.close()

conn_review.close()


