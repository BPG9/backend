from mongoengine import *


class ProfilePicture(Document):
    """
    Model for user profile pictures.
    Separated from regular pictures on the model level
        as these can be saved in a separate collections and users can only choose from them.
    """
    meta = {'db_alias': 'file',
            'collection': 'profilepicture'}
    picture = FileField(content_type='image/jpeg')
    locked = BooleanField(default=False)
