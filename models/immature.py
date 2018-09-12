from . import db
import time


class Immature(db.Model):
    __tablename__ = 'immature'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tx_hash = db.Column(db.String(256), unique = True)
    block_hash = db.Column(db.String(256), )
    block_height = db.Column(db.Integer)
    coin = db.Column(db.String(64))
    tx_result = db.Column(db.Text)

    # new confirmed transferred committed
    nonce = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)


    @classmethod
    def copy(cls, dep_):
        dep = Immature()
        dep.iden = dep_.iden
        dep.tx_hash = dep_.tx_hash
        dep.block_hash = dep_.block_hash
        dep.block_height = dep_.block_height
        dep.coin = dep_.coin
        dep.nonce = dep_.nonce
        dep.status = dep_.status
        dep.tx_result = dep_.tx_result
        return dep
