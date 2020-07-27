from mongoengine import *
from models.ProfilePicture import ProfilePicture


class Badge(Document):
    """
    Template for a user achievement badge in the Database.
    """
    meta = {'db_alias': 'file',
            'collection': 'badge'}
    # for first set of badges this was set to filename of the picture upon ingestion.
    # can be set in other ways for new badges
    id = StringField(required=True, primary_key=True)
    # was set in the same way as id for the first set. can of course be set independently for new badges
    name = StringField(required=True)
    # this is the icon of the Badge
    picture = FileField(content_type='image/jpeg')
    unlocked_picture = ReferenceField(document_type=ProfilePicture, reverse_delete_rule=CASCADE, required=False)
    # currently not used in the first set of badges
    description = StringField()
    cost = IntField(required=True)
