#!/usr/bin/env python3
"""Run CSGO parsing with reliable duplicate checking."""

import csv
from selenium_parser import SeleniumParser
from clusterization.role_features import PLAYERS_TOP20_SOURCE, CS_MAPS

def get_existing_urls(filename):
    """Get set of already parsed URLs."""
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            return {row[0] for row in reader if row}
    except:
        return set()

def run_csgo_safe():
    output_file = "map_stats_csgo.csv"

    # Load players
    with open(PLAYERS_TOP20_SOURCE, "r") as file:
        players = [row[0] for row in csv.reader(file) if row]

    # Get existing URLs
    existing = get_existing_urls(output_file)
    print(f"Already parsed: {len(existing)} URLs")

    # Parse each player for each map
    for i, player in enumerate(players):
        for cs_map in CS_MAPS:
            parser = SeleniumParser(output_file, player, cs_map, game_version="csgo", headless=True)
            url = parser.full_url()

            if url in existing:
                continue

            try:
                parser.parse()
                existing.add(url)
                print(f"[{len(existing)}] {player} - {cs_map}")
            except Exception as e:
                print(f"Error: {player} - {cs_map}: {e}")

if __name__ == "__main__":
    run_csgo_safe()
