from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from utils import encrypt_email, decrypt_email, hash_email

## シークレットキー挿入
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hibi-secret-key'
DB_NAME = 'database.db'

@app.route('/')
def home():
    session.clear()
    return render_template('home.html')

@app.route('/check')
def check():
    return "<h2>予約確認ページ（準備中）</h2>"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # eventsテーブルの再作成時に日付カラム追加
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance INTEGER NOT NULL ,
            name TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            is_provisional BOOL DEFAULT TRUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            email_hash TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/customer_request', methods=['POST'])
def customer_request():
    if not session.get('login_ok'):
        return redirect(url_for('menu'))

    user_id = session.get('user_id')

    if request.method == 'POST':
        event_id = request.form.get('event')

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # 重複チェック
        c.execute('SELECT id FROM reservations WHERE event_id = ? AND user_id = ?', (event_id, user_id))
        existing = c.fetchone()
        if existing:
            conn.close()
            flash("既にこのイベントに予約済みです。")
            return redirect(url_for('new_booking'))

        # イベント予約
        c.execute('INSERT INTO reservations (event_id, user_id) VALUES (?, ?)', (event_id, user_id))
        conn.commit()
        conn.close()

        flash("予約が完了しました。")
        return redirect(url_for('new_booking'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, date FROM events ORDER BY date')
    events = c.fetchall()
    conn.close()
    return render_template('success.html', events=events)

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/register_success', methods=['GET', 'POST'])
def act_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        confirm_email = request.form['confirm_email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        terms = request.form.get('terms')

        error = None

        # 入力チェック
        email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Za-z\d!-/:-@[-`{-~]{8,}$'

        if email != confirm_email:
            error = "メールアドレスが一致しません。"
        elif not re.match(email_pattern, email):
            error = "メールアドレスが正しくありません。"
        elif not re.match(password_pattern, password):
            error = "パスワードは英語数字記号を含む、8文字以上で入力してください。"
        elif password != confirm_password:
            error = "パスワードが一致しません。"
        elif not terms:
            error = "個人情報保護方針が確認できていません。"
            
        if error:
            return render_template('register.html', error=error,
                                   name=name, email=email,
                                   confirm_email=confirm_email,
                                   password=password,
                                   confirm_password=confirm_password,
                                   terms=terms)

        # メール暗号化とパスワードハッシュ化
        email_hash = hash_email(email)
        encrypted_email = encrypt_email(email)
        hashed_password = generate_password_hash(password)

        # メールアドレス重複チェック
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT user_id FROM user WHERE email_hash = ?', (email_hash ,))
        row = c.fetchone()
        conn.close()
        if row:
            error = "既に登録されているメールアドレスです。"
            return render_template('register.html', error=error)

        # 新規登録
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO user (name, email, email_hash, password) VALUES (?, ?, ?, ?)',
                  (name, encrypted_email, email_hash, hashed_password))
        conn.commit()
        conn.close()

        return render_template('register_success.html', email=email)

    return render_template('register.html')

@app.route('/new_booking', methods=['GET','POST'])
def new_booking():
    if not session.get('login_ok'):
        return render_template('home.html')

    user_id = session.get('user_id')  # セッションから直接取得
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, date FROM events ORDER BY date')
    events = c.fetchall()
    conn.close()

    return render_template('new_booking.html', user_id=user_id, events=events)

@app.route('/return_menu', methods=['GET'])
def return_menu():
    if not session.get('login_ok'):
        return render_template('home.html')
    
    return render_template('menu.html')
    
@app.route('/reservation_confirmation', methods=['GET'])
def reservation_confirmation():
    if not session.get('login_ok'):
        return render_template('home.html')
    user_id = session.get('user_id')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, name FROM user WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        flash("ユーザーが見つかりません")
        return redirect(url_for('home'))

    user_id, user_name = row

    c.execute('''
        SELECT e.name, e.date
        FROM reservations r
        JOIN events e ON r.event_id = e.id
        WHERE r.user_id = ?
        ORDER BY e.date
    ''', (user_id,))
    reservations = c.fetchall()
    conn.close()

    return render_template('reservation_confirmation.html', reservations=reservations, user_name=user_name)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/handle_form', methods=['GET', 'POST'])
def handle_form():
    action = request.form.get('action')
    error = None

    if action == 'login' and request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # 暗号化メールで検索
        email_hash = hash_email(email)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT user_id, name, email, password FROM user WHERE email_hash = ?', (email_hash ,))
        user = c.fetchone()
        conn.close()

        if not user or not check_password_hash(user[3], password):
            error = "メールアドレスまたはパスワードが間違っています。"
        else:
            session.clear()
            session['login_ok'] = True
            session['user_id'] = user[0]
            session['user_email'] = decrypt_email(user[2])
            return render_template('menu.html', reservations=[user])

    elif action == 'register':
        return render_template('register.html')

    return render_template('home.html', error=error)

@app.route('/hibiowner', methods=['GET'])
def hibiowner():
    return render_template('admin_login.html')

@app.route('/admin_password', methods=['GET', 'POST'])
def admin_password():
    error = None
    action = request.form.get('action')
    if action == 'admin_login' and request.method == 'POST':
        password = request.form['password']
        if "0214wellness1106" != password:
            error = "パスワードが間違っています。"
        else:
            session.clear()
            session['is_admin'] = True  # 管理者セッションを設定
            return redirect(url_for('admin'))
    return render_template('admin_login.html', error=error)

@app.route('/admin', methods=['GET'])
def admin():
    # 管理者権限チェック
    if not session.get('is_admin'):
        return redirect(url_for('hibiowner'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, attendance , date FROM events ORDER BY date')
    events = [dict(id=row[0], name=row[1], attendance=row[2], date=row[3]) for row in c.fetchall()]

    c.execute('''
        SELECT u.name, u.email, e.name
        FROM reservations r
        JOIN user u ON r.user_id = u.user_id
        JOIN events e ON r.event_id = e.id
        ORDER BY r.id DESC
    ''')
    reservations = [(n, decrypt_email(e), ev) for n, e, ev in c.fetchall()]

    c.execute('''
        SELECT u.email, COUNT(*)
        FROM reservations r
        JOIN user u ON r.user_id = u.user_id
        GROUP BY u.user_id
    ''')
    email_counts = {decrypt_email(k): v for k, v in c.fetchall()}

    c.execute('''
        SELECT e.name, COUNT(r.id)
        FROM reservations r
        JOIN events e ON r.event_id = e.id
        GROUP BY e.id
    ''')
    event_counts = c.fetchall()

    conn.close()
    return render_template('admin.html', events=events, reservations=reservations,
                           email_counts=email_counts, event_counts=event_counts)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
