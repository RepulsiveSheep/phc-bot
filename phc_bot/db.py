import os
from datetime import datetime

from peewee import Model, CharField, DateTimeField, ForeignKeyField
from playhouse.db_url import connect

db = connect(os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'))
db.connect()


class Base(Model):
    created_at = DateTimeField(default=datetime.now)
    last_updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        legacy_table_names = False

    def save(self, *args, **kwargs):
        self.last_updated_at = datetime.now()
        return super().save(*args, **kwargs)


class RepliedSubmission(Base):
    submission_id = CharField(max_length=255)
    image_url = CharField(max_length=4096, null=True, default=None)
    ocr_text = CharField(max_length=10240, null=True, default=None)
    query_text = CharField(max_length=10240, null=True, default=None)
    predicted_link = CharField(max_length=4096, null=True, default=None)

    def __repr__(self):
        return f'<{RepliedSubmission.__name__}(submission_id={self.submission_id}, predicted_link={self.predicted_link}>'


class RepliedComment(Base):
    comment_id = CharField(max_length=255)
    replied_submission = ForeignKeyField(RepliedSubmission, backref='replied_comments', null=True, default=None)

    def __repr__(self):
        return f'<{RepliedComment.__name__}(comment_id={self.comment_id}, replied_submission={self.replied_submission}>'
