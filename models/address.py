from . import db


class Address(db.Model):
    __tablename__ = 'address'
    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    address = db.Column(db.String(128))
    coin = db.Column(db.String(64))
    inuse = db.Column(db.Integer)
