from flask import Flask, request, jsonify
import mysql.connector
import bcrypt

app = Flask(__name__)

# Database connection
db_connection = mysql.connector.connect(
    host="10.20.20.13",
    user="decameron_user",
    password="golqmhui",
    database="decameron_db"
)
cursor = db_connection.cursor()

# Sign Up
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    if cursor.fetchone():
        return jsonify({"message": "Username or email already exists"}), 409

    cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                   (username, email, hashed_password))
    db_connection.commit()
    return jsonify({"message": "User registered successfully!"}), 201

# Log In
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username_or_email, username_or_email))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):  # Password column index
        return jsonify({"message": "Login successful!"}), 200
    return jsonify({"message": "Invalid username/email or password"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
