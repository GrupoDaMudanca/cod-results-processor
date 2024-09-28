import os

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_DESIRED_MODEL = os.environ.get('GEMINI_DESIRED_MODEL')
RESULT_FILETYPES = os.environ.get('RESULT_FILETYPES').replace(' ', '').split(',')
RESULT_FILES_PATH = os.environ.get('RESULT_FILES_PATH')
OUTPUT_FILES_PATH = os.environ.get('OUTPUT_FILES_PATH')
PLAYER_NAMES_FILE_PATH = os.environ.get('PLAYER_NAMES_FILE_PATH')
