from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import os

# here we create code for room check

# ----------------------------------------
# Flask App Configuration
# ----------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------------------------------
# Initialize Extensions
# ----------------------------------------
db = SQLAlchemy(app)
socketio = SocketIO(app)

# ----------------------------------------
# Cloudinary Configuration
# ----------------------------------------
cloudinary.config(
    cloud_name="apna-ghar",           # ✅ Cloud name (replace with your own)
    api_key="238676337565917",        # ✅ Your API key
    api_secret="InvdU50MQOuMxQsfNEYAxR60FyQ",  # ✅ Your API secret
    secure = True
)

# ----------------------------------------
# Database Models
# ----------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    rent = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, default=True)
    room_image = db.Column(db.String(200))
    washroom_image = db.Column(db.String(200))

# ----------------------------------------
# Routes
# ----------------------------------------
@app.route('/')
def home():
    rooms = Room.query.filter_by(available=True).all()
    return render_template('home.html', rooms=rooms)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return redirect(url_for('register'))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials!')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out!')
    return redirect(url_for('home'))

@app.route('/add_room', methods=['GET', 'POST'])
def add_room():
    if 'user_id' not in session:
        flash('Please log in to add a room.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        city = request.form['city']
        area = request.form['area']
        rent = request.form['rent']
        room_image = request.files['room_image']
        washroom_image = request.files['washroom_image']

        # Upload images to Cloudinary
        room_upload = cloudinary.uploader.upload(room_image)
        washroom_upload = cloudinary.uploader.upload(washroom_image)

        new_room = Room(
            owner_id=session['user_id'],
            city=city,
            area=area,
            rent=rent,
            room_image=room_upload['secure_url'],
            washroom_image=washroom_upload['secure_url']
        )

        db.session.add(new_room)
        db.session.commit()
        flash('Room added successfully!')
        return redirect(url_for('home'))

    return render_template('add_room.html')

# ----------------------------------------
# Create Database if Missing
# ----------------------------------------
with app.app_context():
    db.create_all()

# ----------------------------------------
# Run App
# ----------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures the database and tables are created on Render too
    socketio.run(app, debug=True)

