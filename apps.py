import os
import subprocess
from flask import Flask, render_template, request, jsonify
from pydub import AudioSegment

app = Flask(__name__)

MAIN_FOLDER = '.'  # Main folder where 'demo.py' and 'output.txt' are located
AUDIO_FILE = 'input.wav'  # Static filename for output WAV file
TEMP_MP3_FILE = 'input.mp3'  # Temporary filename for the uploaded MP3 file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        return jsonify({'error': 'No audio file found'}), 400

    try:
        # Save the uploaded audio file in the main folder as 'input.mp3'
        audio_file = request.files['audio_data']
        mp3_path = os.path.join(MAIN_FOLDER, TEMP_MP3_FILE)
        audio_file.save(mp3_path)

        # Convert the MP3 file to WAV using FFmpeg
        wav_path = os.path.join(MAIN_FOLDER, AUDIO_FILE)
        conversion_result = subprocess.call(['ffmpeg', '-i', mp3_path, wav_path])

        if conversion_result != 0:
            return jsonify({'error': 'Error converting MP3 to WAV'}), 500

        # Convert the audio file to mono
        sound = AudioSegment.from_wav(wav_path)
        mono_sound = sound.set_channels(1)
        mono_sound.export(wav_path, format='wav')  # Overwrite the original WAV file

        # Prepare command to execute demo.py
        command = [
            'python', 'demo.py',
            '--audio_file', AUDIO_FILE,
            '--output_file', 'pred.csv',
            '--output_trans', 'trans.csv',
            '--modality', 'language'
        ]

        # Run the command in the main folder where demo.py is located
        result = subprocess.run(command, cwd=MAIN_FOLDER, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({'error': 'Error executing demo.py', 'details': result.stderr}), 500

        # Fetch the output from 'output.txt' after processing
        output_file_path = os.path.join(MAIN_FOLDER, 'output.txt')
        if os.path.exists(output_file_path):
            with open(output_file_path, 'r') as file:
                output_content = file.read()
        else:
            output_content = "No output found."

        # Clean up temporary MP3 file
        os.remove(mp3_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Return command and output
    return jsonify({
        'command': ' '.join(command),
        'output': output_content,
        'execution_details': result.stdout
    })

if __name__ == '__main__':
    app.run(debug=True)
