# auth.py
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User

auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                user = User.query.filter_by(nm_user=username).first()
                if user and check_password_hash(user.des_user_passwd, password):
                    session['user_id'] = user.user_id
                    print(session['user_id'])
                    return jsonify({"message": "Login successful!"}), 200
                else:
                    return jsonify({"message": "Invalid credentials"}), 401
            else:
                return jsonify({"message": "Request must be JSON"}), 415
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print(data)
            username = data.get('username')
            password = data.get('password')
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            print(hashed_password)
            try:
                new_user = User(
                    nm_user=username,
                    des_user_passwd=hashed_password
                )
                db.session.add(new_user)
                db.session.commit()
                return jsonify({"message": "User registered successfully!"}), 200
            except Exception as e:
                db.session.rollback()
                print(f"Error: {str(e)}")
                return jsonify({"message": f"Error: {str(e)}"}), 500
    
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])  # Convert to dict and return as JSON
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@auth_bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')