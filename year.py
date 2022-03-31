"""Fetch submission from Pushshift, refresh data from Reddit and save to CSV"""
import csv
from datetime import datetime

import praw
from psaw import PushshiftAPI

DELTA_YEAR = 0  # 0 = current, 1 = past

ATTRS = [
    "id",
    "score",
    "author",
    "permalink",
    "created_utc",
    "gilded",
    "total_awards_received",
    "num_comments",
    "domain",
    "url",
    "upvote_ratio",
    "removed",
    "removed_by_category",
    "locked",
    "over_18",
    "title",
]


def main():

    after = int((datetime(now.year - DELTA_YEAR, 1, 1) - datetime(1970, 1, 1)).total_seconds())
    before = int((datetime(now.year + 1 - DELTA_YEAR, 1, 1) - datetime(1970, 1, 1)).total_seconds())

    filename = f"year-{now.year - DELTA_YEAR}.csv"

    reddit = praw.Reddit(disable_update_check=True)
    api = PushshiftAPI()

    processed_ids = set()
    try:
        with open(filename, "r", newline="", encoding="utf-8") as filecsv:
            reader = csv.reader(filecsv)
            rows = list(reader)
        processed_ids = {row[0] for row in rows}
        after = int(min([float(row[4]) for row in rows[1:]]))
        print("Continuing after:", after)
    except FileNotFoundError:
        with open(filename, "w", newline="", encoding="utf-8") as filecsv:
            writer = csv.writer(filecsv)
            writer.writerow(ATTRS)

    submissions = api.search_submissions(
        limit=1000000, subreddit="italy", after=after, before=before
    )
    
    errors = []
    with open(filename, "a", newline="", encoding="utf-8") as filecsv:
        writer = csv.writer(filecsv)
        try:
            for ps in submissions:
                if ps.id in processed_ids:
                    print("-", end="", flush=True)
                    continue
                try:
                    rs = reddit.submission(ps.id)
                    writer.writerow([getattr(rs, attr) for attr in ATTRS])
                    print(".", end="", flush=True)
                except Exception as e:
                    errors.append(ps.id)
                    print("Error with", ps.id, e)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
