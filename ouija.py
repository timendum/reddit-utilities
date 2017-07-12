"""Produce a summery for AskOuija thread"""
# pylint: disable=C0103
import logging
import datetime
from sys import argv
from praw import Reddit
from praw.models.comment_forest import CommentForest

AGENT = 'python:reddit-ouja:0.1 (by /u/timendum)'

LOGGER = logging.getLogger(__file__)

END = '‡'

# Print open ansers even if there are closed in the same question
TODO_ALWAYS = True

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
        if todo_id:
            self.todo = reddit.comment(id=todo_id)

    def fetch_comments(self):
        """Return the comment of the post"""
        self.post.comment_sort = 'top'
        self.post.comments.replace_more(limit=None)
        return self.post.comments

    def find_answers(self, parent):
        """Given a comment return a list of open and closed replies"""
        closeds = []
        opens = []
        if isinstance(parent, CommentForest):
            parent.replace_more(limit=None)
        for comment in parent.replies:
            # closing found
            if 'goodbye' in comment.body.lower() or \
               'arrivederci' in comment.body.lower():
                if comment.score > 0:
                    closeds.append('[%s](%s?context=99) - %d' % (
                        END, self.permalink(comment), comment.score))

        for comment in parent.replies:
            body = comment.body.strip()
            if len(body) == 1:
                others, oks = self.find_answers(comment)
                for sub in oks:
                    closeds.append(body + sub)
                if not oks or TODO_ALWAYS:
                    for sub in others:
                        opens.append(body + sub)
                    # no descendant and no closed -> last char of an open answer
                    if not others and not oks:
                        if comment.score > 0:
                            opens.append('[%s](%s)' % (body, self.permalink(comment)))
            else:
                LOGGER.debug('Skipped %s', comment.body)
        return opens, closeds

    def oujas(self):
        """Return a list of [ok, todo]

        ok   = list of [question, answer] with ending (Goodbye)
        todo = list of [question, answer] without ending (Goodbye)
        """
        ok, todo = [], []
        for comment in self.fetch_comments():
            if comment.stickied:
                # skip stickied comment
                continue
            question = comment.body
            question = question.split('\n')[0]
            opens, closeds = self.find_answers(comment)
            if closeds:
                closeds.sort(key=lambda a: int(a.split(' - ')[-1]), reverse=True)
                ok.append([question, closeds])
            if not closeds or TODO_ALWAYS:
                if opens:
                    opens.sort(key=len, reverse=True)
                    todo.append([question, opens])
        return ok, todo

    def text(self):
        """Produce two string, one for closed and one for open questions."""
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
        """Write files or edit comments"""
        ok, todo = self.text()
        if self.ok:
            self.ok.edit(ok)
        if self.todo:
            self.todo.edit(todo)

        if not self.ok or not self.todo:
            with open('oks.txt', 'w', encoding='utf8') as f:
                f.write(ok)
            with open('todos.txt', 'w', encoding='utf8') as f:
                f.write(todo)

    def permalink(self, comment):
        """Produce a shorter permalink"""
        return '/r/{}/comments/{}//{}'.format(self.post.subreddit.display_name,
                                              self.post.id, comment.id)


if __name__ == "__main__":
    if len(argv) < 2:
        print('Invoke the program with post_id')
    else:
        args = argv + [None, None]
        o = Ouija(*argv[1:])
        o.output()
