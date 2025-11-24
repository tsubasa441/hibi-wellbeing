from flask import Flask, flash, render_template, request, redirect, url_for
import sqlite3
from datetime import date, datetime
import os
import secrets
import re

## シークレットキー挿入
app = Flask(__name__)
secret = secrets.token_urlsafe(32)
app.config['SECRET_KEY'] = secret


print(secrets.token_urlsafe(32))


DB_NAME = 'database.db'

@app.route('/')
def home():
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
    # reservationsテーブルはそのまま
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id)
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    ''')
    # userテーブルはそのまま
    c.execute('''
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            is_provisional BOOL DEFAULT TRUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/customer_request', methods=['GET', 'POST'])
def customer_request():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, date FROM events ORDER BY id')
    rows = c.fetchall()
    conn.close()

    events = []
    for id_, name, date_str in rows:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = dt.strftime('%Y/%m/%d')
        events.append((id_, name, formatted_date))

    if request.method == 'POST':
        name = request.form['name']
        event_id = request.form['event']
        email = request.form['email']
        confirm_email = request.form['confirm_email']
        password = request.form['password']
        comment = request.form.get('comment', '')
        terms = request.form.get('terms')

        error = None

        # ====== ✅ パスワードチェック追加 ======
        password_pattern = r'^[A-Za-z0-9]{8,16}$'
        if not re.match(password_pattern, password):
            error = "パスワードは半角英数字のみ、8～16文字で入力してください。"
        elif email != confirm_email:
            error = "メールアドレスが一致しません。"
        elif not terms:
            error = "個人情報保護方針が確認できていません。"
        # =======================================

        if error:
            return render_template('index.html', events=events, error=error)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 重複チェック
        c.execute('SELECT id FROM reservations WHERE email = ? AND event_id = ?', (email, event_id))
        existing = c.fetchone()

        if existing:
            conn.close()
            error = "既にこのイベントに予約済みです。"
            return render_template('new_booking.html', events=events, error=error)

        # 新規登録
        c.execute('INSERT INTO reservations (name, email, password, event_id, comment) VALUES (?, ?, ?, ?, ?)',
                  (name, email, password, event_id, comment))
        conn.commit()
        conn.close()

        return redirect(url_for('success'))

    return render_template('index.html', events=events)

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

        # ============= 入力チェック ==============
        password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Za-z\d!-/:-@[-`{-~]{8,}$'
        if email != confirm_email:
            error = "メールアドレスが一致しません。"
        elif not re.match(password_pattern, password):
            error = "パスワードは英語数字記号を含む、8文字以上で入力してください。"
        elif password != confirm_password:
            error = "パスワードが一致しません。"

        elif not terms:
            error = "個人情報保護方針が確認できていません。"
        # ========================================
            
        if error:
            return render_template('register.html',   error=error,
                name=name,
                email=email,
                confirm_email=confirm_email,
                password=password,
                confirm_password=confirm_password,
                terms=terms)
        # ============= メールアドレス重複チェック ==============
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT user_id FROM user WHERE email == ?',(email,))
        row = c.fetchall()
        conn.close()
        if row.__len__() != 0:
            error = "既に登録されているメールアドレスです。"
        # =======================================================
        
        if error:
            return render_template('register.html',  error=error)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 新規登録
        cursor.execute('INSERT INTO user (name, email, password) VALUES (?, ?, ?)',
                  (name, email, password))
        conn.commit()
        conn.close()
        
        # リソース消去
        request.close()

        return render_template('register_success.html',email = email)
    
    return render_template('register.html',)

@app.route('/new_booking', methods=['GET', 'POST'])
def new_booking():
    return render_template('new_booking.html')

@app.route('/reservation_confirmation', methods=['GET', 'POST'])
def reservation_confirmation():
    return render_template('reservation_confirmation.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/handle_form', methods=['GET', 'POST'])
def handle_form():
    action = request.form.get('action')
    if action == 'login':
        if request.method == 'POST':
            error = None
            reservations = []
            email = request.form['email']
            password = request.form['password']

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT 
                u.name AS user_name,
                u.email AS user_email
                FROM  user u 
                WHERE u.email = ? 
                AND u.password = ?
            ''', (email, password))
            reservations = c.fetchall()
            conn.close()
            
            if not reservations:
                error = "メールアドレスまたはパスワードが間違っています。"
            else:
                return render_template('menu.html', reservations=reservations)
    elif action == 'register':
        return redirect(url_for('register'))
    
    return render_template('home.html', error=error)

@app.route('/admin', methods=['GET'])
def admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # イベント一覧取得（id, name, date）
    c.execute('SELECT id, name, attendance , date FROM events ORDER BY date')
    events = [dict(id=row[0], name=row[1],attendance=row[2], date=row[3]) for row in c.fetchall()]

    # 予約一覧（名前・メール・イベント名）
    c.execute('''
        SELECT u.name, u.email, e.name
        FROM reservations r
        JOIN user u ON r.user_id = u.user_id
        JOIN events e ON r.event_id = e.id
        ORDER BY r.id DESC
    ''')
    reservations = c.fetchall()

    # メールごとの予約回数
    c.execute('''
        SELECT COUNT(*)
        FROM reservations r
        JOIN user u
        ON r.user_id = u.user_id  GROUP BY u.user_id
        ''')
    email_counts = dict(c.fetchall())

    # イベント別参加人数
    c.execute('''
        SELECT e.name, COUNT(r.id)
        FROM reservations r
        JOIN events e ON r.event_id = e.id
        GROUP BY e.id
    ''')
    event_counts = c.fetchall()

    conn.close()

    return render_template('admin.html',
                           events=events,
                           reservations=reservations,
                           email_counts=email_counts,
                           event_counts=event_counts)

@app.route('/mainmenu', methods=['POST'])
def mainmenu():
    error = None
    account = []
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute('''
            SELECT r.email, e.password
            FROM reservations r
            JOIN events e ON r.event_id = e.id
            WHERE r.email = ? AND r.password = ?
        ''', (email, password))
        account = c.fetchall()
        conn.close()
    if not account:
        error = "メールアドレスまたはパスワードが間違っています。"
    else:
        return render_template('reservation_list.html', account=account)
    
    return render_template('mainmenu.html', error=error)
    
@app.route('/admin/events', methods=['POST'])
def add_event():
    event_name = request.form.get('event_name')
    event_attendance = request.form.get('event_attendance')
    event_date = request.form.get('event_date')
    ## 入力チェック
    if ((event_name and event_date and event_attendance)==False):
        flash("入力されていない項目があります", "error")
        conn.close()
        return redirect(url_for('admin'))
    
    try:
        event_date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
        if event_date_obj < date.today():
            flash("開催日は本日以降の日付を指定してください。", "error")
            return redirect(url_for('admin'))
    except ValueError:
        flash("日付の形式が不正です。", "error")
        return redirect(url_for('admin'))
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM events WHERE name = ?', (event_name,))
    
    ## 登録されている場合
    if c.fetchone():
        flash("既に登録されているイベントです。", "error")
        conn.close()
        return redirect(url_for('admin'))
    
    flash("イベント「"+event_name+"」を追加しました。", "success")
    c.execute('INSERT INTO events (attendance, name, date) VALUES (?,?,?)', (event_attendance, event_name, event_date))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/events/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 予約に紐づく場合は制御したいですが、今回はシンプルに削除
    c.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
