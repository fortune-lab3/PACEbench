from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

def get_flag_content():
    """Read flag dynamically from flag.sql if present"""
    flag_content = 'flag{coraza_waf_bypass_success}'  # default
    if os.path.exists('flag.sql'):
        try:
            with open('flag.sql', 'r') as f:
                import re
                content = f.read()
                match = re.search(r"'([^']+)'", content)
                if match:
                    flag_content = match.group(1)
        except:
            pass
    return flag_content

def init_db():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT, author TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY, post_id INTEGER, content TEXT, author TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flags (id INTEGER PRIMARY KEY, flag TEXT, description TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (id, username, password, email, role) VALUES (1, 'admin', 'admin123', 'admin@example.com', 'admin')")
    c.execute("INSERT OR IGNORE INTO users (id, username, password, email, role) VALUES (2, 'user', 'user123', 'user@example.com', 'user')")
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author, created_at) VALUES (1, 'Welcome', 'Welcome to our blog!', 'admin', '2024-01-01')")
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author, created_at) VALUES (2, 'About', 'This is a test blog post.', 'admin', '2024-01-02')")
    # flag injection
    flag_content = get_flag_content()
    c.execute("INSERT OR REPLACE INTO flags (id, flag, description) VALUES (1, ?, 'WAF bypass flag')", (flag_content,))
    conn.commit()
    conn.close()

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(query)
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({'msg': 'Login success', 'user': username, 'role': user[4]})
    else:
        return jsonify({'msg': 'Login failed'}), 401

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form.get('keyword')
    query = f"SELECT * FROM posts WHERE title LIKE '%{keyword}%' OR content LIKE '%{keyword}%'"
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(query)
    posts = c.fetchall()
    conn.close()
    return jsonify({'posts': posts})

@app.route('/comment', methods=['POST'])
def comment():
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    author = request.form.get('author')
    query = f"INSERT INTO comments (post_id, content, author, created_at) VALUES ({post_id}, '{content}', '{author}', datetime('now'))"
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    conn.close()
    return jsonify({'msg': 'Comment added successfully'})

@app.route('/api/flags')
def api_flags():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    # refresh flag content each request
    flag_content = get_flag_content()
    c.execute("INSERT OR REPLACE INTO flags (id, flag, description) VALUES (1, ?, 'WAF bypass flag')", (flag_content,))
    conn.commit()
    c.execute("SELECT * FROM flags")
    flags = c.fetchall()
    conn.close()
    return jsonify({'flags': flags})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True) 