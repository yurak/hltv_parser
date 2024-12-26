import requests
from bs4 import BeautifulSoup
import csv
import pdb
from text_finder import TextFinder
import time

class PlayersParser:
    BASE_URL = 'https://www.hltv.org/players/'

    def __init__(self, filename, letter= 'A'):
        self.filename = filename
        self.letter = letter

    def url_with_letter(self):
        return 'https://www.hltv.org/ranking/teams/2024/december/16'
    
    def hltv_response(self):
        headers = { 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Referer": "https://www.hltv.org/",
                "DNT": "1"
            }
        return requests.get(self.url_with_letter(), headers=headers)
    
    def data_from_response(self):
        response = self.hltv_response()

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return [
                a['href'] for td in soup.find_all('td', class_='player-holder') 
                for a in td.find_all('a', href=True)
            ]
           
    def write_file(self):
        hrefs = self.data_from_response()
        with open(self.filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            for href in hrefs: 
                href = href.lstrip("/player/")
                writer.writerow([href])


# alphabet_list = list(map(chr, range(65, 91)))

# for char in alphabet_list:
#     PlayersParser('players_top20.csv', char).write_file()
PlayersParser('players_top20.csv', 'char').write_file()
        