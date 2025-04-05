from flask import Flask, request, jsonify
import os
import cv2
import shutil
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import output
from werkzeug.utils import secure_filename
import tempfile

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

app = Flask(__name__)

# No need for UPLOAD_FOLDER since we'll use temp files
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Increase upload size limit (default is 16MB)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_frames_folder():
    frames_folder = "frames"
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)
    return frames_folder

def extract_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
    
    if duration < 5 or duration > 30:
        print("Video duration must be between 5 and 30 seconds.")
        cap.release()
        return []
    elif 5 <= duration < 10:
        frame_count = 2
    elif 10 <= duration < 15:
        frame_count = 3
    elif 15 <= duration < 20:
        frame_count = 5
    elif 20 <= duration <= 30:
        frame_count = 6
    
    frame_interval = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / frame_count), 1)
    
    frames_folder = create_frames_folder()
    frames = []
    count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if count % frame_interval == 0:
            image_path = os.path.join(frames_folder, f"frame_{count}.jpg")
            cv2.imwrite(image_path, frame)
            frames.append(image_path)
        
        count += 1
    
    cap.release()
    return frames

def get_frame_caption(image_path):
    model = genai.GenerativeModel("gemini-1.5-pro")
    image = Image.open(image_path)
    response = model.generate_content([image, "Describe the action in the image."], stream=False)
    
    if response and hasattr(response, "text"):
        return response.text.strip()
    
    return "No response from model."

def process_video(video_path):
    frames = extract_frames(video_path)
    if not frames:
        return "No frames extracted. Video might be too long or too short."
    
    captions = [get_frame_caption(frame) for frame in frames]
    
    summary_prompt = "Summarize this sequence of actions: " + " ".join(captions)
    model = genai.GenerativeModel("gemini-1.5-pro")
    summary_response = model.generate_content([summary_prompt], stream=False)
    
    if summary_response and hasattr(summary_response, "text"):
        summary_text = summary_response.text.strip()
    else:
        summary_text = "No summary generated."
    
    # Clean up frames folder
    if os.path.exists("frames"):
        shutil.rmtree("frames")
    
    return summary_text

@app.route('/process_video', methods=['POST'])
def upload_video():
    # Check if the post request has the file part
    if 'file' not in request.files:  # Changed from 'video' to 'file' (common Flutter convention)
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Create a temporary file
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            file.save(temp_video.name)
            
            summarized_caption = process_video(temp_video.name)
            extracted_keywords = output.extract_keywords(summarized_caption)
            
            # Clean up
            os.unlink(temp_video.name)
            
            return jsonify({
                "status": "success",
                "summarized_caption": summarized_caption,
                "extracted_keywords": extracted_keywords
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    else:
        return jsonify({
            "status": "error",
            "message": "File type not allowed"
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
