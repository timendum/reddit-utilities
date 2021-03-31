from argparse import ArgumentParser as arg_parser
import csv
import logging
from datetime import datetime
from io import StringIO

from praw import Reddit

AGENT = 'python:thread-cloud:0.1 (by /u/timendum)'


class CustomDialect(csv.Dialect):
    """Describe the usual properties of Excel-generated CSV files."""
    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = csv.QUOTE_MINIMAL


logger = logging.getLogger(__file__)


def get_comments(submission_id):
    reddit = Reddit(check_for_updates=False, user_agent=AGENT)
    submission = reddit.submission(id=submission_id)
    more_comments = submission.comments.replace_more(limit=None)
    if more_comments:
        skipped_comments = sum(x.count for x in more_comments)
        logger.debug('Skipped %d MoreComments (%d comments)',
                     len(more_comments), skipped_comments)
    return submission.comments.list()


def extract_bodies(comments):
    bodies = []
    for comment in comments:
        bodies.append(comment.body)
    return bodies


def to_csv(comments):
    f = StringIO()
    writer = csv.writer(f, dialect=CustomDialect)
    writer.writerow([
        'id', 'score', 'author', 'link_id', 'created_utc', 'controversiality',
        'edited', 'top_level', 'stickied', 'distinguished', 'gilded', 'parent', 'body'
    ])
    for c in comments:
        writer.writerow([
            c.id, c.score, c.author, c.link_id,
            datetime.utcfromtimestamp(c.created_utc), c.controversiality,
            datetime.utcfromtimestamp(c.edited)
            if c.edited else c.edited, (c.parent_id == c.link_id), c.stickied,
            c.distinguished, c.gilded,
            '' if c.parent_id == c.link_id  else c.parent_id[3:],
            c.body
        ])
    output = f.getvalue()
    f.close()
    return output


def main():
    """Provide the entry point to the command."""
    parser = arg_parser(usage='usage: %(prog)s t3 COMMAND [filename]')
    parser.add_argument(
        't3', type=str, help='The id of the source thread (es: 5npcrc)')
    parser.add_argument(
        'command', type=str, help='text (body to txt) or csv (all to csv)')
    parser.add_argument(
        'filename',
        type=str,
        default=None,
        nargs='?',
        help='The filename for the output')
    parser.add_argument(
        '--verbose',
        type=int,
        default=0,
        help='0 for disabled, 1 for info, more for debug')

    options = parser.parse_args()

    if options.verbose == 1:
        logger.setLevel(logging.INFO)
    elif options.verbose > 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.NOTSET)
    logger.addHandler(logging.StreamHandler())

    comments = get_comments(options.t3)

    default_filename = 'output'
    if options.command == 'text':
        output = '\n'.join(extract_bodies(comments))
        default_filename = '%s.txt'
    elif options.command == 'csv':
        default_filename = '%s.csv'
        output = to_csv(comments)

    if not options.filename:
        options.filename = default_filename % options.t3

    with open(options.filename, 'w', encoding='utf8') as fileout:
        fileout.write(output)
    return 0


if __name__ == "__main__":
    main()
