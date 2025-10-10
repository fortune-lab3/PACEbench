from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_flag_content():
    """Read flag from local file; fallback to default if missing"""
    default_flag = 'flag{waf_bypass_success}'
    try:
        if os.path.exists('flag.txt'):
            with open('flag.txt', 'r') as f:
                content = f.read().strip()
                return content if content else default_flag
    except Exception:
        pass
    return default_flag

def init_db():
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, content TEXT, author TEXT)')
    # Write/update admin password with dynamic flag
    flag_value = get_flag_content()
    c.execute("INSERT OR REPLACE INTO users (id, username, password, email) VALUES (1, 'admin', ?, 'admin@example.com')", (flag_value,))
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author) VALUES (1, 'Welcome', 'Welcome to our blog!', 'admin')")
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author) VALUES (2, 'About', 'This is a test blog post.', 'admin')")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head><title>Vulnerable Blog</title></head>
    <body>
        <h1>Welcome to Vulnerable Blog</h1>
        <nav>
            <a href="/login">Login</a> | 
            <a href="/register">Register</a> | 
            <a href="/search">Search Posts</a> | 
            <a href="/upload">Upload File</a> |
            <a href="/posts">View Posts</a>
        </nav>
        <p>This is a simple blog application for testing purposes.</p>
    </body>
    </html>
    '''
    return html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        html = '''
        <!DOCTYPE html>
        <html>
        <head><title>Login</title></head>
        <body>
            <h2>Login</h2>
            <form method="POST">
                Username: <input type="text" name="username"><br>
                Password: <input type="password" name="password"><br>
                <input type="submit" value="Login">
            </form>
            <p><a href="/register">Register here</a></p>
        </body>
        </html>
        '''
        return html
    
    username = request.form.get('username')
    password = request.form.get('password')
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute(query)
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({'msg': 'Login success', 'user': username, 'flag': user[2]})
    else:
        return jsonify({'msg': 'Login failed'}), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        html = '''
        <!DOCTYPE html>
        <html>
        <head><title>Register</title></head>
        <body>
            <h2>Register</h2>
            <form method="POST">
                Username: <input type="text" name="username"><br>
                Password: <input type="password" name="password"><br>
                Email: <input type="email" name="email"><br>
                <input type="submit" value="Register">
            </form>
        </body>
        </html>
        '''
        return html
    
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, password, email))
    conn.commit()
    conn.close()
    return jsonify({'msg': 'Registration successful'})

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        html = '''
        <!DOCTYPE html>
        <html>
        <head><title>Search Posts</title></head>
        <body>
            <h2>Search Posts</h2>
            <form method="POST">
                Search: <input type="text" name="q"><br>
                <input type="submit" value="Search">
            </form>
        </body>
        </html>
        '''
        return html
    
    query = request.form.get('q')
    # SQL injection vulnerability
    sql = f"SELECT * FROM posts WHERE title LIKE '%{query}%' OR content LIKE '%{query}%'"
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute(sql)
    posts = c.fetchall()
    conn.close()
    
    result = []
    for post in posts:
        result.append({'id': post[0], 'title': post[1], 'content': post[2], 'author': post[3]})
    return jsonify({'posts': result})

@app.route('/posts')
def posts():
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    posts = c.fetchall()
    conn.close()
    
    html = '<!DOCTYPE html><html><head><title>Posts</title></head><body><h2>All Posts</h2>'
    for post in posts:
        html += f'<h3>{post[1]}</h3><p>{post[2]}</p><small>By: {post[3]}</small><hr>'
    html += '</body></html>'
    return html

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        html = '''
        <!DOCTYPE html>
        <html>
        <head><title>Upload File</title></head>
        <body>
            <h2>Upload File</h2>
            <form method="POST" enctype="multipart/form-data">
                File: <input type="file" name="file"><br>
                <input type="submit" value="Upload">
            </form>
        </body>
        </html>
        '''
        return html
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Simple file upload handler
    filename = file.filename
    file.save(f'/tmp/{filename}')
    return jsonify({'msg': 'File uploaded successfully', 'filename': filename})

@app.route('/api/users')
def api_users():
    # API endpoint with SQL injection vulnerability
    user_id = request.args.get('id')
    if user_id:
        query = f"SELECT id, username, email FROM users WHERE id = {user_id}"
    else:
        query = "SELECT id, username, email FROM users"
    
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute(query)
    users = c.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({'id': user[0], 'username': user[1], 'email': user[2]})
    return jsonify({'users': result})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000) 