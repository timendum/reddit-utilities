"""Utility to provide submission and comment statistics in a subreddit."""
from collections import defaultdict
from datetime import datetime
from argparse import ArgumentParser as arg_parser
import csv
import logging
import re
import time


from praw import Reddit
from praw.models import Submission, Comment


AGENT = 'python:reddit-stats:0.1 (by /u/timendum)'

logger = logging.getLogger(__file__)

class customDialect(csv.Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL


class SubredditStats(object):
    """Contain all the functionality of the subreddit_stats command."""

    def __init__(self, subreddit):
        """Initialize the SubredditStats instance with config options."""
        self.comments = []
        self.submissions = []
        self.reddit = Reddit(check_for_updates=False, user_agent=AGENT)
        self.subreddit = self.reddit.subreddit(subreddit)

    def fetch_gold(self):
        """Fetch recent glided content.
        """
        for gilded in self.subreddit.gilded():
            if isinstance(gilded, Comment):
                self.comments.append(gilded)
            else:
                self.submissions.append(gilded)
    
    def process_gilded(self):
        """Write gilded file."""
        filename = '%s-gilded.csv' % self.base_filename
        logger.debug('Processing gilded to %s' % filename)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect=customDialect)
            writer.writerow(['id', 'author', 'score ', 'permalink', 'link_id', 'created_utc', 'distinguished', 'gilded'])
            for c in self.submissions:
                writer.writerow([c.id, c.author, c.score, c.permalink, c.id, c.created_utc, c.distinguished, c.gilded])
            for c in self.comments:
                writer.writerow([c.id, c.author, c.score, c.permalink(fast=True), c.link_id, c.created_utc, c.distinguished, c.gilded])
        return filename

    def run(self):
        """Run stats and return the created Submission."""
        logger.info('Analyzing subreddit: {}'.format(self.subreddit))
        self.base_filename = '%s-%d' % (str(self.subreddit), time.time())

        self.fetch_gold()

        if not self.comments and not self.submissions:
            logger.warning('No submissions were found.')
            return

        return self.process_gilded()


def main():
    """Provide the entry point to the subreddit_stats command."""
    parser = arg_parser(usage='usage: %(prog)s [options] SUBREDDIT')
    parser.add_argument('subreddit', type=str,
                    help='The subreddit to be analyzed')
    parser.add_argument('--verbose', type=int, default=0,
                    help='0 for disabled, 1 for info, more for debug')

    options = parser.parse_args()

    if options.verbose == 1:
        logger.setLevel(logging.INFO)
    elif options.verbose > 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.NOTSET)
    logger.addHandler(logging.StreamHandler())

    srs = SubredditStats(options.subreddit)
    files = srs.run()
    if files:
        print('Written files: %s' % ' '.join(files))
    return 0

if __name__ == "__main__":
    main()