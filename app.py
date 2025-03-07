from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
import bcrypt
from datetime import datetime, timezone
import re

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# MongoDB connection setup (replace with your MongoDB URI)
client = MongoClient('mongodb+srv://prakritisewa04:01012004@cluster0.ntnzg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
#client = MongoClient('mongodb://localhost:27017/')
db = client['SocialWorkerApp']  # Replace with your database name
users_collection = db['users']  # Replace with your collection name
media_collection = db['media']  # Define the media collection
store_collection = db['store']  # Define the store collection

@app.route('/', methods=['GET'])
def check_status():
    # Here, you can add any logic to check if the server is actually ready.
    # For example, check if necessary services or databases are connected.
    # In this case, we'll just return a simple "ready" message.
    return jsonify({"status": "ready", "message": "Server is up and running!"}), 200

@app.route('/get_latest_media', methods=['GET'])
def get_latest_media():
    try:
        # Query to get the latest 50 media items, sorted by timestamp in descending order
        latest_media = media_collection.find().sort('timestamp', DESCENDING).limit(50)
        
        # Create a list of media items with their URL and other details
        media_list = []
        for media in latest_media:
            user = users_collection.find_one({"userId": media['userId']})
            profile_photo = user.get('profPhoto', None)
            media_list.append({
                'url': media['url'],
                'mediaType': media['mediaType'],  # Can be 'video' or 'image'
                'username':user['username'],
                'userId': user['userId'],
                'profPhoto':  profile_photo,
                'likes_count': len(media["likes"]),
            })
        
        return jsonify({'media': media_list}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

# Check if username is available
@app.route('/check-username', methods=['POST'])
def check_username():
    data = request.get_json()
    username = data.get('username')

    user = users_collection.find_one({"username": username})
    if user:
        return jsonify({"available": False}), 200
    return jsonify({"available": True}), 200

# User registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    userId = data.get('userId')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    profPhoto = ""

    # Check if the username or email is already in use
    if users_collection.find_one({"username": username}):
        return jsonify({"error": "Username is already taken"}), 400
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email is already in use"}), 400

    # Hash the password before saving it
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create new user document
    user = {
        "userId": userId,
        "username": username,
        "email": email,
        "password": hashed_password,
        "profPhoto": profPhoto,
        "coins" : 0,
    }

    users_collection.insert_one(user)
    return jsonify({"message": "User registered successfully"}), 200

# Save media URL endpoint
@app.route('/save-media-url', methods=['POST'])
def save_media_url():
    data = request.get_json()
    url = data.get('url')
    user_id = data.get('userId')
    media_type = data.get('mediaType')

    if not url or not user_id or not media_type:
        return jsonify({"error": "Missing fields"}), 400

    # Create a document with the media URL
    media_data = {
        "url": url,
        "userId": user_id,
        "mediaType": media_type,
        "timestamp": datetime.now(tz=timezone.utc),
        "likes": [],
    }

    media_collection.insert_one(media_data)
    return jsonify({"message": "Media URL saved successfully"}), 200

# Get media URLs endpoint
@app.route('/get-media', methods=['GET'])
def get_media():
    user_id = request.args.get('userId')

    if not user_id:
        return jsonify({"error": "Missing userId parameter"}), 400

    # Query to get all media documents for the specified user
    media_data = list(media_collection.find({"userId": user_id}, {"_id": 0}))
    return jsonify({"media": media_data}), 200

#Get store data
@app.route('/get_store_data', methods=['GET'])
def get_store_data():
    try:
        # Fetch all documents from the store collection
        store_data = list(store_collection.find())  # Use .find() to get documents
        
        # Convert ObjectId to string for JSON serialization
        for item in store_data:
            item['_id'] = str(item['_id'])  # Convert ObjectId to string
            
        return jsonify({"store": store_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



#For Searching other users
@app.route('/search_users', methods=['GET'])
def search_users():
    query = request.args.get('query', '').strip()  # Get the query parameter

    if not query:  # Return an error if the query is empty
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        # Use a regex pattern to find usernames that match or contain the query
        regex_pattern = re.compile(query, re.IGNORECASE)  # Case-insensitive search

        # Query the database for usernames matching the regex
        matching_users = users_collection.find(
            {'username': regex_pattern},  # Assuming 'username' is the field name in your collection
            {'_id': 0, 'username': 1, 'profPhoto': 1, 'userId':1, 'email': 1}  # Select only the fields needed
        ).limit(6)  # Limit to top 6 results

        # Create a list to hold the matched user data
        user_list = []
        for user in matching_users:
            user_list.append(user)

        return jsonify({'users': user_list}), 200  # Return matched users
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Handle exceptions

@app.route('/users/update-profile', methods=['POST'])
def update_profile():
    try:
        # Parse JSON data from the request
        data = request.get_json()
        user_id = data.get('userId')
        username = data.get('username')
        profile_image_url = data.get('profPhoto')  # URL of the image (can be None)

        # Check if required fields are present
        if not user_id or not username:
            return jsonify({'message': 'User ID and Username are required'}), 400

        # Create the update object
        update_fields = {'username': username}

        # Only add profile image URL if it's provided
        if profile_image_url:
            update_fields['profPhoto'] = profile_image_url

        # Update the user document in MongoDB
        result = users_collection.update_one(
            {'userId': user_id},
            {'$set': update_fields}
        )

        if result.matched_count > 0:
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        # Log the error details
        print(f"Error occurred: {str(e)}")
        return jsonify({'message': 'An error occurred while updating the profile', 'error': str(e)}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = users_collection.find_one({'userId': user_id})
    profile_photo = user.get('profPhoto', None)
    if user:
        return jsonify({
            'userId': user['userId'],
            'username': user['username'],
            'email': user['email'],
            'profPhoto': profile_photo
        }), 200
    else:
        return jsonify({'error': 'User not found'}), 404
    
@app.route('/fetch_likes', methods=['GET'])
def get_likes_count():
    media_url = request.args.get('mediaUrl')
    if not media_url:
        return jsonify({"error": "Missing media URL"}), 400
    
    post = media_collection.find_one({"url": media_url})
    if not post:
        print("post not found")
        return jsonify({"error": "Post not found"}), 404

    return jsonify({"likes_count": len(post["likes"])}), 200

@app.route('/update_likes', methods=['POST'])
def update_likes():
    data = request.get_json()
    media_url = data.get("mediaUrl")
    user_id = data.get("userId")

    if not media_url or not user_id:
        return jsonify({"error": "Missing fields"}), 400

    post = media_collection.find_one({"url": media_url})
    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Add or remove like
    if user_id in post["likes"]:
        media_collection.update_one({"url": media_url}, {"$pull": {"likes": user_id}})
    else:
        media_collection.update_one({"url": media_url}, {"$addToSet": {"likes": user_id}})

    updated_post = media_collection.find_one({"url": media_url})
    return jsonify({"likes_count": len(updated_post["likes"])}), 200

@app.route('/fetch_coins', methods=['GET'])
def get_coins():
    userId = request.args.get('userId')
    if not userId:
        return jsonify({"error": "Missing userId"}), 400
    
    user = users_collection.find_one({"userId": userId})
    if not user:
        print("User not found")
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"coins": user["coins"]}), 200
           
if __name__ == '__main__':
    app.run(host='0.0.0.0',port = 8080)
