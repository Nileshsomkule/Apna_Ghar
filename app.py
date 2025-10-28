from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'room_finder_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///roomfinder.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*')

# =====================
# MODELS
# =====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student / owner

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    city = db.Column(db.String(100))
    area = db.Column(db.String(100))
    rent = db.Column(db.Float)
    available = db.Column(db.Boolean, default=True)
    room_image = db.Column(db.String(200))
    washroom_image = db.Column(db.String(200))

# =====================
# ROUTES
# =====================
@app.route('/')
def home():
    rooms = Room.query.filter_by(available=True).all()
    return render_template('index.html', rooms=rooms)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
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
            session['role'] = user.role
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('home'))

# =====================
# OWNER - ADD ROOM
# =====================
@app.route('/add_room', methods=['GET', 'POST'])
def add_room():
    if 'user_id' not in session or session['role'] != 'owner':
        flash('Only owners can add rooms.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        city = request.form['city']
        area = request.form['area']
        rent = request.form['rent']
        available = True if request.form.get('available') else False

        room_img = request.files['room_image']
        wash_img = request.files['washroom_image']

        room_filename = secure_filename(room_img.filename)
        wash_filename = secure_filename(wash_img.filename)

        room_img.save(os.path.join(app.config['UPLOAD_FOLDER'], room_filename))
        wash_img.save(os.path.join(app.config['UPLOAD_FOLDER'], wash_filename))

        new_room = Room(
            owner_id=session['user_id'],
            city=city,
            area=area,
            rent=rent,
            available=available,
            room_image=room_filename,
            washroom_image=wash_filename
        )
        db.session.add(new_room)
        db.session.commit()
        socketio.emit('room_update', {'msg': 'New room added!'}, broadcast=True)
        flash('Room added successfully!')
        return redirect(url_for('home'))

    return render_template('add_room.html')

# =====================
# EDIT ROOM
# =====================
@app.route('/edit_room/<int:id>', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.get_or_404(id)
    if 'user_id' not in session or session['role'] != 'owner' or room.owner_id != session['user_id']:
        flash('Unauthorized access!')
        return redirect(url_for('home'))

    if request.method == 'POST':
        room.city = request.form['city']
        room.area = request.form['area']
        room.rent = request.form['rent']
        room.available = True if request.form.get('available') else False
        db.session.commit()
        flash('Room updated successfully!')
        return redirect(url_for('home'))

    return render_template('edit_room.html', room=room)

# =====================
# DELETE ROOM
# =====================
@app.route('/delete_room/<int:id>')
def delete_room(id):
    room = Room.query.get_or_404(id)
    if 'user_id' not in session or session['role'] != 'owner' or room.owner_id != session['user_id']:
        flash('Unauthorized access!')
        return redirect(url_for('home'))

    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully!')
    return redirect(url_for('home'))

# =====================
# SEARCH
# =====================
@app.route('/search')
def search():
    city = request.args.get('city')
    area = request.args.get('area')
    rooms = Room.query
    if city:
        rooms = rooms.filter(Room.city.ilike(f'%{city}%'))
    if area:
        rooms = rooms.filter(Room.area.ilike(f'%{area}%'))
    rooms = rooms.filter_by(available=True).all()
    return render_template('index.html', rooms=rooms)

# =====================
# MAIN
# =====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
