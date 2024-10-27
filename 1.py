import requests
from bs4 import BeautifulSoup
import csv


def parse_player_stats():
    url = "https://www.hltv.org/stats/players/922/snappi"

    headers = { 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            "Referer": "https://www.hltv.org/",
            "DNT": "1"
         }
    response = requests.get(url, headers=headers)


    if response.status_code != 200:
        print(f"Can't fetch: {response.status_code}")

    soup = BeautifulSoup(response.content, 'html.parser')


    player                 = soup.find('h1',  class_='summaryNickname text-ellipsis').get_text(strip=True)

    firepower              = soup.find('div', class_="row-stats-section-score").contents[0].get_text(strip=True)
    kpr                    = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Kills per round'}).get('data-original-value')
    damage_per_round       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round'}).get('data-original-value')
    dpr_win                = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round win'}).get('data-original-value')
    rounds_with_kill       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a kill'}).get('data-original-value')
    rating_1               = soup.find('div', class_='role-stats-row stats-side-combined', title="HLTV's in-house formula for performance, taking into account Kills, Damage, Survival, Impact, and round-to-round consistency.").find('div', class_='role-stats-data').get_text(strip=True)
    rounds_with_multi_kill = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a multi-kill'}).get('data-original-value')
    pistol_round_rating    = soup.find('div', class_='role-stats-row stats-side-combined', title="Rating 1.0 in the first round of each half.").find('div', class_='role-stats-data').get_text(strip=True)

    print(player, firepower, kpr, damage_per_round, dpr_win, rounds_with_kill, rating_1, rounds_with_multi_kill, pistol_round_rating)

    with open('hltv attributes.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Player", "firepower", "kpr", "damage per round", "dpr/win", "rounds with kill", "rating 1.0", "rounds with multi kill", "pistol round rating"])
        writer.writerow([player, firepower, kpr, damage_per_round, dpr_win, rounds_with_kill, rating_1, rounds_with_multi_kill, pistol_round_rating])
parse_player_stats()