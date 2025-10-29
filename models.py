from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    crosswords = db.relationship('Crossword', backref='author', lazy=True)

class Crossword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    author_username = db.Column(db.String(80), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    words = db.Column(db.Text, nullable=False) 
    grid = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)
    font_file = db.Column(db.String(255), nullable=True)


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crossword_id = db.Column(db.Integer, db.ForeignKey('crossword.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_token = db.Column(db.String(64), nullable=True, index=True)
    guest_name = db.Column(db.String(100), nullable=True)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    crossword = db.relationship('Crossword', backref=db.backref('scores', lazy=True))
    user = db.relationship('User', backref=db.backref('scores', lazy=True))
