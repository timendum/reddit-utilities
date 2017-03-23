"""Find best comment on reddit."""
import csv
import logging
import calendar
import time
from argparse import ArgumentParser as arg_parser
from os import path
import pystache
from praw import Reddit
from email.utils import formatdate

HOUR_IN_SECONDS = 60 * 60
DAY_IN_SECONDS = 60 * 60 * 24
AGENT = 'python:reddit-stats:0.1 (by /u/timendum)'

LOGGER = logging.getLogger(__file__)


class CustomDialect(csv.Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL


class SubredditStats(object):
    """Contain all the functionality of the subreddit_stats command."""

    def __init__(self, subreddit=None, multireddit=None, days=2):
        """Initialize the SubredditStats instance with config options."""
        self.submissions = []
        self.comments = []
        # extract post with at least 2 ours and less the <days+1> days
        now_utc = calendar.timegm(time.gmtime())
        self.max_date_thread = now_utc - HOUR_IN_SECONDS * 2
        self.min_date_thread = now_utc - DAY_IN_SECONDS * (days + 1)
        self.min_date = now_utc - DAY_IN_SECONDS * days
        self.reddit = Reddit(check_for_updates=False, user_agent=AGENT)
        if subreddit:
            self.subreddit = self.reddit.subreddit(subreddit)
        elif multireddit:
            self.subreddit = self.reddit.multireddit(*multireddit)
        else:
            raise ValueError('Specify subreddit or multireddit')

    def fetch_recent_submissions(self):
        """Fetch recent submissions in subreddit with boundaries.

        :param max_duration: When set, specifies the number of days to include

        """

        LOGGER.debug('Fetching submissions until %d', (self.min_date_thread))
        for submission in self.subreddit.new(limit=None):
            if submission.created_utc <= self.min_date_thread:
                break
            if submission.created_utc > self.max_date_thread:
                continue
            self.submissions.append(submission)

    def fetch_comments(self):
        """Write comments file."""
        LOGGER.debug('Fetching comments on %d submissions',
                     len(self.submissions))

        for index, submission in enumerate(self.submissions):
            if submission.num_comments == 0:
                continue
            submission.comment_sort = 'top'

            more_comments = submission.comments.replace_more()
            if more_comments:
                skipped_comments = sum(x.count for x in more_comments)
                LOGGER.debug('Skipped %d MoreComments (%d comments)',
                             len(more_comments), skipped_comments)

            LOGGER.debug('Fetched %d comments on %d/%d submissions',
                         len(submission.comments.list()), index + 1,
                         len(self.submissions))
            self.comments.extend(submission.comments.list())

    def process_comments(self, score_limit):
        """Apply filters to comments."""
        LOGGER.debug('Fetched %d comments', len(self.comments))
        self.comments = [
            comment for comment in self.comments if comment.score > score_limit
        ]
        self.comments.sort(key=lambda x: x.score, reverse=True)
        LOGGER.debug('Remained %d comments', len(self.comments))

    def publish_csv(self):
        """Write comments to file."""
        filename = 'comments-%s-%d.csv' % (self.subreddit.display_name,
                                           self.max_date_thread)
        LOGGER.debug('Processing comments to %s', filename)
        with open(filename, 'w', newline='', encoding='utf-8') as filecsv:
            writer = csv.writer(filecsv, dialect=CustomDialect)
            writer.writerow([
                'd', 'score', 'author', 'link', 'created_utc',
                'distinguished', 'gilded', 'body'
            ])
            for comment in self.comments:
                writer.writerow([
                    comment.id, comment.score, comment.author, comment.permalink(fast=True),
                    comment.created_utc, comment.distinguished, comment.gilded,
                    comment.body
                ])
        return filename

    def publish_feed(self):
        """Generate an RSS feed"""
        data = {
            'title': 'Best comment of %s' % self.subreddit.display_name,
            'url': self.reddit.config.reddit_url + self.subreddit.path,
            'description': 'Best comments',
            'rss2update': formatdate(),
            'entries': [
                {'title':'[%d] %s on %s' % (comment.score, comment.author, comment.submission.title),
                 'url': self.reddit.config.reddit_url + comment.permalink(fast=True),
                 'text': comment.body_html
                }
                for comment in self.comments
            ]
        }
        renderer = pystache.Renderer()
        output = renderer.render_path(
            path.join(path.dirname(path.abspath(__file__)), 'rss.mustache'),
            data)
        with open('best-comment.xml', 'w', encoding='utf8') as text_file:
            text_file.write(output)
        return True

    def run(self, action, score_limit):
        """Run stats and return the created Submission."""
        LOGGER.info('Analyzing subreddit: %s', self.subreddit)

        self.fetch_recent_submissions()
        self.fetch_comments()

        if not self.submissions:
            LOGGER.warning('No submissions were found.')
            return

        self.process_comments(score_limit)

        if action == 'csv':
            return self.publish_csv()
        if action == 'feed':
            return self.publish_feed()
        else:
            raise ValueError('Invalid action')


def main():
    """Provide the entry point to the subreddit_stats command."""
    parser = arg_parser(usage='usage: %(prog)s [options] SUBREDDIT ACTION')
    parser.add_argument(
        'subreddit',
        type=str,
        help='The subreddit or multireddit to be analyzed')
    parser.add_argument(
        'action', type=str, help='The action to be performed: mail or csv')
    parser.add_argument(
        '--days', type=int, default=2, help='The days to be extracted')
    parser.add_argument(
        '--score',
        type=int,
        default=40,
        help='The minumum number of score to be included')
    parser.add_argument(
        '--verbose',
        type=int,
        default=0,
        help='0 for disabled, 1 for info, more for debug')

    options = parser.parse_args()

    if options.verbose == 1:
        LOGGER.setLevel(logging.INFO)
    elif options.verbose > 1:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.NOTSET)
    LOGGER.addHandler(logging.StreamHandler())

    multireddit = options.subreddit.split('/m/')
    if len(multireddit) > 1:
        subreddit = None
    else:
        multireddit = None
        subreddit = options.subreddit

    srs = SubredditStats(subreddit, multireddit, options.days)
    srs.run(options.action, score_limit=options.score)


if __name__ == "__main__":
    main()
