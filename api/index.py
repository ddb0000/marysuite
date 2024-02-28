from flask import Flask, request, redirect, url_for, flash, render_template_string
from flask_pymongo import PyMongo, ObjectId
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__)
app.config.update(MONGO_URI=os.getenv("MONGO_URI"), SECRET_KEY=os.getenv("SECRET_KEY"))
mongo, bcrypt = PyMongo(app), Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_logout'

User = type('User', (UserMixin,), {"__init__": lambda self, user_id: setattr(self, 'id', str(user_id))})
login_manager.user_loader(lambda user_id: User(str(user_id)) if mongo.db.users.find_one({"_id": ObjectId(user_id)}) else None)

def render_html(title, body):
    return render_template_string("<html><head><title>{{ title }}</title></head><body>{{ body | safe }}</body></html>", title=title, body=body)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dash'))
    body = '<h1>MarySuite - Your Herb Tracker</h1>'
    if not current_user.is_authenticated:
        body += '<a href="/login">Login</a> | <a href="/register">Register</a>'
    else:
        body += '<a href="/dash">Dashboard</a> | <form method="post" action="/login?logout=true"><input type="submit" value="Logout"></form>'
    return render_html('Home - MarySuite', body)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dash'))
    if request.method == 'POST':
        user = mongo.db.users.find_one({'name': request.form['username']})
        if user and bcrypt.check_password_hash(user['password'], request.form['password']):
            login_user(User(str(user['_id'])))
            flash('Logged in successfully!')
            return redirect(url_for('dash'))
        flash('Invalid username/password combination')
    body = '<form method="POST"><input type="text" name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required><input type="submit" value="Login"></form>'
    return render_html('Login', body)

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if mongo.db.users.find_one({'name': request.form['username']}):
            flash('Username already exists.')
        else:
            mongo.db.users.insert_one({
                'name': request.form['username'],
                'password': bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            })
            flash('Registration successful!')
            return redirect(url_for('login'))
    body = '''<h2>Register</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <input type="submit" value="Register">
    </form>'''
    return render_html('Register', body)

@app.route('/dash')
@login_required
def dash():
    logout_form = '<form method="post" action="/logout"><input type="submit" value="Logout"></form>'
    herbs = list(mongo.db.herbs.find({"user_id": ObjectId(current_user.id)}))
    body = '<h1>Your Herbs</h1><ul>'
    for herb in herbs:
        body += f'''
        <li>{herb['name']}: {herb['quantity']}
            <form method="post" action="/delete_herb/{herb['_id']}" style="display: inline;">
                <input type="submit" value="Delete">
            </form>
            <form action="/edit_herb/{herb['_id']}" style="display: inline;">
                <button>Edit</button>
            </form>
        </li>'''
    body += '</ul><h2>Add New Herb</h2>'
    body += '''<form method="POST" action="/add_herb">
            <input type="text" name="name" placeholder="Herb Name" required>
            <input type="text" name="quantity" placeholder="Quantity (e.g., 10g)" required>
            <input type="submit" value="Add Herb">
        </form>'''
    return render_html('Dashboard - MarySuite', body + logout_form)

@app.route('/add_herb', methods=['POST'])
@login_required
def add_herb():
    mongo.db.herbs.insert_one({
        "user_id": ObjectId(current_user.id),
        "name": request.form['name'],
        "quantity": request.form['quantity']
    })
    flash('Herb added successfully!')
    return redirect(url_for('dash'))

@app.route('/delete_herb/<herb_id>', methods=['POST'])
@login_required
def delete_herb(herb_id):
    mongo.db.herbs.delete_one({"_id": ObjectId(herb_id), "user_id": ObjectId(current_user.id)})
    flash('Herb deleted successfully!')
    return redirect(url_for('dash'))

@app.route('/edit_herb/<herb_id>', methods=['GET', 'POST'])
@login_required
def edit_herb(herb_id):
    herb = mongo.db.herbs.find_one({"_id": ObjectId(herb_id), "user_id": ObjectId(current_user.id)})
    if request.method == 'POST':
        mongo.db.herbs.update_one({"_id": ObjectId(herb_id)}, {"$set": {
            "name": request.form['name'],
            "quantity": request.form['quantity']
        }})
        flash('Herb updated successfully!')
        return redirect(url_for('dash'))
    body = f'''<h1>Edit Herb</h1>
    <form method="POST" action="/edit_herb/{herb_id}">
        <input type="text" name="name" value="{herb['name']}" required>
        <input type="text" name="quantity" value="{herb['quantity']}" required>
        <input type="submit" value="Update Herb">
    </form>'''
    return render_html('Edit Herb', body)
