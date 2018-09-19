from . import db
import time


class ERC721_Connect(db.Model):
    __tablename__ = 'erc721_connect'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(64))
    token_id = db.Column(db.Integer)
    mit_name = db.Column(db.String(64))
    status = db.Column(db.SmallInteger)
    @classmethod
    def copy(cls, dep_):
        dep = ERC721_Connect()
        dep.iden = dep_.iden
        dep.token = dep_.token
        dep.token_id = dep_.token_id
        dep.mit_name = dep_.mit_name
        dep.status = dep_.status
        return dep
