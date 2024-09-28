import pandas as pd
import os

from app.helpers import file_valid
from config import LATEST_OUTPUT_FILE_PATH, TEMP_OUTPUT_FILES_PATH


if not file_valid(LATEST_OUTPUT_FILE_PATH):
    latest_df = pd.read_csv(LATEST_OUTPUT_FILE_PATH)
else:
    latest_df = pd.DataFrame()

    print(f'Warning: {LATEST_OUTPUT_FILE_PATH} doesn\'t exist or is empty. Creating it.')

full_base_path = os.path.join(os.getcwd(), TEMP_OUTPUT_FILES_PATH)

paths = [
    os.path.join(full_base_path, path) for path in
    os.listdir(full_base_path)
    if any(filetype in path for filetype in ['.csv'])
]

if paths:
    combined_df = pd.concat([
        latest_df,
        pd.concat([pd.read_csv(path) for path in paths])
    ])

    consolidated_df = combined_df.drop_duplicates(subset=['match_id', 'player_id'], keep='first')

    consolidated_df.to_csv(LATEST_OUTPUT_FILE_PATH, index=False)

    print(f'Data consolidated and saved to {LATEST_OUTPUT_FILE_PATH}')
else:
    print("No new files found in the specified directory.")
