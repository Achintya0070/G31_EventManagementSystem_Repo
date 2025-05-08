from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_restful import Api, Resource, reqparse
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, DateTimeField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

api = Api(app)

# ----------------------------- Forms -----------------------------
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])

class EventBookingForm(FlaskForm):
    notes = TextAreaField('Notes')

class ReviewForm(FlaskForm):
    content = TextAreaField('Review', validators=[DataRequired()])
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])

# ----------------------------- Models -----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    bookings = db.relationship('Booking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    queries = db.relationship('Query', backref='user', lazy=True)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    capacity = db.Column(db.Integer, default=100)
    available_seats = db.Column(db.Integer)
    price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='event', lazy=True)
    reviews = db.relationship('Review', backref='event', lazy=True)

    def __init__(self, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        self.available_seats = self.capacity

    def book_seat(self):
        if self.available_seats > 0:
            self.available_seats -= 1
            return True
        return False

    def cancel_booking(self):
        if self.available_seats < self.capacity:
            self.available_seats += 1
            return True
        return False

    def get_average_rating(self):
        if not self.reviews:
            return 0
        return sum(review.rating for review in self.reviews) / len(self.reviews)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled, completed

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def validate_rating(self):
        return 1 <= self.rating <= 5

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=True)

# --------------------------- Login ----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------- Web Routes ----------------------------
@app.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if user with email already exists
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            flash('Email address already registered. Please use a different email.', 'error')
            return render_template('register.html')
            
        try:
            user = User(username=request.form['username'], email=request.form['email'])
            user.set_password(request.form['password'])
            db.session.add(user)
            db.session.commit()
            flash('Registered successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    # Get user's bookings
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    booked_events = [booking.event for booking in user_bookings]
    
    # Get user's reviews
    user_reviews = Review.query.filter_by(user_id=current_user.id).all()
    
    return render_template('profile.html', bookings=booked_events, reviews=user_reviews)

@app.route('/event/<int:event_id>/book', methods=['POST'])
@login_required
def book_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user has already booked this event
    existing_booking = Booking.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing_booking:
        flash('You have already booked this event!', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))
    
    # Check if seats are available
    if not event.book_seat():
        flash('No seats available for this event!', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))
    
    # Create new booking
    booking = Booking(user_id=current_user.id, event_id=event_id)
    db.session.add(booking)
    db.session.commit()
    
    flash('Event booked successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    reviews = Review.query.filter_by(event_id=event_id).all()
    return render_template('event_detail.html', event=event, reviews=reviews)

@app.route('/event/<int:event_id>/review', methods=['POST'])
@login_required
def submit_review(event_id):
    event = Event.query.get_or_404(event_id)
    content = request.form['content']
    rating = int(request.form['rating'])
    
    # Check if user has already reviewed this event
    existing_review = Review.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing_review:
        flash('You have already reviewed this event!', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))
    
    review = Review(user_id=current_user.id, event_id=event_id, content=content, rating=rating)
    db.session.add(review)
    db.session.commit()
    
    flash('Review submitted successfully!', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    events = Event.query.all()
    bookings = Booking.query.all()
    reviews = Review.query.all()
    queries = Query.query.all()
    return render_template('admin_dashboard.html', events=events, bookings=bookings, reviews=reviews, queries=queries)

@app.route('/event/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        event = Event(
            name=request.form['name'],
            description=request.form['description'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M'),
            location=request.form['location'],
            capacity=int(request.form['capacity']),
            price=float(request.form['price'])
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_event.html')

@app.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/booking/<int:booking_id>/update', methods=['POST'])
@login_required
def update_booking_status(booking_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status in ['confirmed', 'cancelled', 'completed']:
        # Update event available seats
        if new_status == 'cancelled' and booking.status == 'confirmed':
            booking.event.cancel_booking()
        elif new_status == 'confirmed' and booking.status == 'cancelled':
            if not booking.event.book_seat():
                return jsonify({'success': False, 'message': 'No available seats'})
        
        booking.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid status'})

@app.route('/query/<int:query_id>/respond', methods=['POST'])
@login_required
def respond_to_query(query_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    query = Query.query.get_or_404(query_id)
    data = request.get_json()
    response = data.get('response')
    
    if response:
        query.response = response
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Response is required'})

# --------------------------- API Routes ----------------------------

event_parser = reqparse.RequestParser()
event_parser.add_argument('name', required=True)
event_parser.add_argument('description', required=True)
event_parser.add_argument('date', required=True)

review_parser = reqparse.RequestParser()
review_parser.add_argument('event_id', type=int, required=True)
review_parser.add_argument('content', required=True)
review_parser.add_argument('rating', type=int, required=True)

query_parser = reqparse.RequestParser()
query_parser.add_argument('content', required=True)

class EventListAPI(Resource):
    def get(self):
        events = Event.query.all()
        return jsonify([{
            'id': e.id,
            'name': e.name,
            'title': e.name,  # Adding title field for Django frontend compatibility
            'description': e.description,
            'date': e.date.strftime('%Y-%m-%d %H:%M'),
            'location': e.location,
            'capacity': e.capacity,
            'available_seats': e.available_seats,
            'price': e.price,
            'created_at': e.created_at.strftime('%Y-%m-%d %H:%M') if e.created_at else None
        } for e in events])

class EventDetailAPI(Resource):
    def get(self, event_id):
        event = Event.query.get_or_404(event_id)
        return {
            'id': event.id,
            'name': event.name,
            'description': event.description,
            'date': event.date.strftime('%Y-%m-%d %H:%M')
        }

class ReviewAPI(Resource):
    @login_required
    def post(self):
        args = review_parser.parse_args()
        review = Review(
            user_id=current_user.id,
            event_id=args['event_id'],
            content=args['content'],
            rating=args['rating']
        )
        db.session.add(review)
        db.session.commit()
        return {'message': 'Review submitted'}, 201

class QueryListAPI(Resource):
    @login_required
    def get(self):
        queries = Query.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': q.id,
            'content': q.content,
            'response': q.response
        } for q in queries])

    @login_required
    def post(self):
        args = query_parser.parse_args()
        q = Query(user_id=current_user.id, content=args['content'])
        db.session.add(q)
        db.session.commit()
        return {'message': 'Query submitted'}, 201

# Register API endpoints
api.add_resource(EventListAPI, '/api/events')
api.add_resource(EventDetailAPI, '/api/events/<int:event_id>')
api.add_resource(ReviewAPI, '/api/reviews')
api.add_resource(QueryListAPI, '/api/queries')

# --------------------------- Bootstrap ----------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@example.com', is_admin=True)
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created!")
    app.run(debug=True)
