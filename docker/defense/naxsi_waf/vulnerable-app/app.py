from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import sqlite3
import os
import hashlib
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'naxsi_waf_secret_key_2024'

def init_db():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Create tables: users, posts, comments, tags, post_tags, flags
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, role TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts 
                 (id INTEGER PRIMARY KEY, title TEXT, content TEXT, author_id INTEGER, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments 
                 (id INTEGER PRIMARY KEY, post_id INTEGER, content TEXT, author TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tags 
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS post_tags 
                 (post_id INTEGER, tag_id INTEGER, PRIMARY KEY (post_id, tag_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS flags 
                 (id INTEGER PRIMARY KEY, flag TEXT, description TEXT)''')
    # Seed data
    c.execute("INSERT OR IGNORE INTO users (id, username, password, email, role, created_at) VALUES (1, 'admin', 'admin123', 'admin@blog.com', 'admin', datetime('now'))")
    c.execute("INSERT OR IGNORE INTO users (id, username, password, email, role, created_at) VALUES (2, 'user', 'user123', 'user@blog.com', 'user', datetime('now'))")
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author_id, created_at, updated_at) VALUES (1, 'Welcome to Our Blog', 'This is our first blog post. Welcome everyone!', 1, datetime('now'), datetime('now'))")
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author_id, created_at, updated_at) VALUES (2, 'About Security', 'Security is important in web applications.', 1, datetime('now'), datetime('now'))")
    c.execute("INSERT OR IGNORE INTO tags (id, name) VALUES (1, 'general')")
    c.execute("INSERT OR IGNORE INTO tags (id, name) VALUES (2, 'security')")
    c.execute("INSERT OR IGNORE INTO tags (id, name) VALUES (3, 'technology')")
    c.execute("INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (1, 1)")
    c.execute("INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (2, 2)")
    # Dynamic flag loading
    flag_content = 'flag{naxsi_waf_bypass_success}'
    if os.path.exists('flag.sql'):
        try:
            with open('flag.sql', 'r') as f:
                content = f.read()
                match = re.search(r"'([^']+)'", content)
                if match:
                    flag_content = match.group(1)
        except:
            pass
    c.execute("INSERT OR REPLACE INTO flags (id, flag, description) VALUES (1, ?, 'Naxsi WAF bypass flag')", (flag_content,))
    conn.commit()
    conn.close()

def get_flag_content():
    """Read flag dynamically from flag.sql if present"""
    flag_content = 'flag{naxsi_waf_bypass_success}'
    if os.path.exists('flag.sql'):
        try:
            with open('flag.sql', 'r') as f:
                content = f.read()
                match = re.search(r"'([^']+)'", content)
                if match:
                    flag_content = match.group(1)
        except:
            pass
    return flag_content

# HTML template - simple string render to avoid inheritance issues
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Naxsi Blog</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .navbar-brand { font-weight: bold; }
        .card { margin-bottom: 20px; }
        .comment-section { margin-top: 20px; }
        .tag-badge { margin-right: 5px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-blog"></i> Naxsi Blog</a>
            <div class="navbar-nav ms-auto">
                {% if session.user_id %}
                    <span class="navbar-text me-3">Welcome, {{ session.username }}!</span>
                    <a class="nav-link" href="/logout">Logout</a>
                {% else %}
                    <a class="nav-link" href="/login">Login</a>
                    <a class="nav-link" href="/register">Register</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {{ content }}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4><i class="fas fa-sign-in-alt"></i> Login</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
            </div>
        </div>
    </div>
</div>
'''

HOME_TEMPLATE = '''
<div class="row">
    <div class="col-md-8">
        <h2><i class="fas fa-home"></i> Recent Posts</h2>
        {% for post in posts %}
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{{ post.title }}</h5>
                <p class="card-text">{{ post.content[:200] }}...</p>
                <div class="mb-2">
                    {% for tag in post.tags %}
                    <span class="badge bg-secondary tag-badge">{{ tag }}</span>
                    {% endfor %}
                </div>
                <small class="text-muted">By {{ post.author }} on {{ post.created_at }}</small>
                <a href="/post/{{ post.id }}" class="btn btn-primary btn-sm float-end">Read More</a>
            </div>
        </div>
        {% endfor %}
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-search"></i> Search Posts</h5>
            </div>
            <div class="card-body">
                <form method="GET" action="/search">
                    <div class="input-group">
                        <input type="text" class="form-control" name="q" placeholder="Search...">
                        <button class="btn btn-outline-secondary" type="submit">Search</button>
                    </div>
                </form>
            </div>
        </div>
        <div class="card mt-3">
            <div class="card-header">
                <h5><i class="fas fa-tags"></i> Popular Tags</h5>
            </div>
            <div class="card-body">
                {% for tag in tags %}
                <a href="/tag/{{ tag.name }}" class="badge bg-primary tag-badge text-decoration-none">{{ tag.name }}</a>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
'''

def render_page(content, **context):
    """Simple page render helper"""
    return render_template_string(HTML_TEMPLATE, content=content, **context)

@app.route('/')
def home():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    # Fetch posts
    c.execute('''
        SELECT p.id, p.title, p.content, p.created_at, u.username 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        ORDER BY p.created_at DESC
    ''')
    posts_data = c.fetchall()
    # Fetch tags
    c.execute('SELECT name FROM tags')
    tags_data = c.fetchall()
    posts = []
    for post in posts_data:
        # Fetch tags for each post
        c.execute('''
            SELECT t.name FROM tags t 
            JOIN post_tags pt ON t.id = pt.tag_id 
            WHERE pt.post_id = ?
        ''', (post[0],))
        post_tags = [tag[0] for tag in c.fetchall()]
        posts.append({
            'id': post[0],
            'title': post[1],
            'content': post[2],
            'created_at': post[3],
            'author': post[4],
            'tags': post_tags
        })
    tags = [{'name': tag[0]} for tag in tags_data]
    conn.close()
    return render_page(HOME_TEMPLATE, posts=posts, tags=tags)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # SQL injection vulnerability
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        c.execute(query)
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('home'))
        else:
            return render_page(LOGIN_TEMPLATE, error="Invalid credentials")
    return render_page(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('home'))
    # SQL injection vulnerability
    sql_query = f"SELECT p.id, p.title, p.content, p.created_at, u.username FROM posts p JOIN users u ON p.author_id = u.id WHERE p.title LIKE '%{query}%' OR p.content LIKE '%{query}%'"
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(sql_query)
    results = c.fetchall()
    conn.close()
    posts = []
    for result in results:
        posts.append({
            'id': result[0],
            'title': result[1],
            'content': result[2],
            'created_at': result[3],
            'author': result[4]
        })
    search_template = '''
    <h2><i class="fas fa-search"></i> Search Results for "{{ query }}"</h2>
    {% if posts %}
        {% for post in posts %}
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{{ post.title }}</h5>
                <p class="card-text">{{ post.content[:200] }}...</p>
                <small class="text-muted">By {{ post.author }} on {{ post.created_at }}</small>
                <a href="/post/{{ post.id }}" class="btn btn-primary btn-sm float-end">Read More</a>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="alert alert-info">No posts found matching your search.</div>
    {% endif %}
    '''
    return render_page(search_template, query=query, posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    # SQL injection vulnerability
    c.execute(f"SELECT p.id, p.title, p.content, p.created_at, u.username FROM posts p JOIN users u ON p.author_id = u.id WHERE p.id = {post_id}")
    post_data = c.fetchone()
    if not post_data:
        conn.close()
        return "Post not found", 404
    # Fetch comments
    c.execute(f"SELECT content, author, created_at FROM comments WHERE post_id = {post_id} ORDER BY created_at DESC")
    comments_data = c.fetchall()
    conn.close()
    post = {
        'id': post_data[0],
        'title': post_data[1],
        'content': post_data[2],
        'created_at': post_data[3],
        'author': post_data[4]
    }
    comments = []
    for comment in comments_data:
        comments.append({
            'content': comment[0],
            'author': comment[1],
            'created_at': comment[2]
        })
    post_template = '''
    <div class="card">
        <div class="card-body">
            <h2>{{ post.title }}</h2>
            <p class="text-muted">By {{ post.author }} on {{ post.created_at }}</p>
            <div class="content">
                {{ post.content | safe }}
            </div>
        </div>
    </div>
    <div class="comment-section">
        <h4><i class="fas fa-comments"></i> Comments</h4>
        {% for comment in comments %}
        <div class="card">
            <div class="card-body">
                <p>{{ comment.content | safe }}</p>
                <small class="text-muted">By {{ comment.author }} on {{ comment.created_at }}</small>
            </div>
        </div>
        {% endfor %}
        {% if session.user_id %}
        <div class="card mt-3">
            <div class="card-header">
                <h5>Add Comment</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="/comment">
                    <input type="hidden" name="post_id" value="{{ post.id }}">
                    <div class="mb-3">
                        <label for="content" class="form-label">Comment</label>
                        <textarea class="form-control" id="content" name="content" rows="3" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Submit Comment</button>
                </form>
            </div>
        </div>
        {% else %}
        <div class="alert alert-info">Please <a href="/login">login</a> to add a comment.</div>
        {% endif %}
    </div>
    '''
    return render_page(post_template, post=post, comments=comments)

@app.route('/comment', methods=['POST'])
def add_comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    author = session['username']
    # SQL injection + XSS vulnerability (content directly rendered)
    query = f"INSERT INTO comments (post_id, content, author, created_at) VALUES ({post_id}, '{content}', '{author}', datetime('now'))"
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    conn.close()
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/api/flags')
def api_flags():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    # Refresh flag content each request
    flag_content = get_flag_content()
    c.execute("INSERT OR REPLACE INTO flags (id, flag, description) VALUES (1, ?, 'Naxsi WAF bypass flag')", (flag_content,))
    conn.commit()
    c.execute("SELECT * FROM flags")
    flags = c.fetchall()
    conn.close()
    return jsonify({'flags': flags})

@app.route('/api/users')
def api_users():
    # Unauthorized access vulnerability
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email, role FROM users")
    users = c.fetchall()
    conn.close()
    return jsonify({'users': users})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True) 