# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "praw<8",
# ]
# ///
from argparse import ArgumentParser as arg_parser
import logging
import sqlite3
import sys

import praw

LOGGER = logging.getLogger(__file__)


def init_db() -> None:
    conn = sqlite3.connect("users_log.db")
    conn.executescript(
        """CREATE TABLE IF NOT EXISTS banned (
        id VARCHAR(50) NOT NULL,
        username VARCHAR(20) NOT NULL,
        subreddit VARCHAR(30),
        duration VARCHAR(10),
        created_utc INTEGER,
        PRIMARY KEY (id)
        );
        CREATE INDEX IF NOT EXISTS idx_banned_username ON banned (username);
        CREATE INDEX IF NOT EXISTS idx_banned_created_utc ON banned (created_utc);
"""
    )
    conn.executescript(
        """CREATE TABLE IF NOT EXISTS removed (
        id VARCHAR(50) NOT NULL,
        username VARCHAR(20) NOT NULL,
        subreddit VARCHAR(30),
        target VARCHAR(10),
        post VARCHAR(10),
        created_utc INTEGER,
        PRIMARY KEY (id)
        );
        CREATE INDEX IF NOT EXISTS idx_removed_username ON removed (username);
        CREATE INDEX IF NOT EXISTS idx_removed_created_utc ON removed (created_utc);
"""
    )
    conn.commit()
    return conn


def get_last(conn: sqlite3.Connection, table: str, subreddit: str) -> str:
    before = None
    query = conn.execute(
        f"SELECT id FROM {table} WHERE subreddit=? ORDER BY created_utc DESC LIMIT 1",
        (subreddit,),
    )
    for row in query:
        before = row[0]
    LOGGER.debug("Last %s in DB: %s", table, before)
    return before


def download_banned(sub: praw.reddit.Subreddit, conn: sqlite3.Connection) -> list[dict[str, str]]:
    actions = []
    params = {"before": get_last(conn, "banned", sub.display_name)}
    for action in sub.mod.log(action="banuser", limit=1001, params=params):
        actions.append(
            (
                action.id,
                action.target_author,
                action.subreddit,
                action.details,
                action.created_utc,
            )
        )
    return actions


def download_removed(sub: praw.reddit.Subreddit, conn: sqlite3.Connection) -> list[dict[str, str]]:
    actions = []
    params = {"before": get_last(conn, "removed", sub.display_name)}
    for action in sub.mod.log(action="addremovalreason", limit=1001, params=params):
        target = next(sub._reddit.info(fullnames=[action.target_fullname]))
        actions.append(
            (
                action.id,
                action.target_author,
                action.subreddit,
                action.target_fullname,
                getattr(target, 'link_id', target.fullname),
                target.created_utc,
            )
        )
    return actions


def main(subreddits: list[str]) -> None:
    reddit = praw.Reddit()
    conn = init_db()
    for nsubreddit in subreddits:
        LOGGER.info("Sub: %s", nsubreddit)
        # fetch new actions
        rsubreddit = reddit.subreddit(nsubreddit)
        if rsubreddit.id is None:
            continue
        actions = download_banned(rsubreddit, conn)
        LOGGER.debug("Banned: %s", actions)
        conn.executemany("insert or replace into banned values (?,?,?,?,?)", actions)
        actions = download_removed(rsubreddit, conn)
        LOGGER.debug("Removed %s", actions)
        conn.executemany("insert or replace into removed values (?,?,?,?,?,?)", actions)
        conn.commit()
        LOGGER.debug("Added %d", len(actions))
    conn.close()


if __name__ == "__main__":
    """Provide the entry point to the user_since command."""
    parser = arg_parser(usage='usage: %(prog)s subreddit')
    parser.add_argument('subreddit', type=str, help='The display name of the subreddit')
    parser.add_argument(
        '--verbose', type=int, default=0, help='0 for disabled, 1 for info, more for debug')
    options = parser.parse_args()

    if options.verbose == 1:
        LOGGER.setLevel(logging.INFO)
    elif options.verbose > 1:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.NOTSET)
    LOGGER.addHandler(logging.StreamHandler())
    main([options.subreddit])



    