ATTACH DATABASE (SELECT SUBSTR(file, 0, LENGTH(file)-2) || '_' || STRFTIME('%Y-%m.db', DATE('now','start of month', '-1 month')) FROM pragma_database_list WHERE name='main') AS old;

CREATE TABLE old.submissions AS SELECT * FROM submissions WHERE created_utc < STRFTIME('%s', DATE('now','start of month')) AND created_utc >= STRFTIME('%s', DATE('now','start of month', '-1 month'));

CREATE TABLE old.submissions_awards AS SELECT * FROM submissions_awards AS c WHERE EXISTS (SELECT id FROM old.submissions WHERE submissions.id = c.submission_id);

CREATE TABLE old.comments AS SELECT * FROM comments WHERE created_utc < STRFTIME('%s', DATE('now','start of month')) AND created_utc >= STRFTIME('%s', DATE('now','start of month', '-1 month'));

CREATE TABLE old.comments_awards AS SELECT * FROM comments_awards AS c WHERE EXISTS (SELECT id FROM old.comments WHERE comments.id = c.comment_id);

CREATE TABLE old.traffics AS SELECT * FROM traffics WHERE day < STRFTIME('%s', DATE('now','start of month')) AND day > STRFTIME('%s', DATE('now','start of month', '-1 month'));