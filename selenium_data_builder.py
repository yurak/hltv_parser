from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time

class SeleniumDataBuiler:
    def __init__(self, driver, cs_map):
        self.driver = driver
        self.cs_map = cs_map
        self.dict = {}

    def player_name(self):
        return self.driver.find_element(By.CLASS_NAME, "player-summary-stat-box-left-nickname text-ellipsis").text

    def age(self):
        age_str = self.driver.find_element(By.CLASS_NAME, "player-summary-stat-box-left-player-age").text
        age = int(age_str.split()[0])
        return age

    def safe_click(self, xpath):
        """Waits for an element, scrolls into view, and clicks it safely."""
        element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        WebDriverWait(self.driver, 2).until(lambda d: element.is_displayed())
        self.driver.execute_script("arguments[0].click();", element)

    def build(self):
        self.dict = {}
        self.section('', True)

        #self.dict['player_name'] = self.player_name()
        self.dict['map'] = self.cs_map
        self.dict['age'] = self.age()

        self.safe_click('//*[@data-side-stats="ct"]')
        self.section('ct_')

        self.safe_click('//*[@data-side-stats="t"]')
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
            
            klass = {
                'ct_': 'ct',
                't_': 't'
            }.get(side, 'combined')
           
            clickable_section = element.find_element(By.CSS_SELECTOR, f"div.role-stats-section-title-wrapper.stats-side-{klass}")
            # if clickable_section.is_displayed():
            if not 'active' in element.get_attribute("class").split():
                clickable_section.click()
            
            
            nested_elements = element.find_elements(By.CSS_SELECTOR, f"div.role-stats-row.stats-side-{klass}")
            for nested_el in nested_elements:
               
                time.sleep(0.07)
                if nested_el.text:
                    nested_array = nested_el.text.split('\n')
                    camel_case= nested_array[0]
                    key = side + camel_case.lower().replace(" ", "_").replace('-','_').replace('%','')
                    try:
                        result = float(nested_array[1].strip('%'))
                    except ValueError:
                        result = nested_array[1]
    
                    self.dict[key] = result
                else:
                    continue