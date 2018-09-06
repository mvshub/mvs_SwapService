from . import db
import time


class Result(db.Model):
    __tablename__ = 'result'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    swap_id = db.Column(db.Integer, nullable=False)
    from_address = db.Column(db.String(128))
    to_address = db.Column(db.String(128))
    amount = db.Column(db.Numeric(64, 18), nullable=False)

    coin = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(64), nullable=False)

    tx_from = db.Column(db.String(256))
    tx_hash = db.Column(db.String(256))
    tx_burn = db.Column(db.String(256))

    tx_height = db.Column(db.Integer)
    confirm_height = db.Column(db.Integer)
    confirm_status = db.Column(db.SmallInteger, default=0)
    status = db.Column(db.SmallInteger, default=0)
    date = db.Column(db.Integer, default=0)
    time = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)

    fee = db.Column(db.Numeric(64, 18))
    from_fee = db.Column(db.Numeric(64, 18))

    @classmethod
    def copy(cls, dep_):
        dep = Result()
        dep.iden = dep_.iden
        dep.swap_id = dep_.swap_id
        dep.from_address = dep_.from_address
        dep.to_address = dep_.to_address
        dep.amount = dep_.amount
        dep.token = dep_.token
        dep.coin = dep_.coin
        dep.tx_hash = dep_.tx_hash
        dep.tx_burn = dep_.tx_burn
        dep.tx_from = dep_.tx_from
        dep.confirm_status = dep_.confirm_status
        dep.status = dep_.status
        dep.date = dep_.date
        dep.time = dep_.time
        dep.message = dep_.message
        dep.fee = dep_.fee
        dep.from_fee = dep_.from_fee

        return dep

    @classmethod
    def to_json(cls, obj):
        #import pdb; pdb.set_trace()
        return {
            'swap_id': obj.swap_id,
            'from_address': obj.from_address,
            'to_address': obj.to_address,
            'amount': str(obj.amount),
            'token': obj.token,
            'coin': obj.coin,
            'tx_hash': obj.tx_hash,
            'tx_from': obj.tx_from,
            'confirm_status': obj.confirm_status,
            'status': obj.status,
            'date': str(obj.date),
            'time': str(obj.time),
            'message': obj.message
        }
