# pyright: standard
"""
Sends reviews to Gemini for topic labeling
"""

import time
import os
import json
import re
import untruncate_json
from dotenv import load_dotenv
import sqlite3
import enum
from pydantic import BaseModel
from google import genai
import asyncio
# from tqdm.asyncio import tqdm_asyncio # Optional: for progress bar

load_dotenv()

class Topic(enum.Enum):
    """Topics of reviews that Gemini will consider for choose for labeling.
    Last two was added because of my curiosity, but they are not correctly
    handled by Gemini and deleted in last version of dataset after cleaning."""
    DELICIOUS_FOOD = "delicious food"
    TASTELESS_FOOD = "tasteless food"
    LONG_WAIT = "long wait"
    SHORT_WAIT = "short wait"
    IS_DELIVERY = "is delivery"
    GOOD_LOCATION = "good location"
    BAD_LOCATION = "bad location"
    GOOD_STAFF = "good staff"
    BAD_STAFF = "bad staff"
    GOOD_SERVICE = "good service"
    BAD_SERVICE = "bad service"
    PLEASANT_AMBIANCE = "pleasant ambience"
    UNPLEASANT_AMBIANCE = "unpleasant_ambiance"
    EXPENSIVE_PRICE = "expensive price"
    REASONABLE_PRICE = "reasonable price"
    GOOD_OVERALL = "overall good"
    BAD_OVERALL = "overall bad"
    SMALL_PORTION = "small portion"
    IGNORANCE_KAZAKH = "ignorance of kazakh"
    IGNORANCE_RUSSIAN = "ignorance of russian"

class Review(BaseModel):
    id: int
    topics: list[Topic]

def remove_newlines_in_json_strings(json_text):
    """Because Gemini 2.0 Flash has 8k token output, it truncated output to ~200 reviews,
      so we are need to maximize outputed reviews and handle truncated jsons, using
      untruncated_json library. But it not handles situations when strings goes to new line,
      and because its not allowed in JSON it cannot be correctly parsed. so fix it by this function."""
    # This pattern finds strings: " ... " possibly spanning multiple lines
    # It replaces newlines (\n or \r\n) inside quotes with a space
    def replacer(match):
        s = match.group(0)
        return s.replace('\n', ' ').replace('\r', ' ')

    # Match strings in JSON: "anything" — including multiline
    string_pattern = re.compile(r'"(?:[^"\\]|\\.|\\\n)*?"', re.DOTALL)
    return string_pattern.sub(replacer, json_text)

conn = sqlite3.connect("reviews.db")
cursor = conn.cursor()

# put Google AI studio api key to .env

api=os.getenv("api")
client = genai.Client(api_key=api)

def get_reviews(num: int):
    cursor.execute(f"""
        SELECT id, clean_text
        FROM reviews
        WHERE topics IS NULL
          AND clean_text is NOT NULL
        ORDER BY RANDOM()
        LIMIT {num};
    """)
    return cursor.fetchall()

def reviews_to_chunks(reviews, num):
    """Split large amount of reviews to smaller chunks because of limited tokens of LLM"""
    result = []
    for i in range(0, len(reviews), num):
        chunk = reviews[i:i+num]
        result.append(chunk)
    return result

def chunks_to_json(chunks):
    result = []
    for chunk in chunks:
        json_data = [{"id": id_, "text": text} for id_,text in chunk]
        json_str = json.dumps(json_data, ensure_ascii = False, indent=2)
        result.append(json_str)
    return result

async def process_chunk(json_str: str):
    """Sends a single chunk to the API and processes the response."""

    request = f"""You are a helpful assistant for tagging customer reviews with multiple relevant topics. Given a JSON array of reviews with ids, analyze its content and return topics that review contains and id of that review. Reviews generally in Russian and Kazakh language.
    {json_str}
    """

    print("Sending request for a chunk...")
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=request,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[Review],
            },
        )

        print("Received response for a chunk")
        text = response.text
        if not text:
            print("Empty response text")
            return []

        # Handle truncated json
        json_text = untruncate_json.complete(text)
        json_text = remove_newlines_in_json_strings(json_text)
        arr = json.loads(json_text)
        return arr

    except Exception as e:
        print(f"Error processing chunk: {e}")
        return []

random_reviews = [0]
i = 0
times = []
async def main():
    global i # Access the global counter

    while True: # Loop continues as long as get_reviews returns data
        start_time = time.time()

        reviews = get_reviews(4000)
        if not reviews: # Stop if no more reviews to process
            break

        chunks = reviews_to_chunks(reviews, 200) # Split to chunks
        jsons = chunks_to_json(chunks)

        # Create a list of coroutines for the API calls
        tasks = [process_chunk(json_str) for json_str in jsons]

        # Run the API calls concurrently
        # Use tqdm_asyncio.gather for a progress bar if desired
        # results = await tqdm_asyncio.gather(*tasks)
        results = await asyncio.gather(*tasks)


        processed_count = 0
        for arr in results:
            if not arr:
                continue

            # Process the results and update the database (sequentially is safer for sqlite)
            for item in arr:
                 # Ensure item has expected structure and 'topics' is a list
                if isinstance(item, dict) and 'id' in item and 'topics' in item and isinstance(item['topics'], list):
                    cursor.execute("""
                        UPDATE reviews
                        SET topics = ?
                        WHERE id = ?;
                    """, (str(item["topics"]), item["id"]))
                    processed_count += 1
                else:
                    print(f"Skipping unexpected item structure: {item}")


        conn.commit()
        end_time = time.time()
        print(f"Commited {processed_count} reviews in this iteration.")
        print(f"Iteration {i} took {end_time-start_time:.2f} seconds")
        times.append(end_time-start_time)
        print(f"Avg time per iteration: {sum(times)/len(times):.2f} seconds")
        i += 1

    conn.close()
    print("Finished processing all reviews.")

if __name__ == "__main__":
    asyncio.run(main())
