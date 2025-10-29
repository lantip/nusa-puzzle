from flask import (Flask, render_template, redirect, 
    session, url_for, request, flash, jsonify, current_app,
    send_file, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Crossword, Score
from utils import assign_clue_numbers
from crossword.generator import Crossword as CrosswordGenerator
from slugify import slugify 
from sqlalchemy import func, desc, or_, and_, case
from sqlalchemy.sql import label
from PIL import Image, ImageDraw, ImageFont
import uuid, json, re, os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/about', methods=['GET'])
def about():
    return render_template('landing/tentang.html')

@app.route('/terms-of-service', methods=['GET'])
def terms():
    return render_template('landing/terms.html')

@app.route('/privacy-policy', methods=['GET'])
def privacy():
    return render_template('landing/privacy.html')


def generate_crossword_preview(crossword, output_dir='static/previews'):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{crossword.slug}.png"
    path = os.path.join(output_dir, filename)

    grid = eval(crossword.grid) 
    cell_size = 40
    padding = 20
    rows, cols = len(grid), len(grid[0])
    width, height = cols * cell_size + 2 * padding, rows * cell_size + 2 * padding

    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    for r in range(rows):
        for c in range(cols):
            x1 = padding + c * cell_size
            y1 = padding + r * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size

            if grid[r][c] == ' ':
                draw.rectangle([x1, y1, x2, y2], fill="#000", outline="#999")
            else:
                draw.rectangle([x1, y1, x2, y2], fill="white", outline="black")

    font = ImageFont.load_default()
    draw.text((10, 5), crossword.title[:25], fill="black", font=font)

    img.save(path)
    return path

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/fonts')
def get_fonts():
    font_dir = os.path.join(current_app.static_folder, 'font')
    fonts = []
    for file in os.listdir(font_dir):
        name, ext = os.path.splitext(file)
        if ext.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
            if '__' in name:
                label, fontname = name.split('__', 1)
            else:
                label, fontname = name, name
            fonts.append({
                'label': label.strip(),
                'file': file,
                'fontname': fontname.strip()
            })
    fonts.sort(key=lambda f: f['label'].lower())
    return jsonify(fonts)


@app.route('/admin')
@login_required
def admin_dashboard():
    crosswords = Crossword.query.filter_by(author_id=current_user.id)
    return render_template('admin/dashboard.html', crosswords=crosswords)

@app.route('/admin/new', methods=['GET'])
@login_required
def admin_new():
    return render_template('admin/new.html')

@app.route('/admin/generate_preview', methods=['POST'])
@login_required
def generate_preview():
    data = request.get_json()
    title = data.get('title', '').strip()
    words = data.get('words', [])

    # Sanitize
    available_words = [(w['word'].strip(), w['clue'].strip()) for w in words if w['word'] and w['clue']]

    if not available_words:
        return jsonify({'error': 'No valid words provided'}), 400

    gen = CrosswordGenerator(cols=15, rows=15, available_words=available_words)
    gen.compute_crossword(time_permitted=1.0)
    crossword_data = gen.to_json()

    return jsonify({
        'grid': crossword_data['grid'],
        'words': crossword_data['words']
    })


@app.route('/admin/save_crossword', methods=['POST'])
@login_required
def save_crossword():
    data = request.get_json()
    title = data.get('title')
    grid = data.get('grid')
    words = data.get('words')
    font_name = data.get('font_file')  # 🆕

    slug = slugify(title)
    crossword = Crossword(
        title=title,
        slug=slug,
        author_username=current_user.username,
        author_id=current_user.id,
        grid=json.dumps(grid),
        words=json.dumps(words),
        font_file=font_name,
    )
    db.session.add(crossword)
    db.session.commit()

    return jsonify({'success': True, 'redirect': url_for('view_crossword', slug=slug)})


@app.route('/admin/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit(id):
    crossword = Crossword.query.get_or_404(id)
    if crossword.author_id != current_user.id:
        flash("You don't have permission to modify this")
        return redirect(url_for('admin_dashboard'))
    preview = json.loads(crossword.grid)
    words = json.loads(crossword.words)

    if request.method == 'POST':
        title = request.form.get('title', crossword.title)
        if 'generate' in request.form:
            available_words = []
            for w in words:
                if isinstance(w, dict):
                    word, clue = w.get("word"), w.get("clue")
                else:
                    word, clue = w
                if word and clue:
                    available_words.append((word.strip(), clue.strip()))
            gen = CrosswordGenerator(cols=15, rows=15, available_words=available_words)
            gen.compute_crossword(time_permitted=1.0)
            crossword_data = gen.to_json()
            preview = crossword_data["grid"]
            words = crossword_data["words"]

            flash("✅ Crossword regenerated (not yet saved). Click 'Save' to store changes.")
        elif 'save' in request.form:
            crossword.title = title
            grid_data = request.form.get('griddata') 
            word_data = request.form.get('wordlist')
            crossword.grid = grid_data
            crossword.words = word_data
            db.session.commit()
            flash("✅ Crossword saved.")
            return redirect(url_for('admin_dashboard'))
    numbering = assign_clue_numbers(preview, words, empty=' ')
    number_grid = numbering.get("number_grid")

    rows = len(preview)
    cols = len(preview[0]) if rows else 0

    if not number_grid:
        number_grid = [[None] * cols for _ in range(rows)]
    else:
        while len(number_grid) < rows:
            number_grid.append([None] * cols)
        for r in range(rows):
            if len(number_grid[r]) < cols:
                number_grid[r].extend([None] * (cols - len(number_grid[r])))

    clues = {
        "all": numbering["clues"],
        "across": numbering["across"],
        "down": numbering["down"]
    }

    return render_template(
        'admin/edit.html',
        crossword=crossword,
        preview=preview,
        words=words,
        numbers=number_grid,
        clues=clues
    )


@app.route('/admin/<int:id>/publish')
@login_required
def admin_publish(id):
    crossword = Crossword.query.get_or_404(id)
    crossword.is_published = True
    db.session.commit()

    generate_crossword_preview(crossword)

    flash('Crossword published and preview generated!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/<int:id>/view')
@login_required
def view_crossword(id):
    crossword = Crossword.query.get_or_404(id)
    grid = json.loads(crossword.grid)
    words_data = json.loads(crossword.words)

    # Normalize: convert list -> dict
    if isinstance(words_data, list):
        # expect list of [word, clue] pairs
        words = {w['word']: w['clue'] for w in words_data}
    elif isinstance(words_data, dict):
        words = words_data
    else:
        words = {}

    return render_template(
        'admin/view.html',
        crossword=crossword,
        preview=grid,
        words=words
    ) 

@app.route('/cw-<author_username>/<slug>', methods=['GET', 'POST'])
def play_crossword(author_username, slug):
    crossword = Crossword.query.filter_by(author_username=author_username, slug=slug).first_or_404()
    if not crossword.is_published:
        flash('The game is not published yet.')
        if current_user.is_authenticated:
            return redirect('/admin')
        return redirect('/')

    grid = json.loads(crossword.grid)
    words = json.loads(crossword.words)

    identity = case(
        (
            Score.user_id.isnot(None),
            ('user_' + func.cast(Score.user_id, db.String))
        ),
        else_=(
            'guest_' + func.coalesce(Score.guest_token, '') + '_' + func.coalesce(Score.guest_name, '')
        )
    )

    ranked = (
        db.session.query(
            Score,
            func.row_number().over(
                partition_by=identity,
                order_by=Score.score.desc()
            ).label('rnk')
        )
        .filter(Score.crossword_id == crossword.id)
    ).subquery()

    scores = (
        db.session.query(Score)
        .join(ranked, Score.id == ranked.c.id)
        .filter(ranked.c.rnk == 1)
        .order_by(Score.score.desc())
        .limit(5)
        .all()
    )

    if request.method == 'POST':
        score_value = int(request.form.get('score', 0))
        if current_user.is_authenticated:
            new_score = Score(
                crossword_id=crossword.id,
                user_id=current_user.id,
                score=score_value
            )
        else:
            if 'guest_token' not in session:
                session['guest_token'] = str(uuid.uuid4())
            guest_name = request.form.get('guest_name', '').strip() or 'Guest'
            session['guest_name'] = guest_name

            new_score = Score(
                crossword_id=crossword.id,
                guest_token=session['guest_token'],
                guest_name=guest_name,
                score=score_value
            )

        db.session.add(new_score)
        db.session.commit()
        flash('Your score has been recorded!')
        return redirect(url_for('play_crossword', author_username=author_username, slug=slug))

    guest_name = session.get('guest_name', '')

    numbering = assign_clue_numbers(grid, words, empty=' ')
    number_grid = numbering.get("number_grid")

    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    if not number_grid:
        number_grid = [[None] * cols for _ in range(rows)]
    else:
        while len(number_grid) < rows:
            number_grid.append([None] * cols)
        for r in range(rows):
            if len(number_grid[r]) < cols:
                number_grid[r].extend([None] * (cols - len(number_grid[r])))

    clues = {
        "all": numbering["clues"],
        "across": numbering["across"],
        "down": numbering["down"]
    }

    num_map = {}
    for c in numbering['clues']:
        key = (int(c['row']), int(c['col']), True if c['orientation'] == 'down' else False)
        num_map[key] = int(c['number'])

    annotated_words = []
    for w in words:
        if isinstance(w, dict):
            row = int(w.get('row', 0))
            col = int(w.get('col', 0))
            vert = bool(w.get('vertical', False))
            number = num_map.get((row, col, vert))
            neww = w.copy()
            neww['number'] = number
            annotated_words.append(neww)
        else:
            word_text, clue_text, row, col, vert = w[0], w[1], w[2], w[3], w[4]
            number = num_map.get((int(row), int(col), bool(vert)))
            annotated_words.append({
                'word': word_text,
                'clue': clue_text,
                'row': int(row),
                'col': int(col),
                'vertical': bool(vert),
                'number': number
            })

    words = annotated_words
    return render_template(
        'play/play.html',
        crossword=crossword,
        grid=grid,
        words=words,
        guest_name=guest_name,
        scores=scores,
        numbers=number_grid,
        clues=clues
    )

@app.route('/api/submit_score/<id>', methods=['POST'])
def submit_score(id):
    crossword = Crossword.query.filter_by(id=id).first_or_404()
    data = request.get_json()    
    score_value = data.get('score', 0)
    if score_value < 1:
        return jsonify({'success': True})
    if current_user.is_authenticated:
        new_score = Score(
            crossword_id=crossword.id,
            user_id=current_user.id,
            score=score_value
        )

    else:
        if 'guest_token' not in session:
            session['guest_token'] = str(uuid.uuid4())
        guest_name = data.get('guest_name').strip() or 'Guest'
        session['guest_name'] = guest_name

        new_score = Score(
            crossword_id=crossword.id,
            guest_token=session['guest_token'],
            guest_name=guest_name,
            score=score_value
        )

    db.session.add(new_score)
    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/scoreboard/<slug>')
def get_scoreboard(slug):
    crossword = Crossword.query.filter_by(slug=slug).first_or_404()
    scores = Score.query.filter_by(crossword_id=crossword.id).order_by(Score.score.desc()).all()
    return jsonify({'scores': [{'name': s.name, 'score': s.score} for s in scores]})

@app.route("/", methods=["GET"])
def home():
    fonts = ["bali", "batak", "iban", "incung", "jangang", "jawa", "kawi", "lampung", 
             "lontara", "ende", "malesung", "mbojo", "minangkabau", "pallawa", "pegon",
             "rejang", "sunda"]
    return render_template('landing/home.html', fonts=fonts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        # --- Validation ---
        if not username or not password or not confirm:
            flash('Please fill out all fields 😅', 'warning')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match 😬', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters 💪', 'danger')
            return redirect(url_for('register'))

        # Optional: regex strength check
        pattern = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).+$')
        if not pattern.match(password):
            flash('For stronger security, mix letters and numbers 🔒', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken. Try another one 😉', 'danger')
            return redirect(url_for('register'))

        # --- Create new user ---
        new_user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f'Welcome, {username}! Your account is ready 🎉', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('auth/register.html')

@app.route('/preview/<slug>.png')
def crossword_preview(slug):
    preview_path = os.path.join('static', 'previews', f'{slug}.png')
    os.makedirs(os.path.dirname(preview_path), exist_ok=True)

    if not os.path.exists(preview_path):
        crossword = Crossword.query.filter_by(slug=slug, is_published=True).first()
        if not crossword:
            abort(404)
        generate_crossword_preview(crossword, output_dir=os.path.join('static', 'previews'))

    return send_file(preview_path, mimetype='image/png')

@app.route('/list-games')
def games_list():
    play_counts = db.session.query(
        Score.crossword_id,
        func.count(Score.id).label('play_count')
    ).group_by(Score.crossword_id).subquery()

    crosswords = (
        db.session.query(
            Crossword,
            func.coalesce(play_counts.c.play_count, 0).label('plays')
        )
        .outerjoin(play_counts, Crossword.id == play_counts.c.crossword_id)
        .filter(Crossword.is_published == True)
        .order_by(Crossword.created_at.desc(), func.coalesce(play_counts.c.play_count, 0).desc())
        .all()
    )

    return render_template('landing/list-games.html', crosswords=crosswords)

@app.route('/play-random')
def play_random():
    crossword = (
        Crossword.query
        .filter_by(is_published=True)
        .order_by(func.random()) 
        .first()
    )
    if not crossword:
        flash("No published crosswords available yet.", "warning")
        return redirect(url_for('games_list'))
    
    return redirect(url_for('play_crossword', slug=crossword.slug, author_username=crossword.author_username))

@app.route('/hall-of-fame')
def hall_of_fame():
    global_scores_subq = (
        db.session.query(
            case(
                (Score.user_id.isnot(None), func.coalesce(Score.user_id, 0)),
                else_=0
            ).label('player_id'),
            func.coalesce(Score.guest_name, User.username).label('player_name'),
            func.max(Score.score).label('best_score')
        )
        .outerjoin(User, Score.user_id == User.id)
        .group_by('player_name', 'player_id')
        .order_by(desc('best_score'))
        .limit(10)
        .subquery()
    )

    global_leaderboard = db.session.query(
        global_scores_subq.c.player_name,
        global_scores_subq.c.best_score
    ).order_by(desc(global_scores_subq.c.best_score)).all()

    crosswords = Crossword.query.filter_by(is_published=True).order_by(Crossword.created_at.desc()).all()
    leaderboard_data = []
    for cw in crosswords:
        scores_subq = (
            db.session.query(
                case(
                    (Score.user_id.isnot(None), func.coalesce(Score.user_id, 0)),
                    else_=0
                ).label('player_id'),
                func.coalesce(Score.guest_name, User.username).label('player_name'),
                func.max(Score.score).label('best_score')
            )
            .outerjoin(User, Score.user_id == User.id)
            .filter(Score.crossword_id == cw.id)
            .group_by('player_name', 'player_id')
            .order_by(desc('best_score'))
            .limit(5)
            .all()
        )
        leaderboard_data.append((cw, scores_subq))

    return render_template(
        'landing/leaderboards.html',
        global_leaderboard=global_leaderboard,
        leaderboard_data=leaderboard_data
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # create default admin
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin'))
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
