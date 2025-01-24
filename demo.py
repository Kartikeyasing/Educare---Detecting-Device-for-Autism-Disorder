import os
import sys
import warnings
import argparse
import logging
import numpy as np
import pandas as pd
import subprocess
import torch
import torchaudio
from transformers import BertTokenizerFast, BertForTokenClassification, Wav2Vec2FeatureExtractor
import whisper_timestamped as whisper

from models import AcousticModel, MultimodalModel

warnings.filterwarnings("ignore")

# Define labels for the token classification
labels = ['FP', 'RP', 'RV', 'RS', 'PW']

def run_asr(audio_file, device):
    audio, orgnl_sr = torchaudio.load(audio_file)
    audio_rs = torchaudio.functional.resample(audio, orgnl_sr, 16000)[0, :].to(device)

    model = whisper.load_model('demo_models/asr', device=device)
    print('Loaded finetuned Whisper ASR model.')

    result = whisper.transcribe(model, audio_rs, language='en', beam_size=5, temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0))

    words = []
    for segment in result['segments']:
        words += segment['words']
    
    text_df = pd.DataFrame(words)
    text_df['text'] = text_df['text'].str.lower()

    return text_df

def run_language_based(audio_file, text_df, device):
    # Tokenize the text
    text = ' '.join(text_df['text'])
    tokenizer = BertTokenizerFast.from_pretrained('bert-base-uncased')
    tokens = tokenizer(text, return_tensors="pt").to(device)

    # Initialize Bert model and load in pre-trained weights
    model = BertForTokenClassification.from_pretrained('bert-base-uncased', num_labels=len(labels))
    try:
        model.load_state_dict(torch.load('demo_models/language.pt', map_location='cpu'), strict=False)
    except RuntimeError as e:
        print(f"Error loading model weights: {e}")

    print('Loaded finetuned language model') 

    model.config.output_hidden_states = True
    model.to(device)

    # Get Bert output at the word-level
    output = model(input_ids=tokens['input_ids'])
    probs = torch.sigmoid(output.logits)
    preds = (probs > 0.5).int()[0][1:-1]
    emb = output.hidden_states[-1][0][1:-1]

    # Convert Bert word-level output to a dataframe with word timestamps
    pred_columns = [f"pred{i}" for i in range(preds.shape[1])]
    pred_df = pd.DataFrame(preds.cpu(), columns=pred_columns)
    emb_columns = [f"emb{i}" for i in range(emb.shape[1])]
    emb_df = pd.DataFrame(emb.detach().cpu(), columns=emb_columns)
    df = pd.concat([text_df, pred_df, emb_df], axis=1)

    # Convert dataframe to frame-level output
    frame_emb, frame_pred = convert_word_to_framelevel(audio_file, df)

    return frame_emb, frame_pred

def convert_word_to_framelevel(audio_file, df):
    df['end'] = df['end'] + 0.01
    info = torchaudio.info(audio_file)
    end = info.num_frames / info.sample_rate

    frame_time = np.arange(0, end, 0.01).tolist()
    num_labels = len(labels)
    frame_pred = [[0] * num_labels for _ in range(len(frame_time))]
    frame_emb = [[0] * 768 for _ in range(len(frame_time))]

    for idx, row in df.iterrows():
        start_idx = round(row['start'] * 100)
        end_idx = min(round(row['end'] * 100), len(frame_time))
        frame_pred[start_idx:end_idx] = [[row[f'pred{i}'] for i in range(num_labels)]] * (end_idx - start_idx)
        frame_emb[start_idx:end_idx] = [[row[f'emb{i}'] for i in range(768)]] * (end_idx - start_idx)

    frame_emb = torch.Tensor(np.array(frame_emb)[::2])
    frame_pred = torch.Tensor(np.array(frame_pred)[::2])

    return frame_emb, frame_pred

def run_acoustic_based(audio_file, device):
    audio, orgnl_sr = torchaudio.load(audio_file)
    audio_rs = torchaudio.functional.resample(audio, orgnl_sr, 16000)[0, :].to(device)

    feature_extractor = Wav2Vec2FeatureExtractor(sampling_rate=16000, do_normalize=True)
    audio_feats = feature_extractor(audio_rs, sampling_rate=16000).input_values[0]
    audio_feats = torch.Tensor(audio_feats).unsqueeze(0).to(device)

    model = AcousticModel()
    model.load_state_dict(torch.load('demo_models/acoustic.pt', map_location='cpu'))
    model.to(device)
    print('Loaded finetuned acoustic model.')

    emb, output = model(audio_feats)
    probs = torch.sigmoid(output)
    preds = (probs > 0.5).int()[0]

    return emb, preds

def run_multimodal(language, acoustic, device):
    min_size = min(language.size(0), acoustic.size(0))
    language = language[:min_size].unsqueeze(0).to(device)
    acoustic = acoustic[:min_size].unsqueeze(0).to(device)

    model = MultimodalModel()
    model.load_state_dict(torch.load('demo_models/multimodal.pt', map_location='cpu'))
    model.to(device)
    print('Loaded finetuned multimodal model.')

    output = model(language, acoustic)
    probs = torch.sigmoid(output)
    preds = (probs > 0.5).int()[0]

    return preds

def setup_log(log_file):
    logger = logging.getLogger("demo_log")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file)
    stream_handler = logging.StreamHandler(sys.stdout)

    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    stream_handler.setFormatter(log_format)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    sys.stdout = logger
    sys.stderr = logger

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio_file', type=str, required=True, help='path to 8k .wav file')
    parser.add_argument('--output_trans', type=str, required=False, help='path to intermediate .csv with ASR transcript')
    parser.add_argument('--output_file', type=str, required=True, help='path to output .csv')
    parser.add_argument('--device', type=str, default='cpu', help='cpu or cuda')
    parser.add_argument('--modality', type=str, default='multimodal', choices=['language', 'acoustic', 'multimodal'], help='modality can be language, acoustic, or multimodal')

    args = parser.parse_args()

    # Setup log
    # setup_log(args.output_file.replace('.csv', '.log'))

    text_df = None
    if args.modality in ['language', 'multimodal']:
        text_df = run_asr(args.audio_file, args.device)
        if args.output_trans:
            text_df.to_csv(args.output_trans)
        language_emb, preds = run_language_based(args.audio_file, text_df, args.device)

    if args.modality in ['acoustic', 'multimodal']:
        acoustic_emb, preds = run_acoustic_based(args.audio_file, args.device)

    if args.modality == 'multimodal':
        preds = run_multimodal(language_emb, acoustic_emb, args.device)

    # Save output
    pred_df = pd.DataFrame(preds.cpu(), columns=labels).astype(int)
    pred_df['frame_time'] = [round(i * 0.02, 2) for i in range(pred_df.shape[0])]
    pred_df.set_index('frame_time', inplace=True)
    pred_df.to_csv(args.output_file)

    # Run final.py after processing
    subprocess.run([sys.executable, 'final.py'])
