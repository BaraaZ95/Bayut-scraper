# Bayut-scraper
Python crawler that scrapes bayut data with scrapy and selenium

To run:
1) install requirements
```
pip install -r requirements
```
2) run crawler
```
scrapy crawl bayut_spider
```
Note: 
- If you want to write the data to mongodb, enter your mongodb connection and db info in the settings.py file
- Example of the output is in output.json file
