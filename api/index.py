from flask import Flask, request, redirect, url_for, flash, render_template_string
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    u = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return User(u['_id']) if u else None

class User(UserMixin):
    def __init__(self, user_id):
        self.id = str(user_id)

@app.route('/')
def home():
    home_template = """
    <!DOCTYPE html>
    <html>
    <head><title>Home - MarySuite</title></head>
    <body>
    <h1>MarySuite - Your Herb Tracker</h1>
    <a href="/login">Login</a> | <a href="/register">Register</a>
    </body>
    </html>
    """
    return home_template

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            users.insert_one({'name': request.form['username'], 'password': hashpass})
            flash('Registration successful!')
            return redirect(url_for('login'))
        flash('Username already exists.')

    register_template = """
    <!DOCTYPE html>
    <html>
    <head><title>Register</title></head>
    <body>
    <h2>Register</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <input type="submit" value="Register">
    </form>
    </body>
    </html>
    """
    return register_template

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = mongo.db.users.find_one({'name': request.form['username']})
        if user and bcrypt.check_password_hash(user['password'], request.form['password']):
            user_obj = User(user['_id'])
            login_user(user_obj)
            flash('Logged in successfully!')
            return redirect(url_for('dash'))
        flash('Invalid username/password combination')
    return """
    <!DOCTYPE html>
    <html><head><title>Login</title></head><body>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <input type="submit" value="Login">
    </form></body></html>
    """

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/secret')
@login_required
def secret():
    return 'Only authenticated users can see this!'

@app.route('/dash')
@login_required
def dash():
    user_id = current_user.id
    user_herbs = mongo.db.herbs.find({"user_id": ObjectId(user_id)})
    herbs = list(user_herbs)

    if not herbs:
        default_herbs = [
            {"user_id": ObjectId(user_id), "name": "Mint", "quantity": "10g"},
            {"user_id": ObjectId(user_id), "name": "Basil", "quantity": "5g"}
        ]
        mongo.db.herbs.insert_many(default_herbs)
        herbs = default_herbs
    
    herbs_list_html = ''.join([f"<li>{herb['name']}: {herb['quantity']}</li>" for herb in herbs])
  
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard - MarySuite</title></head>
    <body>
        <h1>Your Herbs</h1>
        <ul>
            {% for herb in herbs %}
            <li>{{ herb.name }}: {{ herb.quantity }}
                <form method="POST" action="/delete_herb/{{ herb._id }}">
                    <button type="submit">Delete</button>
                </form>
                <form method="GET" action="/edit_herb/{{ herb._id }}">
                    <button type="submit">Edit</button>
                </form>
            </li>
            {% endfor %}
        </ul>
        <h2>Add New Herb</h2>
        <form method="POST" action="/add_herb">
            <input type="text" name="name" placeholder="Herb Name" required>
            <input type="text" name="quantity" placeholder="Quantity (e.g., 10g)" pattern=".*g$" title="Quantity should end with a 'g' for grams." required>
            <input type="submit" value="Add Herb">
        </form>
        <form method="POST" action="/logout">
            <button type="submit">Logout</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(dashboard_html, herbs=herbs)

@app.route('/add_herb', methods=['POST'])
@login_required
def add_herb():
    quantity = request.form['quantity']
    if not quantity.lower().endswith('g'):
        quantity += 'g'

    herb = {
        "user_id": ObjectId(current_user.id),
        "name": request.form['name'],
        "quantity": quantity
    }
    mongo.db.herbs.insert_one(herb)
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
    herb_to_edit = mongo.db.herbs.find_one({"_id": ObjectId(herb_id), "user_id": ObjectId(current_user.id)})
    if not herb_to_edit:
        flash('Herb not found.')
        return redirect(url_for('dash'))

    if request.method == 'POST':
        new_name = request.form.get('name', herb_to_edit['name'])
        new_quantity = request.form.get('quantity', herb_to_edit['quantity'])
        if not new_quantity.lower().endswith('g'):
            new_quantity += 'g'
        mongo.db.herbs.update_one(
            {"_id": ObjectId(herb_id), "user_id": ObjectId(current_user.id)},
            {"$set": {"name": new_name, "quantity": new_quantity}}
        )
        flash('Herb updated successfully!')
        return redirect(url_for('dash'))

    edit_form_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Edit Herb</title></head>
    <body>
        <h1>Edit Herb</h1>
        <form method="POST" action="/edit_herb/{herb_id}">
            <label for="name">Herb Name:</label>
            <input type="text" id="name" name="name" value="{herb_to_edit['name']}" required>
            <label for="quantity">Quantity:</label>
            <input type="text" id="quantity" name="quantity" value="{herb_to_edit['quantity']}" required>
            <input type="submit" value="Update Herb">
        </form>
        <a href="/dash">Back to Dashboard</a>
    </body>
    </html>
    """
    return render_template_string(edit_form_html)
