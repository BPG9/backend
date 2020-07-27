from mongoengine import *
from models.Badge import Badge
from models.ProfilePicture import ProfilePicture

badge_dict = {}
for badge in Badge.objects.all():
    badge_dict[badge.id] = 0


class User(Document):
    """
        Template for a user in the Database.
    """
    meta = {'db_alias': 'user',
            'collection': 'user'}
    # has to be unique. further enforced in account creation and ChangeUsername function
    username = StringField(required=True, unique=True)
    # will be stored as a hash. hashed by werkzeug's generate_password_hash()
    password = StringField(required=True)
    # needed to create tours. modified by PromoteUser with Code
    producer = BooleanField(default=False)
    # list of badges the user has earned. updated when a user makes progess towards a badge
    badges = ListField(ReferenceField(document_type=Badge, reverse_delete_rule=PULL))
    # TODO: possibly add a default picture here. Would have to know document id of the ProfilePicture on the server
    #       to use as default. Seems unsafe to hardcode this if database changes though.
    #       Could maybe also register a new delete rule that resets it to a default picture if the chosen one is deleted
    profile_picture = ReferenceField(document_type=ProfilePicture, reverse_delete_rule=NULLIFY)
    # initialized with all badges that exist upon creation. when new badges are created they are added for all users
    badge_progress = DictField(default=badge_dict)
