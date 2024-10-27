import requests
from bs4 import BeautifulSoup
import csv
import pdb

def hltv_response(player_sufix):
    base = 'https://www.hltv.org/stats/players/'
    full_url = base + player_sufix
    headers = { 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Referer": "https://www.hltv.org/",
                "DNT": "1"
            }
    return requests.get(full_url, headers=headers)

def data_from_response(response):
    soup = BeautifulSoup(response.content, 'html.parser')
    data_dict = {}
    data_dict['player']      = soup.find('h1',  class_='summaryNickname text-ellipsis').get_text(strip=True)
    data_dict['firepower']              = soup.find('div', class_="row-stats-section-score").contents[0].get_text(strip=True)
    data_dict['kpr']                    = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Kills per round'}).get('data-original-value')
    data_dict['damage_per_round']       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round'}).get('data-original-value')
    data_dict['dpr_win']                = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round win'}).get('data-original-value')
    data_dict['rounds_with_kill']       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a kill'}).get('data-original-value')
    data_dict['rating_1']               = soup.find('div', class_='role-stats-row stats-side-combined', title="HLTV's in-house formula for performance, taking into account Kills, Damage, Survival, Impact, and round-to-round consistency.").find('div', class_='role-stats-data').get_text(strip=True)
    data_dict['rounds_with_multi_kill'] = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a multi-kill'}).get('data-original-value')
    data_dict['pistol_round_rating']    = soup.find('div', class_='role-stats-row stats-side-combined', title="Rating 1.0 in the first round of each half.").find('div', class_='role-stats-data').get_text(strip=True)
    return data_dict

def write_file(data_dict, filename = 'hltv_attributes.csv', with_headers = True):
    with open(filename, 'a+', newline='') as file:
        writer = csv.writer(file)
        if with_headers:
            writer.writerow(data_dict.keys())
            writer.writerow(data_dict.values())
        else:
            writer.writerow(data_dict.values())

def parse_player_stats(player_sufix ='922/snappi'):
    response =  hltv_response(player_sufix)
    if response.status_code != 200:
        print(f"Can't fetch: {response.status_code}")
        return 

    data_dict = data_from_response(response)
    write_file(data_dict)

def process_players(arr):
    for el in arr:
        parse_player_stats(el)

process_players(('922/snappi', '7998/s1mple'))