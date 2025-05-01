import pandas as pd

class Normaliser:

    TEAM_MAP = {
            'navi': ['b1t', 'iM', 'Aleksib', 'jL', 'w0nderful'],
            'vitality': ['ZywOo', 'flameZ', 'ropz', 'mezii', 'apEX']
        }
    COLUMNS_SLASH = ('sniping', 'trading', 'clutching', 'utility', 'firepower', 'opening', 'entrying')
 
    FIREPOWER  = ['kills_per_round','rounds_with_a_kill','kills_per_round_win','rating_1.0','damage_per_round','rounds_with_a_multi_kill','damage_per_round_win', 'pistol_round_rating']
    ENTRYING = ['saved_by_teammate_per_round','traded_deaths_per_round','traded_deaths_percentage','opening_deaths_traded_percentage','assists_per_round','support_rounds']
    TRADING = ['saved_teammate_per_round','trade_kills_per_round','trade_kills_percentage','assisted_kills_percentage','damage_per_kill']
    OPENING = ['opening_kills_per_round','opening_deaths_per_round','opening_attempts','opening_success','win_after_opening_kill','attacks_per_round']
    CLUTCHING = ['clutch_points_per_round','last_alive_percentage','1on1_win_percentage','time_alive_per_round','saves_per_round_loss']
    SNIPING = ['sniper_kills_per_round','sniper_kills_percentage','rounds_with_sniper_kills_percentage','sniper_multi_kill_rounds','sniper_opening_kills_per_round']
    UTILITY = ['utility_damage_per_round','utility_kills_per_100_rounds','flashes_thrown_per_round','flash_assists_per_round','time_opponent_flashed_per_round']

    MAIN_COMPONENTS_MAP = {
                        'firepower': FIREPOWER,
                        'entrying': ENTRYING, 
                        'trading': TRADING, 
                        'opening': OPENING, 
                        'clutching': CLUTCHING,
                        'sniping': SNIPING,
                        'utility': UTILITY
                    }

    PERCENTS = ['rounds_with_a_kill','damage_per_round','rounds_with_a_multi_kill','traded_deaths_percentage', 'opening_deaths_traded_percentage',
                'support_rounds', 'trade_kills_percentage', 'assisted_kills_percentage', 'damage_per_kill', 'opening_attempts',
                'opening_success', 'win_after_opening_kill', 'attacks_per_round', 'last_alive_percentage', '1on1_win_percentage',
                'saves_per_round_loss', 'sniper_kills_percentage', 'rounds_with_sniper_kills_percentage'
            ]
    
    TENS = ['utility_damage_per_round']
    MAXIMUM_COLUMNS = ['rating_1.0', 'kills_per_round', 'kills_per_round_win', 'damage_per_round_win', 'pistol_round_rating']

    TIME_COLUMNS = ['time_alive_per_round']

    def __init__(self, source_file, normalized_file ):
        self.source_file =  source_file
        self.normalized_file = normalized_file
        
    def call(self):
        #self.replace_blank()
        self.normalize()

    def replace_blank(self):
        df = pd.read_csv(self.source_file)

        # Replace all '-' symbols with 0
        df.replace('-', 0, inplace=True)

        # Save the modified CSV file
        df.to_csv(self.source_file, index=False)


    def normalize(self):
        df = pd.read_csv(self.source_file)
        player_to_team = {}
        for team, players in self.TEAM_MAP.items():
            for player in players:
                player_to_team[player] = team

        df['team'] = df['player_name'].apply(lambda p: player_to_team.get(p, 'other'))
        for column in self.PERCENTS:
            if column in df:
                df[column] = df[column].replace('-', 0.0)
                try:
                    df[column] = df[column].astype(float) / 100
                    df[column] = df[column].round(2)
                except:
                    df[column] = 0

        for column in self.TENS:
            if column in df:
                df[column] = df[column].replace('-', 0.0)
                try:
                    df[column] = df[column].astype(float) / 10
                    df[column] = df[column].round(2)
                except:
                    df[column] = 0
        
        for column in self.MAXIMUM_COLUMNS:

            if column in df:
                df[column] = df[column].replace('-', 0.0)
                to_float = df[column].astype(float)
                df[column] = (to_float - to_float.min()) / (to_float.max() - to_float.min())
                df[column] = df[column].round(2)

        for column in self.TIME_COLUMNS:
            if column in df:
                df[column] = df[column].replace('-', 0.0)
                df[column] = df[column].apply(self.time_to_seconds)
                df[column] = (df[column] / 60).round(2)
        
        df = df.apply(lambda col: col.replace('-', 0.0))
        df.to_csv(self.normalized_file, index=False)

    def time_to_seconds(self, time_str):
        if isinstance(time_str,str):
            parts = time_str.split()
            total_seconds = 0
            for part in parts:
                if 'm' in part:
                    total_seconds += int(part.strip('m')) * 60
                elif 's' in part:
                    total_seconds += int(part.strip('s'))
        else:
            total_seconds = 0.0
        return total_seconds



#  error_rows = df[pd.to_numeric(df[column], errors='coerce').isna()]
