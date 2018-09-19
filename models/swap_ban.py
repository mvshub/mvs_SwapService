from . import db
import time


class Swap_ban(db.Model):
    __tablename__ = 'Swap_ban'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    swap_address = db.Column(db.String(128))
    from_address = db.Column(db.String(128))
    to_address = db.Column(db.String(128))
    amount = db.Column(db.Numeric(64, 18))
    fee = db.Column(db.Numeric(64, 18))
    tx_hash = db.Column(db.String(256))
    tx_index = db.Column(db.Integer)
    output_index = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    tx_time = db.Column(db.Numeric(32))
    token = db.Column(db.String(64))
    coin = db.Column(db.String(64))
    token_type = db.Column(db.SmallInteger, default=0)

    # new confirmed transferred committed
    create_time = db.Column(db.Numeric(32))
    message = db.Column(db.Text)
    @classmethod
    def copy(cls, dep_):
        dep = Swap_ban()
        dep.iden = dep_.iden
        dep.swap_address = dep_.swap_address
        dep.from_address = dep_.from_address
        dep.to_address = dep_.to_address
        dep.amount = dep_.amount
        dep.fee = dep_.fee
        dep.tx_hash = dep_.tx_hash
        dep.tx_index = dep_.tx_index
        dep.output_index = dep_.output_index
        dep.block_height = dep_.block_height
        dep.tx_time = dep_.tx_time
        dep.coin = dep_.coin
        dep.token = dep_.token
        dep.token_type = dep_.token_type
        dep.create_time = dep_.create_time
        dep.message = dep_.message
        return dep
