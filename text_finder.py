class TextFinder:
    def __init__(self, soup):
        self.soup = soup
       
    def player(self):
        h1 = self.soup.find('h1',  class_='summaryNickname text-ellipsis')
        return h1.get_text(strip=True)
    
    def role_str(self, role):
        role_str = "role-stats-section role-" + role
        div = self.soup.find('div', class_= role_str ).find('div', class_="row-stats-section-score")
        return div.get_text(strip=True)
  
    def firepower(self):
        return self.role_str('firepower')
    
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
    
    def section_text_data_pr(self, data_title):
        try:
            parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined',  attrs={'data-per-round-title': data_title})
            if not parent_div:
                return ''
            roles_state_div = parent_div.find('div', class_='role-stats-data')
            if not roles_state_div:
                return ''
            return roles_state_div.get_text(strip=True)
        except Exception as e:
            return ''
        
    def section_text_title(self, title):
        try:
            parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', title=title)
            if not parent_div:
                return ''
            roles_state_div = parent_div.find('div', class_='role-stats-data')
            if not roles_state_div:
                return ''
            return roles_state_div.get_text(strip=True)
        except Exception as e:
            return ''
    
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
    
    # Entry   
    def entrying(self):
        return self.role_str('entrying')

    def saved_by_teammate_pr(self):
        return self.section_text_data_pr('Saved by teammate per round')
        
    def traded_deaths_pr(self):
        return self.section_text_data_pr('Traded deaths per round')
        
    def traded_death_percentage(self):
        return self.section_text_title("Percentage of opening deaths where the player's killer was also killed within 5 seconds.")
    
    def opening_death_traded_percentage(self):
        return self.section_text_title("Percentage of opening deaths where the player's killer was also killed within 5 seconds.")

    def asists_pr(self):
        return self.section_text_data_pr('Assists per round')
    
    def support_rounds(self):
        return self.section_text_title("Rounds with an assist, survival, or traded death but no kills.")
    
    #opening
    def opening(self):
        return self.role_str('opening')
    
    def opening_kills_pr(self):
        return self.section_text_data_pr('Opening kills per round')
    
    def opening_deaths_pr(self):
        return self.section_text_data_pr('Opening deaths per round')
    
    def opening_attempts(self):
        return self.section_text_data_pr('Opening attempts')
    
    def opening_sucess(self):
        return self.section_text_title('The percentage of opening duels in which the player got the kill.')

    def win_percent_after_open_kill(self):
        return self.section_text_title('The round win percentage of 5v4s in which the player found the opener.')
    
    def attacks_per_round(self):
        return self.section_text_data_pr('Attacks per round')
    
    def sniping(self):
        return self.role_str('sniping')

    def clutching(self):
        return self.role_str('clutching')
    
    def utility(self):
        return self.role_str('utility')