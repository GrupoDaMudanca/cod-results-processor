import json
import os
from typing import List

from app.helpers import read_new_match, write_matches
from app.match import Match

from config import (
    GEMINI_API_KEY,
    GEMINI_DESIRED_MODEL,
    RESULT_FILETYPES,
    RESULT_FILES_PATH
)

import google.generativeai as genai

from google.generativeai.types.file_types import File

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_DESIRED_MODEL)


def upload_files(paths) -> List[File]:
    return [genai.upload_file(path) for path in paths]


def process_file(file: File) -> Match:
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

            return a json with the following info and schema:

            [{raw_player_name: string, score: int, kills: int, damage: int, redeploys: int, objectives: int}]
            '''
        ]
    )

    file.delete()

    match = read_new_match(
        json.loads(
            result.text.replace('```json', '').replace(
                '```', '').replace('\n', '').replace(' ', '')
        )
    )

    return match


def process_files(root_path: str) -> List[Match]:
    full_base_path = os.path.join(os.getcwd(), root_path)

    paths = [
        os.path.join(full_base_path, path) for path in
        os.listdir(full_base_path)
        if any(filetype in path for filetype in RESULT_FILETYPES)
    ]

    return [process_file(file) for file in upload_files(paths)]


write_matches(process_files(RESULT_FILES_PATH))
