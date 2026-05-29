# pyright: standard
"""
  Load JSON data of firms to database
"""
import sqlite3
import json
from pathlib import Path

json_dir = Path("firms")

DB_PATH = "firms.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS firms (
    id TEXT PRIMARY KEY,
    name TEXT,
    data JSON
    address_name TEXT,
    rating REAL,
    review_count INT,
    star_count INT,
    org_rating REAL,
    org_review_count INT,
    org_star_count INT,
    rubrics TEXT
)
""")

# cur.execute("""
# CREATE TABLE IF NOT EXISTS places(
#     id TEXT PRIMARY KEY,
#     geometry_id TEXT,
#     is_advert INT,
#     name TEXT,
#     extension TEXT,
#     lat REAL,
#     lon REAL,
#     context JSON,
#     reviews JSON,
#     data JSON
# )
# """)

# prev json schema (on first page or when ad is on, i didnt understand)
# id_:str = item.get("id")
# geometry_id:str = item.get("geometry_id")
# is_advert = 1 if bool(item.get("is_advertising")) else 0
# name:str = item.get("name_ex", {}).get("primary")
# extension:str = item.get("name_ex", {}).get("extension")
# lat:float = item.get("lat")
# lon:float = item.get("lon")
# context:str = json.dumps(item.get("context"), ensure_ascii=False)
# reviews:str = json.dumps(item.get("reviews"), ensure_ascii=False)
# raw_json:str = json.dumps(item, ensure_ascii=False)

# Обработка файлов
for file in json_dir.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        obj = json.load(f)

    items = obj.get("body", {}).get("result", {}).get("items", [])
    for item in items:
        # Get basic data
        id_:str = item.get("id").split("_")[0]
        # print(id_)
        # geometry_id:str = item.get("geometry_id")
        # is_advert = 1 if bool(item.get("is_advertising")) else 0
        name:str = item.get("name_ex", {}).get("primary")
        # extension:str = item.get("name_ex", {}).get("extension")
        # lat:float = item.get("lat")
        # lon:float = item.get("lon")
        # context:str = json.dumps(item.get("context"), ensure_ascii=False)
        # reviews:str = json.dumps(item.get("reviews"), ensure_ascii=False)
        raw_json:str = json.dumps(item, ensure_ascii=False)

        cur.execute("""
        INSERT OR REPLACE INTO firms (id, name, data)
        VALUES (?,?,?)
        """, (id_, name, raw_json))

        # cur.execute("""
        # INSERT OR REPLACE INTO places (id, geometry_id, is_advert, name, extension, lat, lon, context,reviews, data)
        # VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?)
        # """, (id_, geometry_id, is_advert, name, extension, lat, lon, context, reviews, raw_json))

conn.commit()
conn.close()
print("Finished loading data")

"""
  Extracts data from JSON from "data" column and put in new columns.
  New columns needed to be created manually
"""

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT id, data FROM firms")
firms = cursor.fetchall()
for id_, json_str in firms:
  json_data = json.loads(json_str)
  reviews = json_data.get("reviews", {})
  # print(reviews)
  rating = reviews.get("general_rating")
  review_num = reviews.get("general_review_count")
  star_num = reviews.get("general_review_count_with_stars")
  org_rating = reviews.get("org_rating")
  org_review_num = reviews.get("org_review_count")
  org_star_num = reviews.get("org_review_count_with_stars")
  rubrics = json_data.get("rubrics", [])
  rubrics_names = []
  for rubric in rubrics:
    rubric_name = rubric.get("name")
    rubrics_names.append(rubric_name)
  address_name = json_data.get("address_name")
  cursor.execute("""
UPDATE firms SET
  address_name = ?,
  rating = ?,
  review_count = ?,
  star_count = ?,
  org_rating = ?,
  org_review_count = ?,
  org_star_count = ?,
  rubrics = ?
WHERE id = ?;""", (address_name, rating, review_num, star_num, org_rating, org_review_num, org_star_num, str(rubrics_names), id_))
  conn.commit()

conn.close()


