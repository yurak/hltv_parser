class TextFinder:
    def __init__(self, soup):
        self.soup = soup
       
    def player(self):
        h1 = self.soup.find('h1',  class_='summaryNickname text-ellipsis')
        return h1.get_text(strip=True)
    
    def firepower(self):
        div = self.soup.find('div', class_="row-stats-section-score")
        return div.contents[0].get_text(strip=True)
    
    def pistol_round_rating(self):
        try:
            parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', title="Rating 2.0 in the first round of each half")
            if not parent_div:
                return ''
            roles_state_div = parent_div.find('div', class_='role-stats-data')
            if not roles_state_div:
                return ''
            return roles_state_div.get_text(strip=True)
        except Exception as e:
            return ''

    def kpr(self):    
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Kills per round'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')
    
    def damage_per_round(self):
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')
    
    def dpr_win(self):
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Damage per round win'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')
    
    def rounds_with_kill(self):
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a kill'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')
    
    def rating_1(self):
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', title="HLTV's in-house formula for performance, taking into account Kills, Damage, Survival, Impact, and round-to-round consistency.")
        if not parent_div:
            return ''
        roles_state_div = parent_div.find('div', class_='role-stats-data')
        roles_state_div.get_text(strip=True)
    
    def rounds_with_multi_kill(self):
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Rounds with a multi-kill'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')