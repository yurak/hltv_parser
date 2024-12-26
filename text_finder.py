class TextFinder:
    ATTRS = [
                'player',
                'country', 'age', 'team',
                'firepower', 'rating_2',
                'kpr', 'damage_per_round', 'dpr_win', 'rounds_with_kill',
                'pistol_round_rating','rounds_with_multi_kill', 'entrying',
                'entrying',
                'saved_by_teammate_pr', 'traded_deaths_pr','traded_death_percentage', 
                'opening_death_traded_percentage', 'asists_pr','support_rounds',
                'opening',
                'opening_kills_pr', 'opening_deaths_pr', 'opening_attempts',
                'opening_sucess', 'win_percent_after_open_kill', 'attacks_per_round',
                'sniping',
                'sniping_kpr', 'sniping_k_percentage', 'rounds_w_sniping_k_percentage',
                'sniping_multi_kill_rounds','sniping_opening_kpr',
                'trading',
                'saved_teammate_pr', 'trade_kills_pr', 'trade_kills_percentage',
                'assisted_kills_percentage', 'damage_per_kill',
                'clutching',
                'clutch_points_pr', 'last_alive_percentage', 'one_v_one_percentage',
                'time_alive_pr', 'saved_per_round_loss',
                'utility',
                'utility_damage_pr', 'utility_kills_per100_r', 'flashes_thrown_pr', 
                'flash_assists_pr', 'timme_opponent_flashed_pr'
            ]
    def __init__(self, soup):
        self.soup = soup
    
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

    def player(self):
        h1 = self.soup.find('h1',  class_='summaryNickname text-ellipsis')
        return h1.get_text(strip=True)
    
    def age(self):
        div = self.soup.find('div',  class_='summaryPlayerAge')
        return div.get_text(strip=True)
    
    def team(self):
        div = self.soup.find('div',  class_='SummaryTeamname text-ellipsis')
        return div.get_text(strip=True)
    
    def country(self):
        div = self.soup.find('div',  class_='summaryRealname text-ellipsis')
        return div.find('img').get('title')

    def role_str(self, role):
        role_str = "role-stats-section role-" + role
        div = self.soup.find('div', class_= role_str ).find('div', class_="row-stats-section-score")
        return div.get_text(strip=True)
    
    # firepower
    def firepower(self):
        return self.role_str('firepower')
    
    def pistol_round_rating(self):
        if self.section_text_title('Rating 2.0 in the first round of each half.'):
            return self.section_text_title('Rating 2.0 in the first round of each half.')
        else:
            return self.section_text_title('Rating 2.1 in the first round of each half.')

    def kpr(self):    
        parent_div = self.soup.find('div', class_='role-stats-row stats-side-combined', attrs={'data-per-round-title': 'Kills per round'})
        if not parent_div:
            return ''
        return parent_div.get('data-original-value')
    
    def damage_per_round(self):
        return self.section_text_data_pr('Damage per round')
    
    def dpr_win(self):
        return self.section_text_data_pr('Damage per round win')
    
    def rounds_with_kill(self):
        return self.section_text_data_pr('Rounds with a kill')
       
    def rating_2(self):
        txt = "HLTV's in-house formula for performance, taking into account Kills, Damage, Survival, Impact, and round-to-round consistency."
        return self.section_text_title(txt)
    
    def rounds_with_multi_kill(self):
        return self.section_text_data_pr ('Rounds with a multi-kill')
     
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
    
    # sniping
    def sniping(self):
        return self.role_str('sniping')
    
    def sniping_kpr(self):
        return self.role_str('sniping')
    
    def sniping_k_percentage(self):
        return self.role_str('sniping')
    
    def rounds_w_sniping_k_percentage(self):
        return self.role_str('sniping')
    
    def sniping_multi_kill_rounds(self):
        return self.role_str('sniping')
    
    def sniping_opening_kpr(self):
        return self.role_str('sniping')
    
    def sniping_kpr(self):
        return self.section_text_data_pr('Sniper kills per round')
    
    def sniping_k_percentage(self):
        return self.section_text_title('Percentage of kills that come with the AWP and SSG-08 snipers.')
    
    def rounds_w_sniping_k_percentage(self):
        return self.section_text_title('Percentage of rounds that the player delivers a kill from the AWP or SSG-08 snipers.')
    
    def sniping_multi_kill_rounds(self):
        return self.section_text_data_pr('Sniper multi-kill rounds')
    
    def sniping_opening_kpr(self):
        return self.section_text_data_pr('Sniper opening kills per round')

    # clutching
    def clutching(self):
        return self.role_str('clutching')
    
    def clutch_points_pr(self):
        return self.section_text_data_pr('Clutch points per round')
    
    def last_alive_percentage(self):
        return self.section_text_title('The percentage of round where this player is the last alive on the server.')
    
    def one_v_one_percentage(self):
        txt = 'Percentage of 1on1 clutches this player wins. The average is about 60%, not 50%, because 1on1s are only created from 2on1s, leaving an easy trade kill sometimes. Be wary of sample size, clutch situations are very rare.'
        return self.section_text_title(txt)
    
    def time_alive_pr(self):
        return self.section_text_data_pr('Time alive per round')
    
    def saved_per_round_loss(self):
        return self.section_text_title('The percentage of round losses this player survives in.')
    
    # utility
    def utility(self):
        return self.role_str('utility')
    
    def utility_damage_pr(self):
        return self.section_text_data_pr('Utility damage per round')
    
    def utility_kills_per100_r(self):
        return self.section_text_data_pr('Utility kills per 100 rounds')
    
    def flashes_thrown_pr(self):
        return self.section_text_data_pr('Flashes thrown per round')
    
    def flash_assists_pr(self):
        return self.section_text_data_pr('Flash assists per round')
    
    def timme_opponent_flashed_pr(self):
        return self.section_text_data_pr('Time opponent flashed per round')
    
    # trading
    def trading(self):
        return self.role_str('trading')
    
    def saved_teammate_pr(self):
        return self.section_text_data_pr('Saved teammate per round')
    
    def trade_kills_pr(self):
        return self.section_text_data_pr('Trade kills per round')
    
    def trade_kills_percentage(self):
        return self.section_text_title('Percentage of kills that were on opponents within 5 seconds of them killing a teammate.')
    
    def assisted_kills_percentage(self):
        return self.section_text_title('Percentage of kills that were on opponents that had already been damaged by teammates.')
    
    def damage_per_kill(self):
        return self.section_text_title('Damage divided by kills. An average below 100 would mean a player is getting more low-damage kills.')