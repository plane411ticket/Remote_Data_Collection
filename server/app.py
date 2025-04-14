from flask import Flask, render_template, request, redirect, url_for, flash, session
from .database import Database  # Use relative import
import hashlib
from functools import wraps
import os

app = Flask(__name__)
# Set a secret key directly to ensure sessions work properly
app.secret_key = os.environ.get('SECRET_KEY') or 'your-secret-key-goes-here'
db = Database()

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        user = db.authenticate_user(username, hashed_password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
            
        if db.check_user_exists(username):
            flash('Username already exists', 'danger')
            return render_template('register.html')
            
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user
        db.insert_users_info(username, hashed_password)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    # Get computer data for this user
    computer_data = db.get_computer_info_by_user(user_id)
    return render_template('dashboard.html', computer_data=computer_data)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
