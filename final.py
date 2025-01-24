import pandas as pd
import os

def combine_csv(trans_csv, pred_csv, output_txt):
    # Load the CSV files
    trans_df = pd.read_csv(trans_csv)
    pred_df = pd.read_csv(pred_csv)

    # Initialize a list to store the final output
    output_data = []

    # Define a mapping of tags to their meanings
    tag_meanings = {
        'FP': 'Filled Pauses',
        'PW': 'Partial Words',
        'RP': 'Repetitions',
        'RV': 'Revisions',
        'RS': 'Restarts'
    }

    # Iterate through each word in the trans_df
    for _, row in trans_df.iterrows():
        word = row['text']  # Assuming 'text' is the column with the word
        start_time = row['start']  # Start time of the word
        end_time = row['end']  # End time of the word

        # Get the corresponding frames from pred_df
        frame_mask = (pred_df['frame_time'] >= start_time) & (pred_df['frame_time'] < end_time)
        relevant_frames = pred_df[frame_mask]

        if not relevant_frames.empty:
            # Calculate the average tag for this word
            avg_tags = relevant_frames[['FP', 'RP', 'RV', 'RS', 'PW']].mean().astype(int).to_dict()  # Convert to dict
            
            # Find the tags with value of 1
            tagged_columns = [tag for tag, value in avg_tags.items() if value == 1]
            
            if tagged_columns:
                # Append the word and its corresponding tags with meanings to the output data
                tags_with_meanings = [f"{tag} - {tag_meanings[tag]}" for tag in tagged_columns]
                output_data.append(f"{word} -> {', '.join(tags_with_meanings)}")
            else:
                # Append the word with "OK" if no tags are found
                output_data.append(f"{word} -> OK")
        else:
            # Append the word with "OK" if no relevant frames
            output_data.append(f"{word} -> OK")

    # Save to output.txt
    with open(output_txt, 'w') as f:
        for line in output_data:
            f.write(f"{line}\n")

    # Delete the input files
    try:
        os.remove('input.mp3')
        os.remove('input.wav')
        print("Input files deleted successfully.")
    except FileNotFoundError:
        print("One or both input files not found.")
    except Exception as e:
        print(f"An error occurred while deleting input files: {e}")

if __name__ == '__main__':
    combine_csv('trans.csv', 'pred.csv', 'output.txt')
