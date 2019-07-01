#pylint: disable=I0011,C0111,W0703
import csv

import praw
from psaw import PushshiftAPI

after = 1527814800
before = 1559350800

reddit = praw.Reddit(disable_update_check=True)
api = PushshiftAPI()

submissions = api.search_submissions(limit=1000000, subreddit='italy', after=after, before=before)

with open('year.csv', 'r', newline='', encoding='utf-8') as filecsv:
    reader = csv.reader(filecsv)
    processed_ids = {row[0] for row in reader}

with open('year.csv', 'a', newline='', encoding='utf-8') as filecsv:
    writer = csv.writer(filecsv)
    #writer.writerow([
    #    'id', 'score', 'author', 'link', 'created_utc',
    #    'gilded', 'num_comments', 'domain', 'url', 'over_18', 'title'
    #])
    for ps in submissions:
        if ps.id in processed_ids:
            continue
        rs = reddit.submission(ps.id)
        writer.writerow([
            ps.id, rs.score, ps.author, rs.permalink,
            ps.created_utc, rs.gilded,
            rs.num_comments, ps.domain, ps.url, rs.over_18, ps.title
        ])
        print('.', end= '', flush=True)