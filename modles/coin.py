from . import db
import time


class Coin(db.Model):
    __tablename__ = 'coin'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    block_height = db.Column(db.Integer)
    name = db.Column(db.String(64))
    token = db.Column(db.String(64))
    total_supply=db.Column(db.Integer)
    decimal=db.Column(db.Integer)

    @classmethod
    def copy(cls, dep_):
        dep = Coin()
        dep.iden = dep_.iden
        dep.block_height = dep_.block_height
        dep.token = dep_.token
        dep.name = dep_.name
        dep.total_supply = dep_.total_supply
        dep.decimal = dep_.decimal
        return dep
