from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
import mysql.connector
import bcrypt

app = Flask(__name__, static_folder=None)
socketio = SocketIO(app)

db_connection = mysql.connector.connect(
    host="10.20.20.13",
    user="golqm",
    password="golqmhui",
    database="decameron_db"
)

cursor = db_connection.cursor()

# User Signup Endpoint
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Hash the password for security
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Check if username or email already exists
    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    existing_user = cursor.fetchone()
    
    if existing_user:
        return jsonify({"message": "Username or email already exists"}), 409

    # Insert the new user
    cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                   (username, email, hashed_password))
    db_connection.commit()
    
    return jsonify({"message": "User registered successfully!"}), 201

# User Login Endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    # Retrieve user based on username or email
    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username_or_email, username_or_email))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Check if the password is correct
    stored_password = user[3]  
    if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"message": "Incorrect password"}), 401

# View Profile Endpoint
@app.route('/profile/<username>', methods=['GET'])
def view_profile(username):
    # Retrieve user details by username
    cursor.execute("SELECT username, email, region, favorite_game, description FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    user_data = {
        "username": user[0],
        "email": user[1],
        "region": user[2],
        "favorite_game": user[3],
        "description": user[4]
    }
    return jsonify(user_data), 200

# Update Profile Endpoint
@app.route('/profile/update', methods=['PUT'])
def update_profile():
    data = request.json
    username = data.get('username')  # Identifies which user to update
    region = data.get('region')
    favorite_game = data.get('favorite_game')
    description = data.get('description')

    # Update user details in the database
    cursor.execute("""
        UPDATE users
        SET region = %s, favorite_game = %s, description = %s
        WHERE username = %s
    """, (region, favorite_game, description, username))

    db_connection.commit()

    return jsonify({"message": "Profile updated successfully!"}), 200

# Create Post Endpoint
@app.route('/post/create', methods=['POST'])
def create_post():
    data = request.json
    username = data.get('username')  # User creating the post
    game = data.get('game')
    platform = data.get('platform')
    player_count = data.get('player_count')
    description = data.get('description')

    # Insert new post into the database
    cursor.execute("""
        INSERT INTO posts (username, game, platform, player_count, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (username, game, platform, player_count, description))
    db_connection.commit()

    return jsonify({"message": "Post created successfully!"}), 201

# View All Posts Endpoint
@app.route('/posts', methods=['GET'])
def view_posts():
    cursor.execute("SELECT id, username, game, platform, player_count, description FROM posts")
    posts = cursor.fetchall()

    posts_list = []
    for post in posts:
        post_data = {
            "id": post[0],
            "username": post[1],
            "game": post[2],
            "platform": post[3],
            "player_count": post[4],
            "description": post[5]
        }
        posts_list.append(post_data)

    return jsonify(posts_list), 200

# Request to Join Post Endpoint
@app.route('/post/join', methods=['POST'])
def request_join():
    data = request.json
    post_id = data.get('post_id')
    requester_username = data.get('requester_username')

    # Insert join request into the database
    cursor.execute("""
        INSERT INTO join_requests (post_id, requester_username)
        VALUES (%s, %s)
    """, (post_id, requester_username))
    db_connection.commit()

    return jsonify({"message": "Join request sent!"}), 201

# Manage Join Requests Endpoint
@app.route('/post/join/manage', methods=['PUT'])
def manage_join_requests():
    data = request.json
    post_id = data.get('post_id')
    requester_username = data.get('requester_username')
    action = data.get('action')  # Accept or Reject

    if action.lower() == 'accept':
        cursor.execute("""
            UPDATE join_requests
            SET status = 'accepted'
            WHERE post_id = %s AND requester_username = %s
        """, (post_id, requester_username))
        db_connection.commit()

        return jsonify({"message": "Join request accepted!"}), 200

    elif action.lower() == 'reject':
        cursor.execute("""
            UPDATE join_requests
            SET status = 'rejected'
            WHERE post_id = %s AND requester_username = %s
        """, (post_id, requester_username))
        db_connection.commit()

        return jsonify({"message": "Join request rejected!"}), 200

    else:
        return jsonify({"message": "Invalid action"}), 400

# Chat Room Handlers

# Join Chat Room
@socketio.on('join')
def handle_join(data):
    username = data['username']
    post_id = data['post_id']
    room = f"post_{post_id}"

    join_room(room)
    send(f"{username} has joined the chat", to=room)

# Leave Chat Room
@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    post_id = data['post_id']
    room = f"post_{post_id}"

    leave_room(room)
    send(f"{username} has left the chat", to=room)

# Handle Chat Messages
@socketio.on('message')
def handle_message(data):
    post_id = data['post_id']
    room = f"post_{post_id}"
    message = data['message']
    username = data['username']

    # Broadcast message to the room
    send({'username': username, 'message': message}, to=room)

# Admin: View All Users Endpoint
@app.route('/admin/users', methods=['GET'])
def view_users():
    cursor.execute("SELECT id, username, email, region, favorite_game, created_at FROM users")
    users = cursor.fetchall()

    users_list = []
    for user in users:
        user_data = {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "region": user[3],
            "favorite_game": user[4],
            "created_at": user[5]
        }
        users_list.append(user_data)

    return jsonify(users_list), 200

# Admin: View All Posts Endpoint
@app.route('/admin/posts', methods=['GET'])
def admin_view_posts():
    cursor.execute("SELECT id, username, game, platform, player_count, description FROM posts")
    posts = cursor.fetchall()

    posts_list = []
    for post in posts:
        post_data = {
            "id": post[0],
            "username": post[1],
            "game": post[2],
            "platform": post[3],
            "player_count": post[4],
            "description": post[5]
        }
        posts_list.append(post_data)

    return jsonify(posts_list), 200

# Admin: Delete Post Endpoint
@app.route('/admin/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    # Delete the specified post
    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    db_connection.commit()

    return jsonify({"message": "Post deleted successfully!"}), 200

# Admin: Maintenance Mode Endpoint
@app.route('/admin/maintenance', methods=['POST'])
def maintenance_mode():
    data = request.json
    status = data.get('status')  # Expected values: "on" or "off"

    if status.lower() == 'on':
        return jsonify({"message": "The application is now in maintenance mode"}), 200
    elif status.lower() == 'off':
        return jsonify({"message": "The application is back online"}), 200
    else:
        return jsonify({"message": "Invalid status value"}), 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
