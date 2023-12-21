# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import pymongo
from scrapy.utils.project import get_project_settings

settings = get_project_settings()


class MongoDBPipeline:
    def __init__(self):
        conn = pymongo.MongoClient(
            settings.get("MONGO_HOST"), settings.get("MONGO_PORT")
        )
        db = conn[settings.get("MONGO_DB_NAME")]
        self.collection = db[settings["MONGO_COLLECTION_NAME"]]

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        self.collection.insert_one(dict(item))
        return item
