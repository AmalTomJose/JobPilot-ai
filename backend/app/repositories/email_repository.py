from sqlalchemy import select, func
from app.models.email import EmailConnection, EmailMessage, EmailSyncRun
from app.models.user import User


class EmailRepository:
    def __init__(self, db):
        self.db = db

    def connection(self, user_id, lock=False, create=False):
        if create:
            self.db.scalar(select(User).where(User.id == user_id).with_for_update(nowait=True))
        query = select(EmailConnection).where(EmailConnection.user_id == user_id)
        row = self.db.scalar(query.with_for_update(nowait=True) if lock else query)
        if row is None and create:
            row = EmailConnection(user_id=user_id)
            self.db.add(row)
            self.db.flush()
        return row

    def message(self, user_id, mailbox, message_id):
        return self.db.scalar(select(EmailMessage).where(EmailMessage.user_id == user_id,
                              EmailMessage.mailbox_email == mailbox, EmailMessage.provider_message_id == message_id))

    def messages(self, user_id, limit, offset):
        query = select(EmailMessage).where(EmailMessage.user_id == user_id)
        items = list(self.db.scalars(query.order_by(EmailMessage.id.desc()).limit(limit).offset(offset)))
        from app.services.email_candidates import extract_openings
        for item in items:
            item.openings = extract_openings(item.payload_data, item.raw_text)
        return dict(items=items,
                    total=self.db.scalar(select(func.count()).select_from(query.subquery())), limit=limit, offset=offset)

    def runs(self, user_id):
        return list(self.db.scalars(select(EmailSyncRun).where(EmailSyncRun.user_id == user_id).order_by(EmailSyncRun.id.desc()).limit(10)))
