#!/usr/bin/env python

import sqlite3, re
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
import accounts

#Note: config is in "config.py"

#initialize app
app = Flask(__name__)
app.config.from_pyfile('config.py')

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

#create db and connect to it
def init_db():
    with closing(connect_db()) as db:
#        with app.open_resource('schema.sql', mode='r') as f:
#            db.cursor().executescript(f.read())
#        db.commit()
        with app.open_resource('accounts.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    'do this before each request'
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    'do this after each request, even if there was an error'
    db = getattr(g, 'db', None)
    # "g" is a special Flask var that stores info for the current request
    if db is not None:
        db.close()

@app.route('/') # run the function below when "/" is requested
def show_entries(): #function name matches the endpoint: "/show_entries"
    'get entries from db and display in show_entries.html'
    cur = g.db.execute('SELECT * FROM entries ORDER BY time desc')
    entries = [dict(id=row[0], title=row[1], text=row[2], time=row[3], submitter=row[4]) for row in cur.fetchall()] #each row is a tuple: (TITLE, TEXT)
    return render_template('show_entries.html', css=[], js=[], entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute(
        'INSERT INTO entries (title, text, submitter) VALUES (?,?,?)',
        # ? is a variable ; string concatenation can cause sql injection
        [request.form['title'], request.form['text'], session['username']] # replaces both question marks
    )
    g.db.commit()
    flash('New entry was successfully posted.')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
#        if request.form['username'] != app.config['USERNAME']:
#            error = 'Invalid username!'
#        elif request.form['password'] != app.config['PASSWORD']:
#            error = 'Invalid password!'
#        else:
#            session['logged_in'] = True
#            flash('You were logged in.')
#            return redirect(url_for('show_entries'))
#    return render_template('login.html', error=error)
        username = request.form['username']
        password = request.form['password']
        verify = accounts.verify_login(g.db, username, password)
        if verify[0]:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('Login successful!')
            return redirect(url_for('show_entries'))
        else:
            error = verify[1]
            return render_template('login.html', css=[], js=[], error=error)
    else:
        return render_template('login.html', css=[], js=[], error=error)

@app.route('/logout') #has to be POST request
def logout():
    session.pop('logged_in', None)
    flash('You were logged out.')
    return redirect(url_for('show_entries'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        valid_info = True
        #check for valid info
        if not re.match(r'^(\w\w+)$', request.form['username']):
            flash('Username must be alphanumeric and at least 2 characters')
            valid_info = False
        if not re.match(r'^(.{4,32})$', request.form['password']):
            flash('Password must be 4 to 32 characters long')
            valid_info = False
        if request.form['password'] != request.form['confirm_password']:
            flash('Passwords do not match')
            valid_info = False

        if valid_info:
            try:
                accounts.add_account(g.db, request.form['username'], request.form['password'])
                flash('Registration successful!')
                return redirect(url_for('show_entries'))
            except accounts.AccountsError:
                flash('That username already exists.')
                return render_template('register.html', css=['register.css'], js=[])
        else:
            return render_template('register.html', css=['register.css'], js=[])
    if request.method == 'GET':
        return render_template('register.html', css=['register.css'], js=[])

if __name__ == '__main__':
    app.run()
