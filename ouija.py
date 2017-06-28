# pylint: disable=C0111,W0621,C0103
import logging
import datetime
from sys import argv
from praw import Reddit
from praw.models.comment_forest import CommentForest

AGENT = 'python:reddit-ouja:0.1 (by /u/timendum)'

LOGGER = logging.getLogger(__file__)

END = '‡'

class Ouija(object):
    """Contain all the functionality of the subreddit_stats command."""

    def __init__(self, post_id, ok_id=None, todo_id=None):
        """Initialize."""
        reddit = Reddit(check_for_updates=False)
        self.post = reddit.submission(id=post_id)
        self.ok = None
        self.todo = None
        if ok_id:
            self.ok = reddit.comment(id=ok_id)
        if ok_id:
            self.todo = reddit.comment(id=todo_id)

    def fetch_comments(self):
        self.post.comment_sort = 'top'
        self.post.comments.replace_more(limit=None)
        return self.post.comments

    def find_answers(self, parent):
        closeds = []
        opens = []
        if isinstance(parent, CommentForest):
            parent.replace_more(limit=None)
        for comment in parent.replies:
            # closing found
            if 'goodbye' in comment.body.lower() or \
               'arrivederci' in comment.body.lower():
                closeds.append('[%s](%s) - %d' % (END, comment.permalink(fast=True), comment.score))

        for comment in parent.replies:
            if len(comment.body.strip()) == 1:
                others, oks = self.find_answers(comment)
                for sub in oks:
                    closeds.append(comment.body + sub)
                if not oks:
                    for sub in others:
                        opens.append(comment.body + sub)
                    if not others:
                        opens.append('[%s](%s)' % (comment.body, comment.permalink(fast=True)))
            else:
                LOGGER.debug('Skipped %s', comment.body)
        return opens, closeds

    def oujas(self):
        ok, todo = [], []
        for comment in self.fetch_comments():
            if comment.stickied:
                # skip stickied comment
                continue
            question = comment.body
            question = question.split('\n\n')[0]
            opens, closeds = self.find_answers(comment)
            if closeds:
                ok.append([question, closeds])
            else:
                if opens:
                    todo.append([question, opens])
        ok.sort(key=lambda a: int(a.split(' - ')[-1]))
        todo.sort(key=len)
        return ok, todo

    def text(self):
        text = ''
        ora = datetime.datetime.now().strftime('%H:%M')
        text += 'I Risultati alle %s.  \n%s = Finito - numero dei voti\n\n' % (ora, END)
        ok, todo = self.oujas()
        for ouja in ok:
            text += ouja[0] + '\n\n'
            for answer in ouja[1]:
                text += '* ' + answer + '\n'
            text += '\n\n'
        a = text
        text = 'Le domande aperte alle %s.\n\n' % (ora)
        for ouja in todo:
            text += ouja[0] + '\n\n'
            for answer in ouja[1]:
                text += '* ' + answer + '\n'
            text += '\n\n'
        b = text
        return a, b

    def output(self):
        ok, todo = self.text()
        if self.ok:
            self.ok.edit(ok)
        else:
            with open('oks.txt', 'w') as f:
                f.write(ok)
        if self.todo:
            self.todo.edit(todo)
        else:
            with open('todos.txt', 'w') as f:
                f.write(todo)


if __name__ == "__main__":
    if len(argv) < 2:
        print('Invoke the program with post_id')
    else:
        args = argv + [None, None]
        o = Ouija(*argv[1:])
        o.output()
