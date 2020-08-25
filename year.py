"""Fetch submission from Pushshift, refresh data from Reddit and save to CSV"""
import csv
from datetime import datetime

import praw
from psaw import PushshiftAPI

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
    "locked",
    "over_18",
    "title",
]


def main():
    now = datetime.now()
    after = int((datetime(now.year, 1, 1) - datetime(1970, 1, 1)).total_seconds())
    before = int((datetime(now.year + 1, 1, 1) - datetime(1970, 1, 1)).total_seconds())

    year = now.year
    filename = "year-{}.csv".format(year)

    reddit = praw.Reddit(disable_update_check=True)
    api = PushshiftAPI()

    submissions = api.search_submissions(
        limit=1000000, subreddit="italy", after=after, before=before
    )

    processed_ids = set()
    try:
        with open(filename, "r", newline="", encoding="utf-8") as filecsv:
            reader = csv.reader(filecsv)
            processed_ids = {row[0] for row in reader}
    except FileNotFoundError:
        with open(filename, "w", newline="", encoding="utf-8") as filecsv:
            writer = csv.writer(filecsv)
            writer.writerow(ATTRS)

    with open(filename, "a", newline="", encoding="utf-8") as filecsv:
        writer = csv.writer(filecsv)
        try:
            for ps in submissions:
                if ps.id in processed_ids:
                    continue
                rs = reddit.submission(ps.id)
                writer.writerow([getattr(rs, attr) for attr in ATTRS])
                print(".", end="", flush=True)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
