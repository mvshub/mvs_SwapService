from . import db


class Scan(db.Model):
    __tablename__ = 'scan'
    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coin = db.Column(db.String(64))
    height = db.Column(db.Integer)
