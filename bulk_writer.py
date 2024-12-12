from hltv_parser import HltvParser
import time
import csv
import pdb
import os

class BulkWriter:
    def __init__(self, filename ='htlv_attrs.csv'):
        self.sleep_time = 1
        self.source_filename = 'players.csv'
        self.filename = filename
        self.slice_tail = 3
    
    def call(self):
        HltvParser(self.filename, '922/snappi').write_headers()
        if os.path.exists(self.source_filename):
            with open(self.source_filename, 'r') as file:
                reader = csv.reader(file)
                rows = [row for row in reader]
                for row in rows[0:self.slice_tail]:
                    time.sleep(self.sleep_time)
                    HltvParser(self.filename, row[0]).parse()
        else:
            print(f"File {self.source_filename} does not exist.")

BulkWriter().call()