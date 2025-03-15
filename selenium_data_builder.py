from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class SeleniumDataBuiler:

    ATTRS = (
        'kpr','dpr','kpr_win','dpr_win','rounds_with_k', 'rounds_with_multi_k'
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
        age_str = element = self.driver.find_element(By.CLASS_NAME, "summaryPlayerAge").text
        age = int(age_str.split()[0])
        return age
    
    def data_original_value(self, text):
        parent_div = self.driver.find_element(By.CSS_SELECTOR, f"div.role-stats-row.stats-side-combined[data-per-round-title='{text}']")
        striped = parent_div.get_attribute("data-original-value").strip('%')
        return float(striped)
    
    
    
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