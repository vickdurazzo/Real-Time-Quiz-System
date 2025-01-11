# Authentication routes (login, register, logout)
from flask import Blueprint, request, session, jsonify,redirect,url_for,render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User,db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            
            username = data.get('username')
            password = data.get('password')

            user = User.query.filter_by(nm_user=username).first()
            
            if user and check_password_hash(user.des_user_passwd, password):
                session['user_id'] = user.user_id
                
                if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
                    return jsonify({"message": "Login successfully","user_id":session['user_id']}), 200
                
                return redirect(url_for('home.home'))
            else:
                return jsonify({"message": "Invalid credentials"}), 401
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"message": "Request must be JSON"}), 415

            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            print(username)
            print(password)
            new_user = User(nm_user=username, des_user_passwd=hashed_password)
            db.session.add(new_user)
            # Debugging: Print the new user object
            print(f"New User: {new_user}")
            db.session.commit()
            # Debugging: Print the new user object
            print(f"New User: {new_user}")

            return jsonify({"message": "User registered successfully!"}), 200
        except Exception as e:
            db.session.rollback()
            # Debugging: Print the exception message
            print(f"Exception occurred: {str(e)}")
            return jsonify({"message": f"Error: {str(e)}"}), 500

    return render_template('register.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "User logout successfully!"}), 200
