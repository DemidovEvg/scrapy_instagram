# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import TakeFirst, MapCompose


class UserItem(scrapy.Item):
    user_id = scrapy.Field(output_processor=TakeFirst())
    username = scrapy.Field(output_processor=TakeFirst())
    user_photo = scrapy.Field(output_processor=TakeFirst())

class FollowerFollowingItem(scrapy.Item):
    username = scrapy.Field(output_processor=TakeFirst())
    user_follower_name = scrapy.Field(output_processor=TakeFirst())
    
