from . import db
import time


class Binder(db.Model):
    __tablename__ = 'binder'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    binder = db.Column(db.String(128), nullable=False)
    to = db.Column(db.String(128), nullable=False)
    tx_hash = db.Column(db.String(256))
    block_height = db.Column(db.Integer)
    tx_time = db.Column(db.Numeric(32), nullable=False)

    @classmethod
    def copy(cls, binder_):
        binder = Binder()
        binder.iden = binder_.iden
        binder.binder = binder_.binder
        binder.to = binder_.to
        binder.tx_hash = binder_.tx_hash
        binder.block_height = binder_.block_height
        binder.tx_time = binder_.tx_time
        return etp
