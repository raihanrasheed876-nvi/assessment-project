
import re
import string
import random
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'change-me'

db = SQLAlchemy(app)

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    long_url = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    clicks = db.Column(db.Integer, default=0)

    def as_dict(self):
        return {
            "code": self.code,
            "long_url": self.long_url,
            "created_at": self.created_at.isoformat(),
            "clicks": self.clicks,
        }

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def generate_code(n=6) -> str:
    alphabet = string.ascii_letters + string.digits
    for _ in range(10):
        code = ''.join(random.choices(alphabet, k=n))
        if not Link.query.filter_by(code=code).first():
            return code
    while True:
        code = ''.join(random.choices(alphabet, k=n+2))
        if not Link.query.filter_by(code=code).first():
            return code

@app.before_first_request
def init_db():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    recent = Link.query.order_by(Link.created_at.desc()).limit(10).all()
    return render_template('index.html', recent=recent)

@app.route('/shorten', methods=['POST'])
def shorten():
    long_url = request.form.get('long_url', '').strip()
    custom_code = request.form.get('custom_code', '').strip()

    if not long_url:
        flash('Please enter a URL.', 'error')
        return redirect(url_for('home'))
    if not is_valid_url(long_url):
        flash('Please enter a valid URL (must start with http:// or https://).', 'error')
        return redirect(url_for('home'))

    if custom_code:
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,20}', custom_code):
            flash('Custom code must be 3-20 chars (letters, numbers, _ or -).', 'error')
            return redirect(url_for('home'))
        if Link.query.filter_by(code=custom_code).first():
            flash('That short code is already taken. Try another.', 'error')
            return redirect(url_for('home'))
        code = custom_code
    else:
        code = generate_code()

    link = Link(code=code, long_url=long_url)
    db.session.add(link)
    db.session.commit()

    short_url = request.host_url + code
    flash(f'Success! Short URL: {short_url}', 'success')
    return redirect(url_for('home'))

@app.route('/<code>')
def redirect_code(code):
    link = Link.query.filter_by(code=code).first()
    if link is None:
        flash('Short code not found.', 'error')
        return redirect(url_for('home'))
    link.clicks += 1
    db.session.commit()
    return redirect(link.long_url, code=302)

@app.route('/api/links')
def api_links():
    links = Link.query.order_by(Link.created_at.desc()).limit(50).all()
    return jsonify([l.as_dict() for l in links])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
