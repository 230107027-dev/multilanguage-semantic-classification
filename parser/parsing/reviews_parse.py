# pyright: standard
"""
  Scrapes reviews of firms using HTTP requests.
  If we try to send request using curl/requests library, even with correct headers it will not works,
  because 2gis will be need for key attribute that i don't know how to easily get and save.
  So, easiest approach is to use Playwright, and send request using browser itself.
  I think using headless mode will works but not tested. Also async with many browsers will work,
  i guess, but i have no purpose for write code for it.
"""
import random
from playwright.sync_api import sync_playwright
import sqlite3
import json
import time
from pathlib import Path
from urllib.parse import urlparse
import hashlib

# Database that contains firms (restaraunts)
DB_PATH = "firms.db"
REVIEW_DIR = Path("reviews")
REVIEW_DIR.mkdir(exist_ok=True)

def get_firm_ids_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM firms")  # get ids of firms (branches)
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids

def save_review_response(response):
    try:
        if response.url.startswith("https://public-api.reviews.2gis.com/2.0/branches"):
            parsed = urlparse(response.url)
            path_parts = parsed.path.strip("/").split("/")

            if "branches" in path_parts:
                idx = path_parts.index("branches")
                firm_id = path_parts[idx + 1]
            else:
                print(f"Could not extract firm ID from {response.url}")
                return

            endpoint_name = "_".join(path_parts)  # e.g., 2.0_branches_<id>_reviews
            qs_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:6]
            # Filename based on branch id and hash of response
            filename = f"{endpoint_name}_{qs_hash}.json"

            firm_dir = REVIEW_DIR / str(firm_id)
            firm_dir.mkdir(exist_ok=True)

            # Usually only JSONs
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                data = response.json()
            else:
                data = {'raw_content': response.text()}

            full_data = {
                'request_url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
                'body': data
            }

            with open(firm_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)

            print(f"Saved review data for firm {firm_id}: {filename}")
    except Exception as e:
        print(f"Error saving review: {e}")

def scrape_reviews():
    firm_ids = get_firm_ids_from_db()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Blocking unnecessary data types
        blocked_types = {"image", "font", "stylesheet"}

        context.route("**/*", lambda route, request: (
            route.abort() if request.resource_type in blocked_types else route.continue_()
        ))

        # We are saving initial requests for branches (the first one)
        collected_requests = {}

        def intercept_response(response):
            if response.url.startswith("https://public-api.reviews.2gis.com/2.0/branches"):
                parsed = urlparse(response.url)
                path_parts = parsed.path.strip("/").split("/")
                if "branches" in path_parts:
                    idx = path_parts.index("branches")
                    firm_id = path_parts[idx + 1]
                else:
                    return
                collected_requests[firm_id] = response.url

                save_review_response(response)

        page.on('response', intercept_response)

        for firm_id in firm_ids:
            if (REVIEW_DIR / str(firm_id)).exists():
              print(f"Skipping already scraped firm {firm_id}")
              continue

            url = f"https://2gis.kz/almaty/firm/{firm_id}"
            print(f"Opening: {url}")

            try:
                page.goto(url, wait_until='networkidle')

                # Press button "Отзывы"
                review_tab = page.locator('text=Отзывы')
                review_tab.scroll_into_view_if_needed()
                review_tab.click()

                page.wait_for_timeout(500)

                btn = page.get_by_role("button", name='Загрузить ещё', exact=True).first
                btn.wait_for(state="visible", timeout=500)
                btn.scroll_into_view_if_needed()
                btn.click()
                page.wait_for_timeout(500)

                api_url = collected_requests.get(str(firm_id))
                if not api_url:
                    print(f"No API call captured for firm {firm_id}")
                    continue

                # After collecting initial request, we are generating subsequent requests with modified offset
                # Why not just scroll down and press button? It's very slow and handles maximum 1000 req/s
                # With generating requests manually, speed increases and limits only by opening new pages of firms.
                #
                parsed = urlparse(api_url)
                base_url = api_url.split("?")[0]
                qs = dict([part.split("=", 1) for part in parsed.query.split("&")])

                # Initial offset (the first 50 we are consume by pressing "Отзывы", the next 50-100 by pressing "Загрузить еще")
                offset = 100

                first_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in qs.items())}"
                first_resp = page.request.get(first_url)
                first_json = first_resp.json()
                # save_review_response(first_resp)

                # Maximum amount of reviews that we can get, parsed from first response
                total = int(first_json.get("meta", {}).get("branch_reviews_count", 0))

                while offset < total:
                    # Set new offset and create new url request
                    qs["offset"] = str(offset)
                    full_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in qs.items())}"
                    print(f"Fetching offset {offset}")
                    try:
                        resp = page.request.get(full_url)
                        save_review_response(resp)
                        offset += int(qs.get("limit", 50))
                        time.sleep(random.randint(50, 100)/100)
                    except Exception as e:
                        print(f"Failed to fetch offset={offset} for firm {firm_id}: {e}")
                        break

            except Exception as e:
                print(f"Error while scraping {firm_id}: {e}")
                continue

        input("Press Enter to close browser...")
        browser.close()

scrape_reviews()
