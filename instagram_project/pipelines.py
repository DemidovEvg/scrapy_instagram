# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from .items import FollowerFollowingItem
from neo4j import GraphDatabase


class Neo4jDb:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_or_merge_user(self, name, user_id, user_photo=''):
        with self.driver.session() as session:
            session.write_transaction(self._create_or_merge_user, name, user_id, user_photo)

    @staticmethod
    def _create_or_merge_user(tx, name, user_id, user_photo):
        result = tx.run("MATCH (u:User {name: $name}) RETURN u", name=name)
        if not result.single():
            tx.run("CREATE (u:User"
                "{name: $name, user_id: $user_id, user_photo: $user_photo})", 
                name=name, user_id=user_id, user_photo=user_photo)

    def follower_following(self, username, user_follower_name):
        with self.driver.session() as session:
            session.write_transaction(self._follower_following, username, user_follower_name)

    @staticmethod
    def _follower_following(tx, username,user_follower_name):
        result = tx.run("MATCH (u1:User {name: $username})<-[fol:followed]-"
                        "(u2:User {name: $user_follower_name}) RETURN fol",
                        username=username, user_follower_name=user_follower_name)

        if not result.single():
            tx.run("MATCH (u1), (u2) "
                "WHERE u1.name=$username and u2.name=$user_follower_name "
                "CREATE (u1)<-[fol:followed]-(u2)", 
                username=username, user_follower_name=user_follower_name)

    def clean_db(self):
        with self.driver.session() as session:
            session.run("MATCH (u) DETACH DELETE u")

instagram_db = Neo4jDb("bolt://localhost:7687", "neo4j", "123")
instagram_db.clean_db()

class CreateUserPipeline:

    def process_item(self, item, spider):
        if not isinstance(item, FollowerFollowingItem):
            instagram_db.create_or_merge_user(name=item['username'], 
                                            user_id=item['user_id'], 
                                            user_photo=item['user_photo'])
        return item


class CreateLinksBetweenPipeline:
    def process_item(self, item, spider):
        if isinstance(item, FollowerFollowingItem):
            instagram_db.follower_following(username=item['username'], 
                                            user_follower_name=item['user_follower_name'])
        return item
