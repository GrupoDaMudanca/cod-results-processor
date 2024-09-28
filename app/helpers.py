
import csv

from app.match import Match, MatchRecord
from config import OUTPUT_FILE_PATH


def read_new_match(match_data: dict) -> Match:
    return Match(*[MatchRecord(**record) for record in match_data])


def write_matches(matches: list[Match]) -> None:
    header = ['match_id', 'player_id', 'player_name', 'score', 'kills', 'damage', 'redeploys', 'objectives']

    with open(OUTPUT_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=header)

        writer.writeheader()

        rows = [
            {
                'match_id': match.id,
                'player_id': record.player.id,
                'player_name': record.player.name,
                'score': record.score,
                'kills': record.kills,
                'damage': record.damage,
                'redeploys': record.redeploys,
                'objectives': record.objectives
            }
            for match in matches
            for record in match.records
        ]

        writer.writerows(rows)
