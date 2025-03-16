from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class SeleniumDataBuiler:
    NOT_VISIBLE = 'not_visible'
    ATTRS = (
        'kpr','dpr','kpr_win','dpr_win','rounds_with_k', 'rounds_with_multi_k',
        'saved_by_teammate', 'traded_deaths_pr', 'traded_death_percent', 'open_death_percent', 'asssits_per_round','support_rounds'
    )

    def __init__(self, driver, cs_map):
        self.driver = driver
        self.cs_map = cs_map
        self.dict = {}

    def player_name(self):
        return self.driver.find_element(By.XPATH, "//h1[contains(@class, 'summaryNickname')]").text

    def rating20(self):
        return 1.2

    def age(self):
        age_str = self.driver.find_element(By.CLASS_NAME, "summaryPlayerAge").text
        age = int(age_str.split()[0])
        return age

    def data_original_value(self, text):
        parent_div = self.driver.find_element(By.CSS_SELECTOR, f"div.role-stats-row.stats-side-combined[data-per-round-title='{text}']")
        striped = parent_div.get_attribute("data-original-value").strip('%')
        return float(striped)

    def section_text_title(self, title):
        el = self.driver.find_element(By.XPATH, f"//div[contains(@class, 'role-stats-row') and contains(@class, 'stats-side-combined') and @title=\"{title}\"]")
        if el.is_displayed():
            return el.text
        return self.NOT_VISIBLE

    #firepower
    def kpr(self):
        text = 'Kills per round'
        return self.data_original_value(text)

    def dpr(self):
        text = 'Damage per round'
        return self.data_original_value(text)

    def kpr_win(self):
        text = 'Kills per round win'
        return self.data_original_value(text)

    def dpr_win(self):
        text = 'Damage per round win'
        value = self.data_original_value(text)
        return value / 100

    def rounds_with_k(self):
        text = 'Rounds with a kill'
        percent = self.data_original_value(text)
        normalized = percent / 100
        return normalized

    def rounds_with_multi_k(self):
        text = 'Rounds with a multi-kill'
        percent = self.data_original_value(text)
        normalized = percent / 100
        return normalized

    def pistol_rating(self):
        if self.section_text_title('Rating 2.0 in the first round of each half.'):
            return self.section_text_title('Rating 2.0 in the first round of each half.').text
        elif self.section_text_title('Rating 1.0 in the first round of each half.'):
            return self.section_text_title('Rating 1.0 in the first round of each half.').text
        else:
            return self.section_text_title('Rating 2.1 in the first round of each half.').text

    #trading
    def saved_by_teammate(self):
        text = 'Saved by teammate per round'
        return self.data_original_value(text)
    
    def traded_deaths_pr(self):
        text = 'Traded deaths per round'
        return self.data_original_value(text)
    
    def traded_death_percent(self):
        return self.section_text_title("Percentage of deaths where the player's killer was also killed within 5 seconds.")
    
    def open_death_percent(self):
        return self.section_text_title("Percentage of opening deaths where the player's killer was also killed within 5 seconds.")
    
    def asssits_per_round(self):
        text = 'Assists per round'
        return self.data_original_value(text)
    
    def support_rounds(self):
        return self.section_text_title('Rounds with an assist, survival, or traded death but no kills.')

    def build(self):
        self.section('', True)
        self.dict['player_name'] = self.player_name()
        self.dict['map'] = self.cs_map
        self.dict['age'] = self.age()
        #firepower
        for attr in self.ATTRS:
            self.dict[attr] = getattr(self, attr)()

        element = self.driver.find_element(By.XPATH, '//*[@data-side-stats="ct"]')
        element.click()
        self.section('ct_')
        element = self.driver.find_element(By.XPATH, '//*[@data-side-stats="t"]')
        element.click()
        self.section('t_')
        return self.dict
    
    def section(self, side ='', click_cookie=False ):
        if click_cookie:
            allow_cookies_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow all cookies')]"))
            )
            allow_cookies_button.click()
        
        elements =  self.driver.find_elements(By.CLASS_NAME, 'role-stats-section')
        for element in elements:
            array = element.text.split('\n')
            property_name = side + array[0].lower()
            self.dict[property_name] = int(array[1])/100