"""Utility to provide submission and comment statistics in a subreddit."""
from collections import defaultdict
from datetime import datetime
from argparse import ArgumentParser as arg_parser
import csv
import logging
import re
import time


from praw import Reddit
from praw.models import Submission


DAYS_IN_SECONDS = 60 * 60 * 24
TOP_VALUES = {'all', 'day', 'month', 'week', 'year'}
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
        self.min_date = 0
        # less then 7 days
        self.max_date = time.time() # - DAYS_IN_SECONDS * 7
        self.reddit = Reddit(check_for_updates=False, user_agent=AGENT)
        self.subreddit = self.reddit.subreddit(subreddit)

    def fetch_recent_submissions(self, max_duration):
        """Fetch recent submissions in subreddit with boundaries.

        Does not include posts within the last 7 days as their scores may not be
        representative.

        :param max_duration: When set, specifies the number of days to include

        """
        if max_duration:
            self.min_date = self.max_date - DAYS_IN_SECONDS * max_duration
        logger.debug('Fetching submissions between %i and %i' % (self.min_date, self.max_date))
        for submission in self.subreddit.new(limit=None):
            if submission.created_utc <= self.min_date:
                break
            if submission.created_utc > self.max_date:
                continue
            self.submissions.append(submission)

    def fetch_top_submissions(self, top):
        """Fetch top submissions by some top value.

        :param top: One of week, month, year, all
        :returns: True if any submissions were found.

        """
        logger.debug('Fetching top submissions with limit=%s' % (top))
        for submission in self.subreddit.top(limit=None, time_filter=top):
            self.submissions.append(submission)

    def fetch_submissions(self, submissions_callback, *args):
        """Wrap the submissions_callback function."""
        submissions_callback(*args)

        logger.debug('Found {} submissions'.format(len(self.submissions)))
        if not self.submissions:
            return

        self.submissions.sort(key=lambda x: x.created_utc)
        self.min_date = self.submissions[0].created_utc
        self.max_date = self.submissions[-1].created_utc
        self.fetch_comments()

    def fetch_comments(self):
        """Write comments file."""
        logger.debug('Fetching comments on {} submissions'
                     .format(len(self.submissions)))

        for index, submission in enumerate(self.submissions):
            if submission.num_comments == 0:
                continue
            submission.comment_sort = 'top'

            more_comments = submission.comments.replace_more()
            if more_comments:
                skipped_comments = sum(x.count for x in more_comments)
                logger.debug('Skipped {} MoreComments ({} comments)'
                             .format(len(more_comments), skipped_comments))

            logger.debug('Fetched {} comments on {}/{} submissions'
                         .format(len(submission.comments.list()), index + 1, len(self.submissions)))
            self.comments.extend(submission.comments.list())

        self.comments.sort(key=lambda x: x.created_utc)

    def process_submissions(self):
        """Write submissions file."""
        filename = '%s-submissions.csv' % self.base_filename
        logger.debug('Processing submitters to %s' % filename)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect=customDialect)
            writer.writerow(['id', 'title', 'score', 'author', 'permalink', 'created_utc', 'domain', 'link_flair_css_class', 'gilded', 'num_comments', 'over_18'])
            for s in self.submissions:
                writer.writerow([s.id, s.title, s.score, s.author, s.permalink, s.created_utc, s.domain, s.link_flair_css_class, s.gilded, s.num_comments, s.over_18])
        return filename
    
    def process_comments(self):
        """Write comments file."""
        filename = '%s-comments.csv' % self.base_filename
        logger.debug('Processing comments to %s' % filename)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect=customDialect)
            writer.writerow(['d', 'score', 'ups', 'downs', 'author', 'link_id', 'created_utc', 'distinguished', 'gilded', 'body'])
            for c in self.comments:
                writer.writerow([c.id, c.score, c.ups, c.downs, c.author, c.link_id, c.created_utc, c.distinguished, c.gilded, c.body])
        return filename

    def publish_results(self, view):
        """Write extraction in csv files."""
        self.base_filename = '%s-%d-%s' % (str(self.subreddit), self.max_date, view)
        submissions_file = self.process_submissions()
        comments_file = self.process_comments()
        return [submissions_file, comments_file]

    def run(self, view):
        """Run stats and return the created Submission."""
        logger.info('Analyzing subreddit: {}'.format(self.subreddit))

        if view in TOP_VALUES:
            callback = self.fetch_top_submissions
        else:
            callback = self.fetch_recent_submissions
            view = int(view)
        self.fetch_submissions(callback, view)

        if not self.submissions:
            logger.warning('No submissions were found.')
            return

        return self.publish_results(view)


def main():
    """Provide the entry point to the subreddit_stats command."""
    parser = arg_parser(usage='usage: %(prog)s [options] SUBREDDIT VIEW')
    parser.add_argument('subreddit', type=str,
                    help='The subreddit to be analyzed')
    parser.add_argument('view', type=str,
                    help='The number of latest days or one of the reddit view (%s)' % ','.join(TOP_VALUES))
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
    files = srs.run(options.view)
    if files:
        print('Written files: %s' % ' '.join(files))
    return 0

if __name__ == "__main__":
    main()