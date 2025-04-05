import os
import cv2
import shutil
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Constants
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_frames_folder():
    """Create a directory to store extracted frames."""
    frames_folder = "frames"
    if not os.path.exists(frames_folder):
        os.makedirs(frames_folder)
    return frames_folder

def extract_frames(video_path):
    """
    Extract key frames from a video based on duration.
    Returns:
        List of paths to extracted frame images.
    """
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
    
    # Validate video duration
    if duration < 5 or duration > 30:
        print("Video duration must be between 5 and 30 seconds.")
        cap.release()
        return []
    
    # Determine number of frames to extract based on duration
    if 5 <= duration < 10:
        frame_count = 2
    elif 10 <= duration < 15:
        frame_count = 3
    elif 15 <= duration < 20:
        frame_count = 5
    elif 20 <= duration <= 30:
        frame_count = 6
    
    frame_interval = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / frame_count), 1)
    
    # Extract frames
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
    """Generate a caption for a single frame using Gemini."""
    model = genai.GenerativeModel("gemini-1.5-pro")
    image = Image.open(image_path)
    response = model.generate_content([image, "Describe the action in the image."], stream=False)
    
    return response.text.strip() if response and hasattr(response, "text") else "No response from model."

def process_video(video_path):
    """
    Process a video file to generate a summary of actions.
    Steps:
        1. Extract key frames
        2. Generate captions for each frame
        3. Summarize the sequence of actions
    """
    frames = extract_frames(video_path)
    if not frames:
        return "No frames extracted. Video might be too long or too short."
    
    # Generate captions for each frame
    captions = [get_frame_caption(frame) for frame in frames]
    
    # Summarize the sequence
    summary_prompt = "Summarize this sequence of actions: " + " ".join(captions)
    model = genai.GenerativeModel("gemini-1.5-pro")
    summary_response = model.generate_content([summary_prompt], stream=False)
    
    summary_text = summary_response.text.strip() if summary_response and hasattr(summary_response, "text") else "No summary generated."
    
    # Cleanup
    if os.path.exists("frames"):
        shutil.rmtree("frames")
    
    return summary_text
