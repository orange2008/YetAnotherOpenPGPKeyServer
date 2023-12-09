from flask import Flask, request, jsonify, render_template
import sqlite3
import time

app = Flask(__name__)

# Initialize the database
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            email TEXT,
            keyid TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Add keys to the database
def add_keys_to_database(content, email, keyid):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('INSERT INTO keys (content, email, keyid, timestamp) VALUES (?, ?, ?, ?)', 
              (content, email, keyid, time.ctime()))
    conn.commit()
    conn.close()

@app.route('/upload_keys', methods=['POST'])
def add_keys():
    try:
        data = request.get_json(force=True)
        content = data.get('content')
        email = data.get('email')
        keyid = data.get('keyid')
    except Exception as e:
        return jsonify(error=str(e)), 400

    # Check if the content is a valid OpenPGP key
    if 'PGP' not in content:
        return jsonify(error="Not valid OpenPGP key"), 401

    # Check if the content is longer than 64 kilobytes
    if len(content.encode('utf-8')) > 64 * 1024:
        return jsonify(error="Content exceeds size limit of 64 kilobytes"), 401

    if content and email and keyid:
        add_keys_to_database(content, email, keyid)
        return jsonify(message="Content added successfully"), 201
    else:
        return jsonify(error="Missing content, email, or keyid"), 400


@app.route('/get_keys', methods=['GET'])
def get_keys():
    email = request.args.get('email')
    keyid = request.args.get('keyid')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    if email:
        c.execute('SELECT * FROM keys WHERE email = ?', (email,))
    elif keyid:
        c.execute('SELECT * FROM keys WHERE keyid = ?', (keyid,))
    else:
        conn.close()
        return jsonify(error="email or keyid required"), 400

    rows = c.fetchall()

    if not rows:
        conn.close()
        return jsonify(error="No records found for the provided email or keyid"), 404

    conn.close()

    posts = [dict(id=row[0], content=row[1], email=row[2], keyid=row[3], timestamp=row[4]) for row in rows]
    return jsonify(posts)

@app.route('/search_keys', methods=['GET'])
def search_keys():
    email = request.args.get('email')
    keyid = request.args.get('keyid')

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    query = 'SELECT * FROM keys WHERE '
    query_params = []

    # Building the query based on provided parameters
    if email:
        query += 'email = ? '
        query_params.append(email)

    if keyid:
        if len(keyid) < 8:
            conn.close()
            return jsonify(error="keyid must be at least 8 characters long"), 400

        if email:
            query += 'AND '
        query += 'keyid LIKE ?'
        keyid_pattern = '%' + keyid[-8:]  # Use the last 8 characters for matching
        query_params.append(keyid_pattern)

    if not (email or keyid):
        conn.close()
        return jsonify(error="Email or keyid required"), 400

    c.execute(query, query_params)
    rows = c.fetchall()

    if not rows:
        conn.close()
        return jsonify(error="No keys were found"), 404

    conn.close()

    # Formatting the result
    keys = [dict(id=row[0], content=row[1], email=row[2], keyid=row[3], timestamp=row[4]) for row in rows]
    return jsonify(keys=keys)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8000)
