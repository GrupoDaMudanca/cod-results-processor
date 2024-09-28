import os
import json
from PIL import Image
import hashlib
import csv

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_DESIRED_MODEL = os.environ.get('GEMINI_DESIRED_MODEL')
RESULT_FILETYPE = os.environ.get('RESULT_FILETYPE')
RESULT_FILES_PATH = os.environ.get('RESULT_FILES_PATH')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_DESIRED_MODEL)


def upload_files(paths):
    return [[genai.upload_file(path), path] for path in paths]


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

            return a json with the following info and schema:

            [{player: string, score: int, kills: int, damage: int, redeploys: int, objectives: int}]
            '''
        ]
    )

    file.delete()

    return json.loads(
        result.text.replace('```json', '').replace(
            '```', '').replace('\n', '').replace(' ', '')
    )


def image_to_hash(image_path):
    # Abra a imagem
    with Image.open(image_path) as img:
        # Converta a imagem em bytes
        img_bytes = img.tobytes()

        # Crie um hash usando hashlib (por exemplo, SHA-256)
        hash_object = hashlib.sha256(img_bytes)

        # Retorne o hash hexadecimal
        return hash_object.hexdigest()


def write_results_csv(results):
    with open('result_games.csv', 'w', newline='') as csvfile:
        fieldnames = ['player', 'score', 'kills',
                      'damage', 'redeploys', 'objectives', 'game_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for game in results:
            for player in game:
                writer.writerow(player)


def process_files(root_path):
    full_base_path = os.path.join(os.getcwd(), root_path)

    paths = [
        os.path.join(full_base_path, path) for path in
        os.listdir(full_base_path)
        if RESULT_FILETYPE in path
    ]

    game_matches = []

    for file, path in upload_files(paths):
        players = []
        for player in process_file(file):
            game_id = image_to_hash(path)
            # TODO add here if to clan tag
            splited = player['player'].split(']')
            if (len(splited) > 1):
                player['player'] = splited[1]
            player['game_id'] = game_id
            players.append(player)

        game_matches.append(players)

    return game_matches


game_results = process_files(RESULT_FILES_PATH)
write_results_csv(game_results)
