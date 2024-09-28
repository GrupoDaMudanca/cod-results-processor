import os
import json

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_DESIRED_MODEL = os.environ.get('GEMINI_DESIRED_MODEL')
RESULT_FILETYPE = os.environ.get('RESULT_FILETYPE')
RESULT_FILES_PATH = os.environ.get('RESULT_FILES_PATH')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_DESIRED_MODEL)


def upload_files(paths):
    return [genai.upload_file(path) for path in paths]


def process_file(file):
    print(f'{file=}')

    result = model.generate_content(
        [
            file,
            "\n\n",
            '''
            Read this image for me, extracting: 
            - The names of the players
            - Their scores, the number of kills
            - The amount of damage, 
            - The number of redeploys and the number of objectives.
            
            Disconsider the line showing the squad's total points.
            Disconsider the clan tag, which is the text enclosed in between [], and any text that isn't in the name column.
            
            return a json with the following info and schema:
            
            [{player: string, score: int, kills: int, damage: int, redeploys: int, objectives: int}]
            '''
        ]
    )

    file.delete()

    return json.loads(
        result.text.replace('```json', '').replace('```', '').replace('\n', '').replace(' ', '')
    )


def process_files(root_path):
    paths = [
        path for path in
        os.listdir(os.path.join(os.getcwd(), root_path))
        if RESULT_FILETYPE in path
    ]

    return [process_file(file) for file in upload_files(paths)]


print(process_files(RESULT_FILES_PATH))
