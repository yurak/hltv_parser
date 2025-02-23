from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class SeleniumDataBuiler:
    def __init__(self, driver, cs_map):
        self.driver = driver
        self.cs_map = cs_map

    def player_name(self):
        return self.driver.find_element(By.XPATH, "//h1[contains(@class, 'summaryNickname')]").text
    
    def build(self):
        dict = self.main_section()
        dict['player_name'] = self.player_name()
        dict['map'] = self.cs_map
        return dict
        
    def main_section(self):
        allow_cookies_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow all cookies')]"))
        )
        allow_cookies_button.click()
     
        elements =  self.driver.find_elements(By.CLASS_NAME, 'role-stats-section')
        dict = {}
        for element in elements:
            array = element.text.split('\n')
            dict[array[0].lower()] = int(array[1])/100
        
        return dict