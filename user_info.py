"""Add user info to csv"""
import csv
import logging
from argparse import ArgumentParser as arg_parser

import prawcore
import praw

AGENT = 'python:users_dump:0.1 (by /u/timendum)'

LOGGER = logging.getLogger(__file__)


class CustomDialect(csv.Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL


def process(filename: str):
    """Read users and add info to the csv"""
    lines = None
    with open(filename, 'r', newline='', encoding='utf-8') as filehanlder:
        rcsv = csv.reader(filehanlder, CustomDialect)
        lines = [l for l in rcsv]
        session = praw.Reddit()
        for line in lines:
            try:
                user = session.redditor(line[0])
                line.append(user.created_utc)
                line.append(user.comment_karma)
                line.append(user.link_karma)
                line.append(user.has_verified_email)
            except prawcore.exceptions.NotFound:
                line.append('n/a')
                line.append('n/a')
                line.append('n/a')
                line.append('n/a')

    with open(filename, 'w', newline='', encoding='utf-8') as filehanlder:
        wcsv = csv.writer(filehanlder, CustomDialect)
        wcsv.writerow(
            ['Username', 'Created UTC', 'Comment karma', 'Link karma', 'Has verified email'])
        for line in lines:
            wcsv.writerow(line)


def main():
    """Provide the entry point to the user_since command."""
    parser = arg_parser(usage='usage: %(prog)s [options] file.csv')
    parser.add_argument('filename', type=str, help='The file with the list of usernames')
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
    process(options.filename)


if __name__ == "__main__":
    main()
