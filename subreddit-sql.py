"""Utility to save submissions, comments and awards from a subreddit into a sqlite database and keep it updated."""
from argparse import ArgumentParser as arg_parser
from datetime import datetime, UTC
import sqlite3
import logging
from praw import Reddit

LOGGER = logging.getLogger(__file__)

SECONDS_IN_DAY = 60 * 60 * 24


class SubredditDump(object):
    def __init__(self, subreddit):
        """Initialize the SubredditStats instance with config options."""
        self.reddit = Reddit(check_for_updates=False)
        if not self.reddit.user.me():
            print(self.reddit.auth.url(scopes=["read", "identity"], state=""))
        self.subreddit = self.reddit.subreddit(subreddit)
        self.con = sqlite3.connect(f"{subreddit}.db")
        self._init_sql()
        self.submissions = []
        self.comments = []
        self._now = int(datetime.now(UTC).timestamp())

    def _init_sql(self) -> None:
        self.con.execute(
            """
CREATE TABLE IF NOT EXISTS submissions(
    id TEXT PRIMARY KEY,
    title TEXT,
    score INTEGER,
    upvote_ratio REAL,
    author TEXT,
    permalink TEXT,
    created_utc INTEGER,
    domain TEXT,
    selftext TEXT,
    link TEXT,
    flair_text TEXT,
    flair_class TEXT,
    num_comments INTEGER,
    over_18 BOOLEAN,
    distinguished BOOLEAN,
    removed BOOLEAN,
    removed_by_category TEXT,
    locked BOOLEAN,
    last_update NOT NULL)"""
        )
        self.con.execute(
            """
CREATE TABLE IF NOT EXISTS submissions_awards(
    id TEXT PRIMARY KEY,
    submission_id TEXT,
    name TEXT,
    count INTEGER,
    award_type TEXT,
    coin_price INTEGER,
    last_update NOT NULL)"""
        )
        self.con.execute(
            """
CREATE TABLE IF NOT EXISTS comments(
    id TEXT PRIMARY KEY,
    score INTEGER,
    author TEXT,
    submission_id TEXT,
    created_utc INTEGER,
    parent_id TEXT,
    body TEXT,
    distinguished BOOLEAN,
    removed BOOLEAN,
    collapsed BOOLEAN,
    locked BOOLEAN,
    last_update NOT NULL)"""
        )
        self.con.execute(
            """
CREATE TABLE IF NOT EXISTS comments_awards(
    id TEXT PRIMARY KEY,
    comment_id TEXT,
    submission_id TEXT,
    name TEXT,
    count INTEGER,
    award_type TEXT,
    coin_price INTEGER,
    last_update NOT NULL)"""
        )
        self.con.execute(
            """
CREATE TABLE IF NOT EXISTS traffics(
    day INTEGER PRIMARY KEY,
    pageviews INTEGER,
    uniques INTEGER,
    new_members INTEGER)"""
        )
        self.con.commit()

    def fetch_recent_submissions(self, days_old: int) -> None:
        """Fetch recent submissions in subreddit with boundaries.

        :param days_old: The number of days to include

        """

        LOGGER.debug("Fetching submissions newer than %s days", days_old)
        min_date = datetime.now(UTC).timestamp() - SECONDS_IN_DAY * days_old
        for submission in self.subreddit.new(limit=None):
            submission.comment_sort = "top"
            if submission.created_utc <= min_date:
                continue
            self.submissions.append(submission)

    def fetch_recent_traffics(self, days_old: int) -> None:
        """Fetch traffics stats in subreddit with boundaries.

        :param days_old: The number of days to include

        """

        LOGGER.debug("Fetching traffic newer than %s days", days_old)
        traffic = self.subreddit.traffic()["day"]
        timelimit = int(datetime.now().timestamp()) - days_old * 60 * 60 * 24
        self.traffic = [row for row in traffic if row[0] > timelimit]

    def process_traffics(self) -> None:
        """Write submissions to sql."""
        LOGGER.debug("Processing %d traffic rows", len(self.traffic))
        self.con.executemany(
            """INSERT OR REPLACE INTO traffics
(day, pageviews, uniques, new_members) VALUES(?, ?, ?, ?)""",
            self.traffic,
        )
        self.con.commit()

    def process_submissions(self) -> None:
        """Write submissions file."""
        LOGGER.debug("Processing %d submissions", len(self.submissions))
        dsubmissions = []
        dawards = []
        for s in self.submissions:
            dsubmissions.append(
                (
                    s.id,
                    s.title,
                    s.score,
                    s.upvote_ratio,
                    s.author.name if s.author else "[deleted]",
                    s.permalink,
                    s.created_utc,
                    s.domain,
                    getattr(s, "selftext", None),
                    getattr(s, "url", None),
                    s.link_flair_text,
                    s.link_flair_css_class,
                    s.num_comments,
                    s.over_18,
                    s.distinguished,
                    s.removed,
                    s.removed_by_category,
                    s.locked,
                    self._now,
                )
            )
            for award in s.all_awardings:
                dawards.append(
                    (
                        award["id"],
                        s.id,
                        award["name"],
                        award["count"],
                        award["award_type"],
                        award["coin_price"],
                        self._now,
                    )
                )
        self.con.executemany(
            """INSERT INTO submissions
    (id, title, score, upvote_ratio, author, permalink, created_utc, domain, selftext, link,
    flair_text, flair_class, num_comments, over_18, distinguished, removed, removed_by_category,
    locked, last_update)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
    score=excluded.score, upvote_ratio=excluded.upvote_ratio, selftext=excluded.selftext,
    flair_text=excluded.flair_text, flair_class=excluded.flair_class,
    num_comments=excluded.num_comments, over_18=excluded.over_18,
    distinguished=excluded.distinguished, removed=excluded.removed,
    removed_by_category=excluded.removed_by_category,
    locked=excluded.locked, last_update=excluded.last_update""",
            dsubmissions,
        )
        if dawards:
            LOGGER.debug("Processing %d submission awards", len(dawards))
            self.con.executemany(
                """INSERT OR REPLACE INTO submissions_awards
    (id, submission_id, name, count, award_type, coin_price, last_update)
    VALUES(?, ?, ?, ?, ?, ?, ?)""",
                dawards,
            )

        self.con.commit()

    def fetch_comments_from_submissions(self) -> None:
        for index, submission in enumerate(self.submissions):
            if submission.num_comments == 0:
                continue

            more_comments = submission.comments.replace_more(limit=None)
            if more_comments:
                skipped_comments = sum(x.count for x in more_comments)
                LOGGER.info(
                    "Skipped %d MoreComments (%d comments) on %s",
                    len(more_comments),
                    skipped_comments,
                    submission,
                )

            LOGGER.debug(
                "Fetched %d comments on %d/%d submissions",
                len(submission.comments.list()),
                index + 1,
                len(self.submissions),
            )
            self.comments.extend(submission.comments.list())

    def process_comments(self) -> None:
        """Write comments to sql."""
        LOGGER.debug("Processing %d comments", len(self.comments))
        dcomments = []
        dawards = []
        for c in self.comments:
            dcomments.append(
                (
                    c.id,
                    c.score,
                    c.author.name if c.author else "[deleted]",
                    c.link_id[3:],
                    c.created_utc,
                    c.parent_id,
                    c.body,
                    c.distinguished,
                    c.removed,
                    c.collapsed,
                    c.locked,
                    self._now,
                )
            )
            for award in c.all_awardings:
                dawards.append(
                    (
                        award["id"],
                        c.id,
                        c.link_id[3:],
                        award["name"],
                        award["count"],
                        award["award_type"],
                        award["coin_price"],
                        self._now,
                    )
                )
        self.con.executemany(
            """INSERT INTO comments
    (id, score, author, submission_id, created_utc, parent_id, body, distinguished, removed,
    collapsed,  locked, last_update)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
    score=excluded.score, distinguished=excluded.distinguished, removed=excluded.removed,
    collapsed=excluded.collapsed, locked=excluded.locked, last_update=excluded.last_update,
    parent_id=excluded.parent_id""",
            dcomments,
        )
        if dawards:
            LOGGER.debug("Processing %d comment awards", len(dawards))
            self.con.executemany(
                """INSERT OR REPLACE INTO comments_awards
    (id, comment_id, submission_id, name, count, award_type, coin_price, last_update)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                dawards,
            )

        self.con.commit()

    def run(self, refresh_old: int, days_old: int) -> None:
        """Run stats and return the created Submission."""
        LOGGER.info("Analyzing subreddit: %s", self.subreddit.display_name)

        # RECENT
        self.fetch_recent_submissions(days_old)
        if not self.submissions:
            LOGGER.warning("No submissions were found.")
        else:
            self.process_submissions()
            self.fetch_comments_from_submissions()
            if not self.comments:
                LOGGER.warning("No comments were found.")
            else:
                self.process_comments()
        self.fetch_recent_traffics(days_old)
        if self.traffic:
            self.process_traffics()
        else:
            LOGGER.warning("No traffic were found.")
        # REFRESH
        self.submissions = []
        self.comments = []
        self.fetch_submissions_to_refresh(refresh_old, days_old)
        if not self.submissions:
            LOGGER.info("No submissions to refresh were found.")
        else:
            self.process_submissions()
            self.fetch_comments_from_submissions()
            if not self.comments:
                LOGGER.info("No comments were found.")
            else:
                self.process_comments()

    def fetch_submissions_to_refresh(self, refresh_old: int, days_old: int) -> None:
        """Fetch submissions in database to be refreshed.

        :param refresh_old: The number of days submissions need to be older then to be refreshed
        :param days_old: The number of days to include

        """

        LOGGER.debug(
            "Fetching submissions between %d and %d days old",
            refresh_old,
            refresh_old - days_old,
        )
        min_date = datetime.now(UTC).timestamp() - refresh_old * SECONDS_IN_DAY
        max_date = min_date + SECONDS_IN_DAY * days_old
        cur = self.con.cursor()
        res = cur.execute(
            "SELECT id from submissions where last_update BETWEEN ? AND ?",
            (min_date, max_date),
        )
        for row in res:
            self.submissions.append(self.reddit.submission(id=row[0]))


def main() -> int:
    """Provide the entry point to the subreddit_stats command."""
    parser = arg_parser()
    parser.add_argument("subreddit", type=str, help="The subreddit to be analyzed")
    parser.add_argument("days_old", type=int, help="Days to be fetched and refreshed")
    parser.add_argument("refresh_old", type=int, help="Update contents older than")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbose level"
    )

    options = parser.parse_args()

    try:
        LOGGER.setLevel([logging.NOTSET, logging.INFO, logging.DEBUG][options.verbose])
    except IndexError:
        LOGGER.setLevel(logging.DEBUG)

    LOGGER.addHandler(logging.StreamHandler())

    srs = SubredditDump(options.subreddit)
    srs.run(options.refresh_old, options.days_old)
    return 0


if __name__ == "__main__":
    main()
