import datetime
from mongoengine import *
from models.User import User


class Tour(Document):
    """
    Template for a tour in the Database.
    """
    meta = {'db_alias': 'tour',
            'collection': 'tour'}
    name = StringField(required=True)
    owner = ReferenceField(document_type=User, required=True, reverse_delete_rule=CASCADE)
    # this is how users find the tour. uniqueness is also enforced in the creation function
    search_id = StringField(required=True, unique=True)
    # password users use to join the tour. can be changed later. featured tours can be joined without session id
    session_id = IntField(required=True)
    # notably includes the owner
    users = ListField(ReferenceField(document_type=User, reverse_delete_rule=PULL))
    # alternatives: 'pending' and 'featured'. used for the review system
    status = StringField(default='private')
    # scale is also enforced upon creation
    difficulty = IntField(required=True, min_value=1, max_value=5)
    description = StringField()
    lastEdit = DateTimeField(default=datetime.datetime.now)
    # this is managed by checkpoint creation and modification methods
    current_checkpoints = IntField(default=0)
