"""Post new submission to Slack"""
import logging
import sqlite3
from sys import argv

import requests
from praw import Reddit

AGENT = "python:post_slack:0.1 (by /u/timendum)"

LOGGER = logging.getLogger(__file__)


def main(subreddit, hook_url):
    conn = sqlite3.connect("reddit.db")

    # Prepare table
    conn.execute(
        """CREATE TABLE IF NOT EXISTS post_slack (
        subreddit VARCHAR(100) NOT NULL,
        created_utc int,
        PRIMARY KEY (subreddit)
        )
"""
    )
    conn.commit()
    # Fetch created_utc
    created_utc = 0
    c = conn.cursor()
    c.execute("SELECT created_utc FROM post_slack WHERE subreddit = ?", [subreddit])
    row = c.fetchone()
    if row:
        created_utc = row[0]
    c.close()
    LOGGER.debug("Latest created_utc %i", created_utc)
    reddit = Reddit(check_for_updates=False)
    rsubreddit = reddit.subreddit(subreddit)
    new_created_utc = 0
    for submission in reversed(list(rsubreddit.new(limit=3))):
        LOGGER.debug("Found %s", submission)
        if not submission.author or submission.removed:
            # deleted or removed
            LOGGER.debug("Skipped: deleted or removed")
            continue
        if submission.created_utc > created_utc:
            LOGGER.debug("OK: %i", submission.created_utc)
            new_created_utc = max(new_created_utc, submission.created_utc)
            r = requests.post(
                hook_url,
                data={
                    "payload": '{{"text": "New post: <https://redd.it/{}|{}> by {}"}}'.format(
                        submission.id, submission.title, submission.author.name
                    )
                },
            )
    if new_created_utc:
        conn.execute(
            "INSERT OR REPLACE INTO post_slack (created_utc, subreddit) VALUES  (?, ?)",
            (new_created_utc, subreddit),
        )
        conn.commit()
        LOGGER.debug("Updated created_utc %i", new_created_utc)
    conn.close()


if __name__ == "__main__":
    if len(argv) < 3:
        print("Invoke the program with subreddit and HOOK_URL")
    else:
        main(argv[1], argv[2])
