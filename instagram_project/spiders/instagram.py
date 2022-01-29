from copy import deepcopy
import scrapy
from scrapy.http import HtmlResponse
from scrapy.loader import ItemLoader
from ..items import UserItem, FollowerFollowingItem
import re
from urllib.parse import urlencode
import requests
from ..settings import USER_AGENT
from collections import Counter


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['instagram.com']
    start_urls = ['http://instagram.com/']

    real_list_from_instagram = ['tapochek88', 'egorr.g', 'elefantishe', 'sunnyhunnybunny', 'bakaytatyana', 'andru_sha', 'olgalakhmanova', '6_6_mad_6_6', 'vkrenev', 'ds_hairandnails', 'ribakit1313', 'olyagaykova', 'akperovaga', 'ninasyrnik', 'dmitriyrakitskiy', 'm_mius', 'mrtidnew', 'anton_sepesov', 'mr.zhirkin', 'shustrila1509', '_anastasiia__09', 'mariiatim35', 'gaikova.s', 'valentina_ivlitskaya', 'olyagaykova', 'bubnowajulia', '_i.bad_', 'mintty.isabella', 'kissa_olya', 'zlatarevna', 'svetlanagaykova5', 'lsn2601', 'vrabi_christina', 'loginelina', 'arssinger', 'nicho.ls13', 'lavrywa', 'xinxin597', 'apollinaria_bad', 'darridilly', 'musicfortstore', 'mariya_oppen_geim', 'zlatarevna', 'komarovam', 'irina.po.wwpc', 'maximdanberg', 'allroad_4x4_spb', 'yakovlev_xdr', 'roger.5022', 'wasteddestiny', 'ac_piter', 'ukuleleshop_nsk', 'badaninava', 'minimod716', '_sharmmaribraiton_', 'myinsta_fun', 'kofr4.ru', 'celebrity_cinematotrapeher', 'crazy_life_303', 'blackcat_band', 'blackcat_band', 'rasfender', 'vdv_drummer', 'vopiiashind', 'morskiekruiz']

    users_set = set()
    users_counter = Counter()
    users_list = []
    # Пользователи с которых будем собирать данные
    # users_for_parse = ['ribakit1313', 'k_l_e_o86', 'dmitriygaikov']
    users_for_parse = ['dmitriygaikov']
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

        # Закоментил на время, пока не понимаю почему кого-то берет по 2 раза, а кого-то ни разу
        # urls ={'followers': f'https://i.instagram.com/api/v1/friendships/{user_id}/followers/?',
        #         'following': f'https://i.instagram.com/api/v1/friendships/{user_id}/following/?'} 

        urls ={'followers': f'https://i.instagram.com/api/v1/friendships/{user_id}/followers/?'}

        query = {"count": 12,
                 "search_surface": "follow_list_page"}

        for followers_or_following, url in urls.items():
            
            yield response.follow(f'{url}{urlencode(query)}', 
                            callback=self.parse_follow_list,
                            headers={"User-Agent" : "Instagram 155.0.0.37.107"}, 
                            cb_kwargs={'user_id': user_id,
                                        'username': username,
                                        'query': query,
                                        'url': url,
                                        'followers_or_following': followers_or_following})
        
    def parse_follow_list(self, response: HtmlResponse, **kwargs):
        text_json = response.json()
        followers_or_followings = text_json['users']

        for f in followers_or_followings:
            self.users_set.add(f['username'])
            self.users_counter.update([f['username']])
            self.users_list.append(f['username'])

        for f in followers_or_followings:

            user_item = UserItem(user_id = f['pk'],
                            username = f['username'],
                            user_photo = f['profile_pic_url'])
            user = ItemLoader(item=user_item, response=response)
            yield user.load_item()

        for f in followers_or_followings:
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
        
        if 'next_max_id' in text_json:
            query = dict(kwargs['query'])
            query['max_id'] = text_json['next_max_id']
            yield response.follow(f"{kwargs['url']}{urlencode(query)}", 
                            callback=self.parse_follow_list,
                            headers={"User-Agent" : "Instagram 155.0.0.37.107"},
                            cb_kwargs={'user_id': kwargs['user_id'],
                                        'username': kwargs['username'],
                                        'query': query,
                                        'url': kwargs['url'],
                                        'followers_or_following': kwargs['followers_or_following']})
        else:
            # Выведим списки по 12 пользователей, в том порядке, как они выдаются через реальный браузер
            cursor = 0
            print(f'{len(self.real_list_from_instagram) = }')
            print(f'Списки из браузера: ')
            while True:
                if cursor + 12 > len(self.real_list_from_instagram):
                    print(self.real_list_from_instagram[cursor:])
                    break
                else:
                    print(self.real_list_from_instagram[cursor:cursor+12])
                    cursor += 12
            # Выведим списки по 12 пользователей, в том порядке, как они распарсены
            cursor = 0
            print(f'{len(self.users_list) = }')
            print(f'Списки при парсинге: ')
            while True:
                if cursor + 12 > len(self.users_list):
                    print(self.users_list[cursor:])
                    break
                else:
                    print(self.users_list[cursor:cursor+12])
                    cursor += 12

            print(f'Найдем разницу в списках через множесва:')
            print(f'{ set(self.real_list_from_instagram) - self.users_set = }')
            print(f'Найдем количетво повторов юзеров:')
            print(f'{ self.users_counter = }')




        
        

