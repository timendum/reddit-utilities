"""Update two multireddits from a wiki page"""
import datetime
import logging
import re

import prawcore
from praw import Reddit

logging.basicConfig(format="%(levelname)s:%(asctime)s %(message)s")
LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(logging.INFO)

SPLIT_TEXT = "Subreddit Locali"

ACTIVE_UTC = 45 * 24 * 60 * 60


class MultiredditUpdate(object):
    """Contain all the functionality."""

    def __init__(self, wikipage, reddit):
        """Initialize"""
        self.wikipage = wikipage
        self._reddit = reddit
        self._created_limit = datetime.datetime.now(datetime.UTC).timestamp() - ACTIVE_UTC

    def _find_and_filter(self, wcontent):
        subs = re.findall(r"r/[0-9A-Za-z_]+", wcontent)
        subs = set(subs)  # unique
        LOGGER.info("Checking %s", subs)
        subs = [sub[2:] for sub in subs]  # name only (no r/)
        subs = [
            sub for sub in subs if sub != self.wikipage.subreddit.display_name
        ]  # no r/italy
        subs = [sub for sub in subs if self._is_active(sub)]
        return subs

    def regional(self, multiname):
        wcontent = self.wikipage.content_md
        wcontent = wcontent.split(SPLIT_TEXT)[1]
        multi = self._reddit.multireddit(self._reddit.user.me().name, multiname)
        subs = self._find_and_filter(wcontent)
        LOGGER.info("Updating %s with %s", multi, subs)
        multi.update(
            subreddits=subs,
            visibility="public",
            description_md="""Subreddit attivi regionali e locali italiane.
        
Aggiornato: {}""".format(
                datetime.date.today().isoformat()
            ),
        )

    def italiano(self, multiname, multiname2):
        wcontent = self.wikipage.content_md
        wcontent = wcontent.split(SPLIT_TEXT)[0]
        multi = self._reddit.multireddit(self._reddit.user.me().name, multiname)
        subs = self._find_and_filter(wcontent)
        LOGGER.info("Updating %s with %s", multi, subs)
        multi.update(
            subreddits=subs,
            visibility="public",
            description_md="""Subreddit in italiano, escluso r/italy
        
Aggiornato: {}""".format(
                datetime.date.today().isoformat()
            ),
        )
        multi = self._reddit.multireddit(self._reddit.user.me().name, multiname2)
        subs.append('italy')
        LOGGER.info("Updating %s with %s", multi, subs)
        multi.update(
            subreddits=subs,
            visibility="public",
            description_md="""Subreddit in italiano
        
Aggiornato: {}""".format(
                datetime.date.today().isoformat()
            ),
        )

    def _is_active(self, subname):
        try:
            rsub = self._reddit.subreddit(subname)
            for submission in rsub.new(limit=5):
                if submission.created_utc > self._created_limit:
                    if submission.author.name == "AutoModerator":
                        LOGGER.debug("Automoderator %s", submission)
                        continue
                    LOGGER.info("%s ok (%s)", subname, submission)
                    return True
            LOGGER.info("%s skipped", subname)
        except prawcore.exceptions.NotFound:
            LOGGER.info("%s NotFound", subname)
        except prawcore.exceptions.Redirect:
            LOGGER.info("%s Redirect", subname)
        except prawcore.exceptions.Forbidden:
            LOGGER.info("%s Forbidden", subname)
        return False


def main():
    """For cli"""
    reddit = Reddit()
    wikipage = reddit.subreddit("italy").wiki["sub_italiani"]
    mu = MultiredditUpdate(wikipage, reddit)
    mu.regional("locali")
    mu.italiano("italiannoitaly", "italian")


if __name__ == "__main__":
    main()
