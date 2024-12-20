import requests
from bs4 import BeautifulSoup
import csv
import pdb
from text_finder import TextFinder
import time

class HltvParser:
    BASE_URL = 'https://www.hltv.org/stats/players/'

    PLAYERS = (
        '11893/zywoo',
        '3741/niko'
    )

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
        headers = { 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Referer": "https://www.hltv.org/",
                "DNT": "1"
            }
        return requests.get(self.full_url(), headers=headers)
    
    def write_file(self, only_headers = True):
        with open(self.filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            if only_headers:
                writer.writerow(self.data_dict.keys())
            else:
                if self.data_dict.values():
                    print('processing ' +  self.player_sufix)
                    writer.writerow(self.data_dict.values())
                else:
                      print('data was not found for:' +  self.player_sufix)
    def full_url(self):
        return self.BASE_URL + self.player_sufix
    
    def data_from_response(self):
        self.data_dict = {}
        response = self.hltv_response()

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_finder = TextFinder(soup)
            self.data_dict['full_url'] = self.full_url()
            for attr in TextFinder.ATTRS:
                self.data_dict[attr] = getattr(text_finder, attr)()
            
        else:
            print(self.full_url())
            print('response is:' + str(self.hltv_response().status_code))
        return self.data_dict

# HltvParser('hltv_attributes2.csv', '922/snappi').write_headers()
# for el in HltvParser.PLAYERS:
#     time.sleep(2.5)
#     HltvParser('hltv_attributes2.csv', el).parse()


# with open('players.csv', 'r') as file:
#     reader = csv.reader(file)
    
#     # Convert rows into an array (list of lists)
#     rows = [row for row in reader]
#     for row in rows:
#         time.sleep(2.5)
#         HltvParser('hltv_attributes2.csv', row[0]).parse()