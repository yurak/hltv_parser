from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class SeleniumDataBuiler:
    def __init__(self, driver, cs_map):
        self.driver = driver
        self.cs_map = cs_map

    def player_name(self):
        return self.driver.find_element(By.XPATH, "//h1[contains(@class, 'summaryNickname')]").text
    
    def rating20(self):
        return 1.2
    
    def age(self):
        age_str = element = self.driver.find_element(By.CLASS_NAME, "summaryPlayerAge").text
        age = int(age_str.split()[0])
        return age

    
    def build(self):
        dict = self.main_section()
        dict['player_name'] = self.player_name()
        dict['map'] = self.cs_map
        dict['age'] = self.age()
        element = self.driver.find_element(By.XPATH, '//*[@data-side-stats="ct"]')
        element.click()
        dict_ct =  self.main_section_ct()
        dict.update(dict_ct)
        element = self.driver.find_element(By.XPATH, '//*[@data-side-stats="t"]')
        element.click()
        dict_t =  self.main_section_t()
        dict.update(dict_t)
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
            dict['all_'+array[0].lower()] = int(array[1])/100
        
        return dict
    
    def main_section_ct(self):
        elements =  self.driver.find_elements(By.CLASS_NAME, 'role-stats-section')
        dict = {}
        for element in elements:
            array = element.text.split('\n')
            dict['ct_' + array[0].lower()] = int(array[1])/100
        
        return dict
    
    def main_section_t(self):
        elements =  self.driver.find_elements(By.CLASS_NAME, 'role-stats-section')
        dict = {}
        for element in elements:
            array = element.text.split('\n')
            dict['t_' + array[0].lower()] = int(array[1])/100
        
        return dict