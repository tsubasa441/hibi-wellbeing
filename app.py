from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os
import secrets

print(secrets.token_urlsafe(32))

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY")
app.config['SECRET_KEY'] = SECRET_KEY

DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # eventsテーブルの再作成時に日付カラム追加
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL
        )
    ''')
    # reservationsテーブルはそのまま
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            event_id INTEGER NOT NULL,
            comment TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def customer_form():
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
        comment = request.form.get('comment', '')
        terms = request.form.get('terms')

        error = None
        if email != confirm_email:
            error = "メールアドレスが一致しません。"
        elif not terms:
            error = "利用規約に同意してください。"

        if error:
            return render_template('index.html', events=events, error=error)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # ここで予約の重複チェック（必要に応じて）
        c.execute('SELECT id FROM reservations WHERE email = ? AND event_id = ?', (email, event_id))
        existing = c.fetchone()

        if existing:
            conn.close()
            error = "既にこのイベントに予約済みです。"
            return render_template('index.html', events=events, error=error)

        # 新規登録
        c.execute('INSERT INTO reservations (name, email, event_id, comment) VALUES (?, ?, ?, ?)',
                  (name, email, event_id, comment))
        conn.commit()
        conn.close()

        return redirect(url_for('success'))

    # GETの場合は普通にフォーム表示
    return render_template('index.html', events=events)

@app.route('/success')
def success():
    return "<h1>予約を受け付けました。ありがとうございました！</h1>"

@app.route('/admin', methods=['GET'])
def admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # イベント一覧取得（id, name, date）
    c.execute('SELECT id, name, date FROM events ORDER BY date')
    events = [dict(id=row[0], name=row[1], date=row[2]) for row in c.fetchall()]

    # 予約一覧（名前・メール・イベント名）
    c.execute('''
        SELECT r.name, r.email, e.name
        FROM reservations r
        JOIN events e ON r.event_id = e.id
        ORDER BY r.id DESC
    ''')
    reservations = c.fetchall()

    # メールごとの予約回数
    c.execute('SELECT email, COUNT(*) FROM reservations GROUP BY email')
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

@app.route('/admin/events', methods=['POST'])
def add_event():
    event_name = request.form.get('event_name')
    event_date = request.form.get('event_date')
    if event_name and event_date:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT id FROM events WHERE name = ?', (event_name,))
        if not c.fetchone():
            c.execute('INSERT INTO events (name, date) VALUES (?, ?)', (event_name, event_date))
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
    app.run()
