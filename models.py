from datetime import datetime
from application import db


class User(db.Model):
    """User class"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cash = db.Column(db.Numeric, nullable=False, default=10000.00)
    transactions = db.relationship('Transaction', backref='owner', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.cash:.2f}')"


class Transaction(db.Model):
    """Stocks transaction"""
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    stocks_symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric, nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Transaction('{self.stocks_symbol}', '{self.shares}', '{self.price}', '{self.transaction_date}')"


class Stocks(db.Model):
    """List of Stocks"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    company_name = db.Column(db.String(60), nullable=False)
    sector = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return f"Stocks('{self.symbol}', '{self.company_name}', '{self.sector}')"
