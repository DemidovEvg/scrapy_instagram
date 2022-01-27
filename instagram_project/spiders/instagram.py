from copy import deepcopy
import scrapy
from scrapy.http import HtmlResponse
from scrapy.loader import ItemLoader
from ..items import UserItem, FollowerFollowingItem
import re
from urllib.parse import urlencode
import requests
from ..settings import USER_AGENT


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['instagram.com']
    start_urls = ['http://instagram.com/']

    # Пользователи с которых будем собирать данные
    users_for_parse = ['ribakit1313', 'k_l_e_o86', 'dmitriygaikov']

    # Для аутентификации под пользователем
    url_authentication = 'https://www.instagram.com/accounts/login/ajax/'
    formdata = {'username': 'Onliskill_udm',
                'enc_password': '#PWD_INSTAGRAM_BROWSER:10:1643131213:AZZQAGTPs6xfu+lt7ppOoFuIqKbWrZ4VaEX53g+SZCn8PJlFrepy7g4RoBJ9hG8g+yNb2R3TWGMrJek2u4SWHgpXYJPp7CijVJirea6j+tAGshfXR9HonVrpXtM9HF0oH+v2RlGNdeDqkBSgLuKb'}

    def parse(self, response: HtmlResponse):
        csrf_token = re.findall(r'"csrf_token":"(\w+)"', response.text)[0]
        headers = {'x-csrftoken': csrf_token}

        yield scrapy.FormRequest(self.url_authentication,
                                    method='POST',
                                    callback=self.after_login,
                                    headers=headers,
                                    formdata=self.formdata)

    def after_login(self, response: HtmlResponse):
        text_json = response.json()
        if text_json['authenticated']:
            for user_for_parse in self.users_for_parse:

                yield response.follow(f'/{user_for_parse}', callback=self.parse_friend)

    def parse_friend(self, response: HtmlResponse):       
        
        user_id = re.findall(r'"logging_page_id":"profilePage_(\w+)"', response.text)[0]
        username = re.findall(rf'"id":"{user_id}","username":"(\w+)"', response.text)[0]

        
        user_info = requests.get(f'https://www.instagram.com/{username}/?__a=1', headers={'User-agent': USER_AGENT})
        user_photo = user_info.json()['graphql']['user']['profile_pic_url']
        item=UserItem(user_id=user_id,
                      username=username,
                      user_photo=user_photo)
        user = ItemLoader(item=item, response=response)
        yield user.load_item()

        urls ={'followers': f'https://i.instagram.com/api/v1/friendships/{user_id}/followers/?',
                'following': f'https://i.instagram.com/api/v1/friendships/{user_id}/following/?'} 

        query = {"count": 12,
                 "search_surface": "follow_list_page"}

        for followers_or_following, url in urls.items():
            
            yield response.follow(f'{url}{urlencode(query)}', 
                            callback=self.parse_follow_list,
                            headers={"User-Agent" : "Instagram 155.0.0.37.107"}, 
                            cb_kwargs={'user_id': user_id,
                                        'username': username,
                                        'query': query.copy(),
                                        'url': url,
                                        'followers_or_following': followers_or_following})
        
    def parse_follow_list(self, response: HtmlResponse, **kwargs):
        text_json = response.json()
        if text_json['users']:
            if 'next_max_id' in text_json:
                kwargs['query']['max_id'] = text_json['next_max_id']
                yield response.follow(f"{kwargs['url']}{urlencode(kwargs['query'])}", 
                                callback=self.parse_follow_list,
                                headers={"User-Agent" : "Instagram 155.0.0.37.107"},
                                cb_kwargs={'user_id': kwargs['user_id'],
                                            'username': kwargs['username'],
                                            'query': kwargs['query'].copy(),
                                            'url': kwargs['url'],
                                            'followers_or_following': kwargs['followers_or_following']})
            followers_or_followings = text_json['users']
            for f in followers_or_followings:
                user_item = UserItem(user_id = f['pk'],
                                username = f['username'],
                                user_photo = f['profile_pic_url'])
                user = ItemLoader(item=user_item, response=response)
                yield user.load_item()

                if kwargs['followers_or_following'] == 'followers': 
                    username = kwargs['username']              
                    user_follower_name = f['username']
                    
                else:
                    username = f['username']
                    user_follower_name = kwargs['username']
                    
                folower_following_item = FollowerFollowingItem(username=username,
                                            user_follower_name=user_follower_name)

                folower_following = ItemLoader(item=folower_following_item, response=response)
                yield folower_following.load_item()
    

        
        

