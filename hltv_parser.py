import requests
from bs4 import BeautifulSoup
import csv
import pdb

class HltvParser:
    BASE_URL = 'https://www.hltv.org/stats/players/'

    def __init__(self, filename, player_sufix):
        self.filename = filename
        self.data_dict = {}
        self.player_sufix = player_sufix
       

    def parse(self, only_headers= False):
        self.data_from_response()
        self.write_file(only_headers)

    def write_headers(self):
        self.data_from_response()
        self.write_file()
        
    def hltv_response(self):
        full_url = self.BASE_URL + self.player_sufix
        headers = { 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Referer": "https://www.hltv.org/",
                "DNT": "1"
            }
        return requests.get(full_url, headers=headers)
    
    def write_file(self, only_headers = True):
        with open(self.filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            if only_headers:
                writer.writerow(self.data_dict.keys())
            else:
                writer.writerow(self.data_dict.values())
    
    def data_from_response(self):
        soup = BeautifulSoup(self.hltv_response().content, 'html.parser')
        data_dict = {}
        self.data_dict['player']      = soup.find('h1',  class_='summaryNickname text-ellipsis').get_text(strip=True)
        self.data_dict['firepower']              = soup.find('div', class_="row-stats-section-score").contents[0].get_text(strip=True)
        self.data_dict['kpr']                    = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Kills per round'}).get('data-original-value')
        self.data_dict['damage_per_round']       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round'}).get('data-original-value')
        self.data_dict['dpr_win']                = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round win'}).get('data-original-value')
        self.data_dict['rounds_with_kill']       = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a kill'}).get('data-original-value')
        self.data_dict['rating_1']               = soup.find('div', class_='role-stats-row stats-side-combined', title="HLTV's in-house formula for performance, taking into account Kills, Damage, Survival, Impact, and round-to-round consistency.").find('div', class_='role-stats-data').get_text(strip=True)
        self.data_dict['rounds_with_multi_kill'] = soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a multi-kill'}).get('data-original-value')
        self.data_dict['pistol_round_rating']    = soup.find('div', class_='role-stats-row stats-side-combined', title="Rating 1.0 in the first round of each half.").find('div', class_='role-stats-data').get_text(strip=True)
        return self.data_dict

HltvParser('hltv_attributes2.csv', '922/snappi').write_headers()
for el in ('922/snappi', '7998/s1mple'):
    HltvParser('hltv_attributes2.csv', el).parse()
