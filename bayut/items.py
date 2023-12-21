import scrapy


# Nested Items can be used
class BayutAgencyItem(scrapy.Item):
    agency_url = scrapy.Field()
    agency_name = scrapy.Field()
    num_of_properties = scrapy.Field()
    about_agency = scrapy.Field()
    agents = scrapy.Field()


# You can make multiple nested items which is more robust: create an item for the agency, agents, and properties. Then nest them togther.
