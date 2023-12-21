import scrapy
from bayut.items import BayutAgencyItem
from selenium.webdriver import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
import time
import random
# from webdriver_manager.chrome import ChromeDriverManager
# import undetected_chromedriver as uc


class BayutSpiderSpider(scrapy.Spider):
    name = "bayut_spider"
    # allowed_domains = ["bayut.com"]
    # start_urls = ["https://www.bayut.com/companies/dubai/page-2/"]
    # start_urls = [
    #    f"https://www.bayut.com/companies/dubai/page-{page_number}/"
    #    for page_number in range(1, 168)
    # ][:1]

    def __init__(self, *args, **kwargs):
        super(BayutSpiderSpider, self).__init__(*args, **kwargs)
        chrome_options = ChromeOptions()
        chrome_options.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.stylesheet": 2,
                "profile.managed_default_content_settings.fonts": 2,
            },
        )
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--load-extension=Adblock-Plus_v3.21.1.crx")
        self.driver = Chrome(options=chrome_options)
        # options = uc.ChromeOptions()
        # options.add_argument("--blink-settings=imagesEnabled=false")
        # options.add_extension("Adblock-Plus_v3.21.1.crx")
        # options.headless = True
        # options.add_argument("--headless")
        # options.add_argument("--load-extension=Adblock-Plus_v3.21.1.crx")
        # self.driver = uc.Chrome(options=options)

    def start_requests(self):
        # You can either manually add the 8 cities or add code to automatically fetch them since there are only 9
        # start_urls = ["https://www.bayut.com/companies/dubai", "https://www.bayut.com/companies/abu-dhabi", "https://www.bayut.com/companies/sharjah, "https://www.bayut.com/companies/ajman", "https://www.bayut.com/companies/ras-al-khaimah", "https://www.bayut.com/companies/umm-al-quwain", "https://www.bayut.com/companies/al-ain", "https://www.bayut.com/companies/fujairah"]
        # for url in start_urls:
        #     yield scrapy.Request(url=url, callback=self.parse)

        start_urls = [
            f"https://www.bayut.com/companies/dubai/page-{i}/" for i in range(2, 50)
        ]
        for url in start_urls[:1]:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        companies_urls = (
            response.css("ul")
            .css("li[role='article'] > article > a::attr(href)")
            .getall()
        )
        for url in companies_urls[:2]:
            yield scrapy.Request(
                url=response.urljoin(url),
                callback=self.parse_agency,
            )
        #    next_page = response.css('a[title="Next"]::attr(href)').get()
        #    if next_page:
        #        yield response.follow(next_page, self.parse)

    async def parse_agency(self, response):
        agency = BayutAgencyItem()
        agency["agency_url"] = response.url
        agency["about_agency"] = {}
        agency_info = response.css(
            'div[aria-label="Agency header"] > div > ul > li::text'
        ).getall()
        agency_name = agency_info[0]
        agency["agency_name"] = agency_name
        num_of_properties = agency_info[2]
        agency["num_of_properties"] = num_of_properties

        ## Selenium code bit
        self.driver.get(response.url)
        read_more_buttons = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".dcd35213"))
        )
        if read_more_buttons:
            for button in read_more_buttons:
                button.click()

            about_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@class="_3ba710dd"]/ul/li')
                )
            )
            for i in about_elements:
                time.sleep(random.uniform(1, 3))  # Add randomness to the scraper
                spans = WebDriverWait(i, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span"))
                )
                spans = [i.text for i in spans]
                spans = [i.replace(":", "").replace("\n", "") for i in spans]
                if any((spans[0] in _ for _ in ["DED", "ORN", "RERA"])):
                    about_dict = {spans[0]: spans[-1]}
                else:
                    about_dict = {spans[0]: spans[1]}

                agency["about_agency"].update(about_dict)
        else:  # If no read more text that is loaded by clicking read more, scrape html normally
            about_list = response.xpath('//div[@class="_3ba710dd"]/ul/li')
            for i in about_list:
                spans = i.css("span::text").getall()
                spans = [i.replace(":", "").replace("\n", "") for i in spans]
                if spans[0] in ["DED", "ORN", "RERA"]:
                    about_dict = {spans[0]: spans[-1]}
                else:
                    about_dict = {spans[0]: spans[1]}
                agency["about_agency"].update(about_dict)

        agents_button = self.driver.find_element(
            by="xpath", value='//div[contains(text(), "Agents")]'
        )
        agents_button.click()
        agents_elements = self.driver.find_elements(
            by="css selector", value="div > ul > li > article > a"
        )

        agency["agents"] = []

        agents_urls = [element.get_attribute("href") for element in agents_elements]
        # Some agencies do not have their agents listed. To scrape these properties, I would need to create a separate spider for the agents.
        # And then just merge the name of the lister of the property with the agent's name if available or the agency.
        for url in agents_urls[:1]:
            req = scrapy.Request(response.urljoin(url), self.parse_agent)
            res = await self.crawler.engine.download(req)
            agent = await self.parse_agent(res)
            agency["agents"].append(agent)

        yield agency

    async def parse_agent(self, response):
        agent = {}
        agent["agent_url"] = response.url
        agent["about_agent"] = {}
        agent_name = response.xpath('//li[@aria-label="Agent name"]/text()').get()
        agent["agent_name"] = agent_name

        agent_review = response.css('div[class="_1075545d _96d4439a"]::text').get()
        agent["agent_review"] = agent_review or None

        ## Selenium code bit
        self.driver.get(response.url)
        # About section
        buttons = self.driver.find_elements(by="css selector", value=".dcd35213")
        if buttons:  # If there is a read more button
            for button in buttons:
                button.click()
                about_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        ((By.CSS_SELECTOR, "ul > li.def7ab22"))
                    )
                )
            for i in about_elements:
                spans = WebDriverWait(i, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span"))
                )
                spans = [i.text for i in spans]
                spans = [i.replace(":", "").replace("\n", "") for i in spans]
                if any((spans[0] in _ for _ in ["DED", "ORN", "RERA", "BRN"])):
                    about_dict = {spans[0]: spans[-1]}
                else:
                    about_dict = {spans[0]: spans[1]}
                agent["about_agent"].update(about_dict)
        else:  # If no read more text that is loaded by clicking read more, scrape html normally
            about_list = response.xpath('//div[@class="c0c107ff"]/ul/li/div/div')
            for i in about_list:
                spans = i.css("span::text").getall()
                spans = [i.replace(":", "").replace("\n", "") for i in spans]
                if spans[0] in ["DED", "ORN", "RERA", "BRN"]:
                    about_dict = {spans[0]: spans[-1]}
                else:
                    about_dict = {spans[0]: spans[1]}
                agent["about_agent"].update(about_dict)

        # Phone number
        call_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Call"]'))
        )
        call_button.click()
        agent_phone_number = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//a[@aria-label="Listing phone number"]')
            )
        )
        agent["phone_number"] = agent_phone_number.text

        properties_urls = response.css(
            "div > ul> li > article > div a::attr(href)"
        ).getall()

        agent["properties"] = []

        for url in properties_urls[:1]:
            time.sleep(random.uniform(1, 3))  # Add randomness to the scraper
            req = scrapy.Request(response.urljoin(url), self.parse_property)
            res = await self.crawler.engine.download(req)
            property = self.parse_property(res)
            agent["properties"].append(property)

        return agent

    def parse_property(self, response):
        property_information_dict = {}
        property_information_dict["property_url"] = response.url
        property_price = response.xpath(
            '//div[@aria-label="Property basic info"]/div/text()'
        ).get()
        property_information_dict["Property_info"]: property_price
        property_location = response.css(
            'div[aria-label="Property header"]::text'
        ).get()
        property_information_dict["Property_location"] = property_location

        properties_information = response.xpath(
            '//div[./h2[contains(text(), "Property Information")]]/ul/li/span/text()'
        ).getall()
        if properties_information:
            for i in range(0, len(properties_information) - 1, 2):
                property_information_dict[
                    properties_information[i]
                ] = properties_information[i + 1]

        ## Selenium bit
        self.driver.get(response.url)
        read_more_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[contains(text(), "Read More")]')
            )
        )
        if read_more_button:
            read_more_button.click()
            info = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        'div[aria-label = "Property description"] >  div > span',
                    )
                )
            )
            info_text = " ".join([element.text for element in info]).strip()

            property_information_dict["Property_description"] = info_text
        else:
            info_text = response.css(
                'div[aria-label = "Property description"] >  div > span::text'
            ).getall()
            property_information_dict["Property_description"] = info_text

        self.driver.execute_script("window.scrollTo(0, 1800)")
        Validated_info_dict = {}
        try:
            Validated_info = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        'ul[class="_7e76939c"] > li',
                    )
                )
            )

            if Validated_info:
                for i in Validated_info:
                    cards = WebDriverWait(i, 10).until(
                        EC.presence_of_all_elements_located(
                            (
                                By.XPATH,
                                "//div[.//h3[contains(text(), 'Validated Information')]]/ul/li",
                            )
                        )
                    )
                    cards = [f.text for f in cards]
                    Validated_info_dict.update({cards[0]: cards[1]})
                property_information_dict["validated_information"] = Validated_info_dict
        except TimeoutException:
            property_information_dict["validated_information"] = None

        try:
            building_info_dict = {}
            building_info = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        "//div[.//h2[contains(text(), 'Building Information')]]/ul/li",
                    )
                )
            )
            if building_info:
                for i in building_info:
                    cards = WebDriverWait(i, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span"))
                    )

                    cards = [f.text for f in cards]
                    building_info_dict.update({cards[0]: cards[1]})
                property_information_dict["building_info"] = building_info_dict
        except TimeoutException:
            property_information_dict["building_info"] = None

        try:
            property_information_dict["amneties"] = {}
            # Click on the 'amenities' button
            amenities_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(text(), "amenities")]')
                )
            )
            if amenities_button:
                amenities_button.click()
                # Extract amenities information
                amenities_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//div[@id='property-amenity-dialog']/ul/div")
                    )
                )

                for element in amenities_elements:
                    category = element.find_element(
                        By.XPATH, ".//div[@class='_9c1fb575']"
                    ).text
                    subcategories = [
                        i.text
                        for i in element.find_elements(
                            By.XPATH, './/span[@class="_005a682a"]'
                        )
                    ]
                    property_information_dict["amneties"].update(
                        {category: subcategories}
                    )

                # Close the amenities dialog
                exit_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            '//div[@aria-label="Dialog"]/button[@aria-label="Close button"]',
                        )
                    )
                )
                exit_button.click()

        except (TimeoutException, ElementClickInterceptedException):
            amneties_list = response.xpath(
                '//div[./h2[contains(text(), "Features / Amenities")]]//span[@class="_005a682a"]/text()'
            ).getall()
            if amneties_list:
                amneties = {"amneties": amneties_list}
                property_information_dict.update(amneties)
            else:
                property_information_dict["amneties"] = None

        try:
            schools_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@class="_89a30ada"]/div[2]')
                )
            )
            # Used to enter the nearby schools, restaurants, hopsitals, parks.
            nearby_locations = {}
            if schools_button:
                schools_button.click()

                tabs = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, '//div[@class="_1075545d a5f6a0f5"]/div')
                    )
                )[1:]
                for tab in tabs:
                    tab.click()
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//div[@id="places-scrollable"]/div/span/div')
                        )
                    )
                    sub_tabs = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, '//div[@id="places-scrollable"]/div/span/div')
                        )
                    )
                    sub_tabs = [
                        i.text.encode("utf-8").decode("utf-8") for i in sub_tabs
                    ]
                    nearby_locations.update({tab.text: sub_tabs})
            property_information_dict.update({"nearby_locations": nearby_locations})
        except (TimeoutException, StaleElementReferenceException):
            property_information_dict["nearby_locations"] = None

        return property_information_dict

    def spider_closed(self, spider):
        # Quit the WebDriver when the spider is closed
        self.driver.quit()
