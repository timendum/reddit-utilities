ATTACH DATABASE (SELECT SUBSTR(file, 0, LENGTH(file)-2) || '_' || STRFTIME('%Y-%m.db', DATE('now','start of month', '-1 month')) FROM pragma_database_list WHERE name='main') AS old;

CREATE TABLE old.submissions AS SELECT * FROM submissions WHERE created_utc < STRFTIME('%s', DATE('now','start of month')) AND created_utc >= STRFTIME('%s', DATE('now','start of month', '-1 month'));

CREATE TABLE old.submissions_awards AS SELECT * FROM submissions_awards AS c WHERE EXISTS (SELECT id FROM old.submissions WHERE submissions.id = c.submission_id);

CREATE TABLE old.comments AS SELECT * FROM comments WHERE created_utc < STRFTIME('%s', DATE('now','start of month')) AND created_utc >= STRFTIME('%s', DATE('now','start of month', '-1 month'));

CREATE TABLE old.comments_awards AS SELECT * FROM comments_awards AS c WHERE EXISTS (SELECT id FROM old.comments WHERE comments.id = c.comment_id);

CREATE TABLE old.traffics AS SELECT * FROM traffics WHERE day < STRFTIME('%s', DATE('now','start of month')) AND day > STRFTIME('%s', DATE('now','start of month', '-1 month'));

-- DELETE

DELETE FROM submissions WHERE EXISTS (select * from old.submissions as otable where submissions.id = otable.id);
DELETE FROM comments WHERE EXISTS (select * from old.comments as otable where comments.id = otable.id);
DELETE FROM submissions_awards WHERE EXISTS (select * from old.submissions_awards as otable where submissions_awards.id = otable.id);
DELETE FROM comments_awards WHERE EXISTS (select * from old.comments_awards as otable where comments_awards.id = otable.id);

-- ON OLD DB


CREATE UNIQUE INDEX submissions_id ON submissions(id);
CREATE UNIQUE INDEX comments_id ON comments(id);
CREATE UNIQUE INDEX submissions_awards_id ON submissions_awards(id);
CREATE UNIQUE INDEX comments_awards_id ON comments_awards(id);
CREATE UNIQUE INDEX traffics_day ON traffics(day);
