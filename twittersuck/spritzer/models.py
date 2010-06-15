from django.db import models
import re
import time, datetime

def strip_tags(text):
    return re.sub('<.*?>', '', text)    

def convert_timestamp(datestr):
    return datetime.datetime(*time.strptime(datestr, '%a %b %d %H:%M:%S +0000 %Y')[:6])

class User(models.Model):
    id = models.IntegerField(primary_key=True)
    username = models.TextField(db_index=True)
    name = models.TextField()
    location = models.TextField(db_index=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    profile_image_url = models.TextField()

class Tweet(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    text = models.TextField()
    user = models.ForeignKey(User, related_name='tweets')
    source = models.TextField()
    timestamp = models.DateTimeField(db_index=True)
    
    # this refers to a Tweet, but we can't guarantee we know anything about
    # that tweet, so it's not a foreign key
    reply_to = models.CharField(null=True, blank=True, max_length=15,
                                db_index=True)
    
    # same deal with Users
    reply_to_name = models.TextField(null=True, blank=True)

    @staticmethod
    def from_json(json):
        user, created = User.objects.get_or_create(id=json['user']['id'])
        user.username = json['user']['screen_name']
        user.name = json['user']['name']
        user.location = json['user']['location']
        user.description = json['user']['description']
        user.profile_image_url = json['user']['profile_image_url']
        user.save()

        tweet,_ = Tweet.objects.get_or_create(
            id = str(json['id']),
            text = json['text'],
            user=user,
            source = strip_tags(json['source']),
            timestamp = convert_timestamp(json['created_at']),
            reply_to = str(json['in_reply_to_status_id']),
            reply_to_name = json['in_reply_to_screen_name']
        )
    
    @staticmethod
    def handle_delete(json):
        id = json['delete']['status']['id']
        try:
            to_delete = Tweet.objects.get(id=str(id))
            to_delete.delete()
            print "BALEETED"
        except Tweet.DoesNotExist:
            pass

