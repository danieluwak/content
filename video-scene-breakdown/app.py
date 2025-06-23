from flask import Flask, request, jsonify
import os
import scenedetect
from scenedetect import detect
from scenedetect.detectors import ContentDetector  # Changed import
import cv2
import google.generativeai as genai
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Gemini API
GOOGLE_API_KEY = "AIzaSyABcfs_DTPsRg-QZrALUmowd0kshRSyMwM"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

def detect_scenes(video_path):
    scene_list = detect(video_path, ContentDetector())  # Changed detector
    return scene_list

def transcribe_scene(video_path, start_time, end_time):
    # Extract audio from the scene
    temp_audio_file = "temp_audio.wav"
    command = f"ffmpeg -ss {start_time} -to {end_time} -i {video_path} -vn -acodec pcm_s16le -ac 1 -ar 16000 {temp_audio_file}"
    os.system(command)

    # Transcribe the audio using Gemini
    try:
        with open(temp_audio_file, "rb") as audio_file:
            contents = audio_file.read()
        prompt = "Transcribe the following audio exactly as it is spoken, without adding any suggestions, interpretations, or corrections. Only provide the exact words spoken in the audio.\n\nAudio: "
        response = model.generate_content([prompt, {"mime_type": "audio/wav", "data": contents}])
        transcription = response.text
    except Exception as e:
        transcription = f"Transcription failed: {str(e)}"

    # Clean up the temporary audio file
    os.remove(temp_audio_file)

    return transcription

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']

    if video.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    filename = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
    video.save(filename)

    # Perform scene detection
    scene_list = detect_scenes(filename)

    # Convert scene list to timestamps and transcribe each scene
    scene_data = []
    for i, scene in enumerate(scene_list):
        start_time = str(scene[0])
        end_time = str(scene[1])
        transcription = transcribe_scene(filename, start_time, end_time)
        scene_data.append({
            'scene_number': i + 1,
            'start_time': start_time,
            'end_time': end_time,
            'transcription': transcription
        })

    return jsonify({'message': 'Video uploaded and processed successfully', 'filename': filename, 'scenes': scene_data}), 200

@app.route('/')
def index():
    return "Welcome to the Video Scene Breakdown App!"

if __name__ == '__main__':
    app.run(debug=True)