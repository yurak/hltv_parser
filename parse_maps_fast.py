#!/usr/bin/env python3
"""Fast parallel map parsing with minimal logging."""

import csv
import sys
from multiprocessing import Process
from selenium_parser import SeleniumParser
from clusterization.role_features import PLAYERS_TOP20_SOURCE, CS_MAPS

def parse_maps_fast(game_version, output_file, silent=True):
    """Parse map statistics with minimal logging."""

    # Load players
    with open(PLAYERS_TOP20_SOURCE, "r") as file:
        players = [row[0] for row in csv.reader(file) if row]

    # Initialize CSV with headers
    SeleniumParser(output_file, players[0], CS_MAPS[0], game_version=game_version, headless=True).write_headers()

    # Parse each player for each map
    for player in players:
        for cs_map in CS_MAPS:
            try:
                parser = SeleniumParser(output_file, player, cs_map, game_version=game_version, headless=True)
                parser.parse()
            except:
                pass

def run_cs2():
    """Run CS2 parsing."""
    parse_maps_fast("cs2", "map_stats_cs2.csv")

def run_csgo():
    """Run CS:GO parsing."""
    parse_maps_fast("csgo", "map_stats_csgo.csv")

if __name__ == "__main__":
    import os

    # Start both processes
    p1 = Process(target=run_cs2)
    p2 = Process(target=run_csgo)

    p1.start()
    p2.start()

    print(f"CS2: PID {p1.pid} | CS:GO: PID {p2.pid}")
    print(f"Monitor: watch -n 10 'wc -l map_stats_*.csv'")

    p1.join()
    p2.join()

    print("Done. Merge: python3 merge_map_stats.py")
