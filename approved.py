"""Dump the approved submitters to csv"""
import csv
from argparse import ArgumentParser as arg_parser
import logging
import praw

AGENT = 'python:approved:0.1 (by /u/timendum)'

LOGGER = logging.getLogger(__file__)

class CustomDialect(csv.Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL

def process(subreddit: str) -> str:
    """Read users and add info to the csv"""
    reddit = praw.Reddit(check_for_updates=False, user_agent=AGENT)
    subr = reddit.subreddit(subreddit)
    contributors = subr.contributor(limit=None)

    filename = '%s-approved.csv' % subreddit
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, dialect=CustomDialect)
        for contributor in contributors:
            writer.writerow([contributor.name])
    return filename

def main():
    """Provide the entry point to the approved command."""
    parser = arg_parser(usage='usage: %(prog)s [options] SUBREDDIT')
    parser.add_argument(
        'subreddit', type=str, help='The subreddit to be analyzed')
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
    process(options.subreddit)


if __name__ == "__main__":
    main()
