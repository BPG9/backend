import datetime

from flask_graphql_auth import create_access_token, create_refresh_token, mutation_jwt_refresh_token_required, \
    get_jwt_identity, mutation_jwt_required, get_jwt_claims
from graphene import ObjectType, List, Mutation, String, Field, Boolean, Int
from werkzeug.security import generate_password_hash, check_password_hash
from models.Admin import Admin as AdminModel
from models.MuseumObject import MuseumObject as MuseumObjectModel
from models.Code import Code as CodeModel
from models.User import User as UserModel
from models.Tour import Tour as TourModel
from models.Question import Question as QuestionModel
from models.AppFeedback import AppFeedback as AppFeedbackModel
from models.Favourites import Favourites as FavouritesModel
from models.Badge import Badge as BadgeModel
from models.Picture import Picture as PictureModel
from models.ProfilePicture import ProfilePicture as ProfilePictureModel
from models.Checkpoint import Checkpoint as CheckpointModel
from models.PictureCheckpoint import PictureCheckpoint as PictureCheckpointModel
from models.ObjectCheckpoint import ObjectCheckpoint as ObjectCheckpointModel
from models.MultipleChoiceQuestion import MultipleChoiceQuestion as MCQuestionModel
from graphene_file_upload.scalars import Upload
import string
import random
from app.ProtectedFields import StringField, ProtectedString, BooleanField, ProtectedBool
from app.Fields import Tour, MuseumObject, Admin, User, Picture, Badge, CheckpointUnion, ProfilePicture
from copy import deepcopy
"""
These are the mutations available in the web portal 
Tasks: create and manage admin accounts 
       create producer promotion codes 
       demote users 
       delete accounts  
       create and manage the museum objects  
       review tours that have been submitted by producers 
       manage featured tours 
       read app feedback 
        
login creates a jwt access and refresh token. 
most other methods require a valid token

"""

# a user claim that is inserted into the claims of admin access tokens upon creation.
# mutations in this Schema validate that the token includes this claim to ensure functions are only called by admins
admin_claim = {'admin': True}


class CreateMuseumObject(Mutation):
    """ Create a Museum Object.
        Parameters: token, String, required, valid jwt access token with the admin claim
                    objectId, String, required, inventory id of the object in the museum
                    category, String, required, category of the object in the museum. 'Abteilung'
                    subCategory, String, required, sub-category of the object in the museum. 'Sammlungsbereich'
                    title, String, required, name of the object
                    year, String, optional, year the object was created/found
                    picture, List of Upload, optional,  images in jpeg format
                    art_type, String, optional, classification of the object e.g. 'painting'
                    creator, String, optional, creators of the object
                    material, String, optional, materials the object is made of
                    size, String, information about the size of the object
                    location, String, optional, locations the object was made/found at
                    description, String, optional, description of the object
                    additionalInformation, String, optional, any additional information about the object
                    interdisciplinary_context, String, optional, interdisciplinary relations of the object
        returns the object and True if successful
        returns Null and False if token did not belong to admin or object with that id already existed
        returns Null and an empty value for ok if token was invalid """

    class Arguments:
        object_id = String(required=True)
        category = String(required=True)
        sub_category = String(required=True)
        title = String(required=True)
        token = String(required=True)
        time_range = String()
        year = String()
        picture = List(Upload)
        art_type = String()
        creator = String()
        material = String()
        size = String()
        location = String()
        description = String()
        additional_information = String()
        interdisciplinary_context = String()

    museum_object = Field(lambda: MuseumObject)
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, object_id, category, sub_category, title, **kwargs):
        year = kwargs.get('year', None)
        picture = kwargs.get('picture', None)
        time_range = kwargs.get('time_range', None)
        art_type = kwargs.get('art_type', None)
        creator = kwargs.get('creator', None)
        material = kwargs.get('material', None)
        size = kwargs.get('size', None)
        location = kwargs.get('location', None)
        description = kwargs.get('description', None)
        additional_information = kwargs.get('additional_information', None)
        interdisciplinary_context = kwargs.get('interdisciplinary_context', None)

        if get_jwt_claims() == admin_claim:

            if not MuseumObjectModel.objects(object_id=object_id):
                museum_object = MuseumObjectModel(object_id=object_id, category=category, sub_category=sub_category,
                                                  title=title, time_range=time_range, year=year,
                                                  art_type=art_type, creator=creator, material=material,
                                                  size_=size, location=location, description=description,
                                                  additional_information=additional_information,
                                                  interdisciplinary_context=interdisciplinary_context)
                if picture is not None:
                    pics = []
                    for pic in picture:
                        x = PictureModel()
                        x.picture.put(pic, content_type='image/jpeg')
                        x.save()
                        pics.append(x)
                    museum_object.update(set__picture=pics)
                museum_object.save()
                return CreateMuseumObject(ok=BooleanField(boolean=True), museum_object=museum_object)

            else:
                return CreateMuseumObject(ok=BooleanField(boolean=False), museum_object=None)
        else:
            return CreateMuseumObject(ok=BooleanField(boolean=False), museum_object=None)


class UpdateMuseumObject(Mutation):
    """ Modify a Museum Object.
        Parameters: token, String, required, valid jwt access token with the admin claim
                    objectId, String, required, inventory id of the object in the museum
                    category, String, optional, category of the object in the museum. 'Abteilung'
                    subCategory, String, optional, sub-category of the object in the museum. 'Sammlungsbereich'
                    title, String, optional, name of the object
                    year, String, optional, year the object was created/found
                    picture, List of String, optional, document ids of existing Picture objects in the database
                    art_type, String, optional, classification of the object e.g. 'painting'
                    creator, String, optional, creators of the object
                    material, String, optional, materials the object is made of
                    size, String, optional, information about the size of the object
                    location, Strings, optional, locations the object was made/found at
                    description, String, optional, description of the object
                    interdisciplinary_context, String, optional, interdisciplinary relations of the object
                    additional_information, String, additional information about the object
        returns the updated object and True if successful
        returns Null and False if token did not belong to admin or object with that id does not exist or a picture id
            was invalid.
        returns Null and an empty value for ok if token was invalid
    """

    class Arguments:
        object_id = String(required=True)
        token = String(required=True)
        category = String()
        sub_category = String()
        time_range = String()
        title = String()
        year = String()
        picture = List(String)
        art_type = String()
        creator = String()
        material = String()
        size = String()
        location = String()
        additional_information = String()
        description = String()
        interdisciplinary_context = String()

    museum_object = Field(lambda: MuseumObject)
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, object_id, **kwargs):
        if get_jwt_claims() == admin_claim:
            if not MuseumObjectModel.objects(object_id=object_id):
                return UpdateMuseumObject(ok=BooleanField(boolean=False), museum_object=None)
            else:
                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                category = kwargs.get('category', None)
                sub_category = kwargs.get('sub_category', None)
                title = kwargs.get('title', None)
                time_range = kwargs.get('time_range', None)
                year = kwargs.get('year', None)
                picture = kwargs.get('picture', None)
                art_type = kwargs.get('art_type', None)
                creator = kwargs.get('creator', None)
                material = kwargs.get('material', None)
                size = kwargs.get('size', None)
                location = kwargs.get('location', None)
                description = kwargs.get('description', None)
                additional_information = kwargs.get('additional_information', None)
                interdisciplinary_context = kwargs.get('interdisciplinary_context', None)

                if category is not None:
                    museum_object.update(set__category=category)
                if sub_category is not None:
                    museum_object.update(set__sub_category=sub_category)
                if title is not None:
                    museum_object.update(set__title=title)
                if year is not None:
                    museum_object.update(set__year=year)
                if picture is not None:
                    pics = []
                    for pid in picture:
                        if PictureModel.objects(id=pid):
                            pic = PictureModel.objects.get(id=pid)
                            pics.append(pic)
                        else:
                            return UpdateMuseumObject(ok=BooleanField(boolean=False), museum_object=None)
                    museum_object.update(set__picture=pics)
                if art_type is not None:
                    museum_object.update(set__art_type=art_type)
                if time_range is not None:
                    museum_object.update(set__time_range=time_range)
                if additional_information is not None:
                    museum_object.update(set__additional_information=additional_information)
                if creator is not None:
                    museum_object.update(set__creator=creator)
                if material is not None:
                    museum_object.update(set__material=material)
                if size is not None:
                    museum_object.update(set__size_=size)
                if location is not None:
                    museum_object.update(set__location=location)
                if description is not None:
                    museum_object.update(set__description=description)
                if interdisciplinary_context is not None:
                    museum_object.update(set__interdisciplinary_context=interdisciplinary_context)
                museum_object.save()
                museum_object.reload()
                return UpdateMuseumObject(ok=BooleanField(boolean=True), museum_object=museum_object)
        else:
            return UpdateMuseumObject(ok=BooleanField(boolean=False), museum_object=None)


class CreateAdmin(Mutation):
    """Create a user account.
           Parameters: username, String, name of the account. has to be unique
                       password, String, password, no requirements, saved as a hash
           if successful returns the created user and ok=True
           if unsuccessful because the username is already taken returns Null and False
    """

    class Arguments:
        username = String(required=True)
        password = String(required=True)

    user = Field(lambda: Admin)
    ok = Boolean()

    def mutate(self, info, username, password):
        if not AdminModel.objects(username=username):
            user = AdminModel(username=username, password=generate_password_hash(password))
            user.save()
            return CreateAdmin(user=user, ok=True)
        else:
            return CreateAdmin(user=None, ok=False)


class DeleteMuseumObject(Mutation):
    """Delete a Museum Object.
       Parameters: token, String, valid jwt access token with the admin claim
                   objectId, String, museum inventory id of the object to be deleted
        returns True if successful
        returns false if token does not have admin claim
        returns empty value if token was invalid
        is successful if object does not exist
        deletes all references to the object in favourites, tours and questions
         """

    class Arguments:
        token = String(required=True)
        object_id = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, object_id):
        if get_jwt_claims() == admin_claim:
            if MuseumObjectModel.objects(object_id=object_id):
                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                pictures = museum_object.picture
                # delete associated pictures
                for picture in pictures:
                    picture.delete()
                # delete object from user favourites
                favourites = FavouritesModel.objects(favourite_objects__contains=museum_object)
                for favourite in favourites:
                    objects = favourite.favourite_objects
                    objects.remove(museum_object)
                    favourite.update(set__favourite_objects=objects)
                    favourite.save()
                # delete object reference from questions
                questions = QuestionModel.objects(linked_objects__contains=museum_object)
                for question in questions:
                    linked = question.linked_objects
                    linked.remove(museum_object)
                    question.update(set__linked_objects=linked)
                # delete checkpoints that reference the object
                checkpoints = ObjectCheckpointModel.objects(museum_object=museum_object)
                for checkpoint in checkpoints:
                    # update tour accordingly
                    tour = checkpoint.tour
                    max_idx = tour.current_checkpoints
                    max_idx -= 1
                    # reduce number of current checkpoints
                    tour.update(set__current_checkpoints=max_idx)
                    tour.save()
                    index = checkpoint.index
                    tour_checkpoints = CheckpointModel.objects(tour=tour)
                    # adjust index of later checkpoints in the tour
                    for cp in tour_checkpoints:
                        if cp.index > index:
                            cpidx = cp.index
                            cpidx -= 1
                            cp.update(set__index=cpidx)
                            cp.save()
                    checkpoint.delete()
                museum_object.delete()
            return DeleteMuseumObject(ok=BooleanField(boolean=True))

        else:
            return DeleteMuseumObject(ok=BooleanField(boolean=False))


class ChangePassword(Mutation):
    """Change a user's password.
       Requires the user to be logged in.
       Parameters: token, String, valid jwt access token of a user
                   password, String, the NEW password
       if successful returns True
       if unsuccessful because the token is invalid returns an empty value
    """

    class Arguments:
        token = String()
        password = String()

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, password):
        username = get_jwt_identity()
        user = AdminModel.objects.get(username=username)
        # password is again saved as a hash
        user.update(set__password=generate_password_hash(password))
        user.save()
        return ChangePassword(ok=BooleanField(boolean=True))


class Auth(Mutation):
    """Login. Create a session and jwt access and refresh tokens.
       Parameters: username, String, the username of the account you wish to log in to
                   password, String, the password of the account. password is hashed and compared to the saved hash.
        if successful returns a jwt accessToken (String), a jwt refresh token (String) and True
            inserts the admin claim to the token's user claims
        if unsuccessful because the user does not exist or the password was invalid returns Null Null and False"""

    class Arguments:
        username = String(required=True)
        password = String(required=True)

    access_token = String()
    refresh_token = String()
    ok = Boolean()

    @classmethod
    def mutate(cls, _, info, username, password):
        if not (AdminModel.objects(username=username) and check_password_hash(
                AdminModel.objects.get(username=username).password, password)):
            return Auth(ok=False)
        else:
            return Auth(access_token=create_access_token(username, user_claims=admin_claim),
                        refresh_token=create_refresh_token(username, user_claims=admin_claim),
                        ok=True)


class Refresh(Mutation):
    """Refresh a user's access token.
       Parameter: refreshToken, String, valid jwt refresh token.
       if successful return a new jwt access token for the owner of the refresh token. this invalidates old access tokens.
       if unsuccessful because the refresh token was invalid returns Null
    """

    class Arguments(object):
        refresh_token = String()

    new_token = String()

    @classmethod
    @mutation_jwt_refresh_token_required
    def mutate(cls, info):
        current_user = get_jwt_identity()
        claim = get_jwt_claims()
        if claim == admin_claim:
            return Refresh(new_token=create_access_token(identity=current_user, user_claims=admin_claim))
        else:
            return Refresh(new_token=None)


class CreateCode(Mutation):
    """Create an account promotion code.
       Parameter: token, String, valid jwt access token with the admin claim
       returns a code and True if successful
       returns Null and false if token does not have admin claim
       returns Null and empty value for ok if token is invalid
       the created code is a random 5-character string """

    class Arguments:
        token = String(required=True)

    ok = ProtectedBool()
    code = ProtectedString()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info):
        if get_jwt_claims() == admin_claim:
            letters = string.ascii_lowercase
            # generate random code
            code_string = ''.join(random.choice(letters) for i in range(5))
            # if the generated code already exists generate a new one
            while CodeModel.objects(code=code_string):
                code_string = ''.join(random.choice(letters) for i in range(5))
            code = CodeModel(code=code_string)
            code.save()
            return CreateCode(ok=BooleanField(boolean=True), code=StringField(string=code_string))
        else:
            return CreateCode(ok=BooleanField(boolean=False), code=None)


class DemoteUser(Mutation):
    """Remove a user's producer status.
       Parameter: token, String, valid jwt access token with the admin claim
                  username, String, name of the user you want to demote
        returns the updated user object and True if successful
        returns Null and False if the user did not exist or the token does not have the admin claim
        returns Null and an empty value for ok if the token was invalid
    """

    class Arguments:
        username = String(required=True)
        token = String(required=True)

    ok = ProtectedBool()
    user = Field(User)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, username):
        if get_jwt_claims() == admin_claim:
            if UserModel.objects(username=username):
                user = UserModel.objects.get(username=username)
                user.update(set__producer=False)
                user.save()
                user = UserModel.objects.get(username=username)
                return DemoteUser(ok=BooleanField(boolean=True), user=user)
            else:
                return DemoteUser(ok=BooleanField(boolean=False), user=None)
        else:
            return DemoteUser(ok=BooleanField(boolean=False), user=None)


class DeleteUser(Mutation):
    """Delete a user account
       Parameters: token, String, valid jwt access token with the admin claim
                   username, String, name of the account you want to delete
        returns True if successful
        returns False if token does not have the admin claim
        returns empty value if token was invalid
        successful if the user does not exist
       NOTE: also deletes the user's:
            owned tours
            checkpoints associated with the tours
            answers associated with the questions among the checkpoints
            answers given by the user to other questions
            favourites
        all of this is enforced in data models by the reverse_delete_rule on reference fields
    """

    class Arguments:
        username = String(required=True)
        token = String(required=True)

    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, username):
        if get_jwt_claims() == admin_claim:
            if UserModel.objects(username=username):
                user = UserModel.objects.get(username=username)
                user.delete()
            return DeleteUser(ok=BooleanField(boolean=True))

        else:
            return DeleteUser(ok=BooleanField(boolean=False))


class DenyReview(Mutation):
    """  Deny a tour that has been submitted for review.
         Parameters: token, String, valid jwt access token with the admin claim
                     tourId, String, document id of the tour
         returns the updated tour object and True if successful
         returns Null and False if tour does not exist or token does not have admin claim
         returns Null and empty value if token was invalid
         sets the tours status field back to private
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)

    ok = Field(ProtectedBool)
    tour = Field(Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        if get_jwt_claims() == admin_claim:
            if TourModel.objects(id=tour_id):
                tour = TourModel.objects.get(id=tour_id)
                tour.update(set__status='private')
                tour.save()
                tour.reload()
                return DenyReview(ok=BooleanField(boolean=True), tour=tour)
            else:
                return DenyReview(ok=BooleanField(boolean=False), tour=None)
        else:
            return DenyReview(ok=BooleanField(boolean=False), tour=None)


class AcceptReview(Mutation):
    """  Accept a tour that has been submitted for review.
         Parameters: token, String, valid jwt access token with the admin claim
                     tourId, String, document id of the tour
         returns the updated tour object and True if successful
         returns Null and False if tour does not exist or token does not have admin claim
         returns Null and empty value if token was invalid
         sets the tours status field to featured
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)

    ok = Field(ProtectedBool)
    tour = Field(Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        if get_jwt_claims() == admin_claim:
            if TourModel.objects(id=tour_id):
                tour = TourModel.objects.get(id=tour_id)
                featured_tour = TourModel(owner=UserModel.objects.get(username=get_jwt_identity()),
                                          status='featured',
                                          difficulty=tour.difficulty,
                                          name=tour.name,
                                          description=tour.description,
                                          session_id=tour.session_id,
                                          search_id=tour.search_id + str(datetime.datetime.now()),
                                          current_checkpoints=tour.current_checkpoints)
                featured_tour.save()
                featured_tour.reload()
                print("out")
                for checkpoint in CheckpointModel.objects(tour=tour):
                    print("in")
                    cp = deepcopy(checkpoint)
                    cp.tour = featured_tour
                    cp.id = None
                    cp.save()
                    cp.reload()

                return AcceptReview(ok=BooleanField(boolean=True), tour=featured_tour)
            else:
                return AcceptReview(ok=BooleanField(boolean=False), tour=None)
        else:
            return AcceptReview(ok=BooleanField(boolean=False), tour=None)


class ReadFeedback(Mutation):
    """Read App Feedback.
       Parameter: token, String, valid jwt access token with the admin claim
                  feedback, String, object id of the feedback to be read
        returns True if successful
        returns False if token does not have admin claim or feedback object does not exist
        returns empty value if token was invalid
        sets the feedback's read field to True
        works on feedback that has already been read
    """

    class Arguments:
        token = String(required=True)
        feedback_id = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, feedback_id):
        if get_jwt_claims() == admin_claim:
            if not AppFeedbackModel.objects(id=feedback_id):
                return ReadFeedback(ok=BooleanField(boolean=False))
            else:
                feedback = AppFeedbackModel.objects.get(id=feedback_id)
                feedback.update(set__read=True)
                feedback.save()
                return ReadFeedback(ok=BooleanField(boolean=True))
        else:
            return ReadFeedback(ok=BooleanField(boolean=False))


class CreateBadge(Mutation):
    """
        Create a new Badge that Users can earn.
        Parameters:
                token, String, valid jwt access token of an admin
                name, String, name of the badge
                badge_id, String, unique ID of the badge
                icon, Upload, expects a jpeg image. used as icon for the badge
                profile_picture, Upload, expects a jpeg image, the profile pictures users can unlock with the badge
                description, String, description text of the badge
                cost, Int, number of points needed to receive the badge
        if successful returns the new badge object and True
        if unsuccessful because token was invalid returns an empty value for ok
        if unsuccessful because token did not possess admin claim or because badge id was taken returns Null and False
    """

    class Arguments:
        token = String(required=True)
        name = String(required=True)
        badge_id = String(required=True)
        icon = Upload(required=True)
        profile_picture = Upload(required=True)
        description = String(required=True)
        cost = Int(required=True)

    ok = Field(ProtectedBool)
    badge = Field(Badge)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, name, badge_id, icon, description, cost, profile_picture):
        # ensure caller is admin
        if get_jwt_claims() == admin_claim:
            # ensure badge id is unique
            if not BadgeModel.objects(id=badge_id):
                pic = ProfilePictureModel(locked=True)
                pic.picture.put(profile_picture, content_type='image/jpeg')
                pic.save()
                pic.reload()
                badge = BadgeModel(id=badge_id, name=name, description=description, cost=cost, unlocked_picture=pic)
                badge.picture.put(icon, content_type='image/jpeg')
                badge.save()
                badge.reload()
                # add badge to the progress dict of all users.
                for user in UserModel.objects.all():
                    badges = user.badge_progress
                    badges[badge_id] = 0
                    user.update(set__badge_progress=badges)
                    user.save()
                return CreateBadge(badge=badge, ok=BooleanField(boolean=True))
            else:
                return CreateBadge(badge=None, ok=BooleanField(boolean=False))
        else:
            return CreateBadge(badge=None, ok=BooleanField(boolean=False))


class CreateProfilePicture(Mutation):
    """
        create a new profile picture for users to choose.
        Parameters:
            token, String, valid jwt access token of an admin
            picture, Upload, the profile picture in jpeg format
        if successful returns True
        if unsuccessful because token was invalid returns empty value
        if unsuccessful because token did not belong to admin returns False
    """

    class Arguments:
        token = String(required=True)
        picture = Upload(required=True)

    ok = Field(ProtectedBool)
    picture = Field(lambda: ProfilePicture)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, picture):
        if not get_jwt_claims() == admin_claim:
            return CreateProfilePicture(ok=BooleanField(boolean=False), picture=None)
        # create document
        pic = ProfilePictureModel()
        # pass data to the FileField
        pic.picture.put(picture, content_type='image/jpeg')
        pic.save()
        return CreateProfilePicture(ok=BooleanField(boolean=True), picture=pic)


class CreatePicture(Mutation):
    class Arguments:
        token = String(required=True)
        picture = Upload(required=True)
        description = String()

    ok = Field(ProtectedBool)
    picture = Field(lambda: Picture)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, picture, description=None):
        if not get_jwt_claims() == admin_claim:
            return CreatePicture(ok=BooleanField(boolean=False), picture=None)
        # create document
        pic = PictureModel(description=description)
        # pass data to the FileField
        pic.picture.put(picture, content_type='image/jpeg')
        pic.save()
        return CreatePicture(ok=BooleanField(boolean=True), picture=pic)


class UpdateBadge(Mutation):
    """
        Updates a Badge.
        Parameters:
            token, String, valid jwt access token with admin claim
            badge_id, String, id of the badge to edit
            icon, Upload, image in jpeg format
            profile_picture, Upload, image in jpeg format
            name, String, new name for the badge
            description, String, new description for the Badge
            cost, Int, new cost of the Badge
            new_id, String, a new id for the badge
        if successful returns the updated badge and true
        if unsuccessful because the token is invalid returns empty value for ok
        returns Null and False if unsuccessful because:
            badge with badge_id does not exist
            token does not belong to admin
            new_id is already in use
    """

    class Arguments:
        badge_id = String(required=True)
        token = String(required=True)
        icon = Upload()
        profile_picture = Upload()
        name = String()
        description = String()
        cost = Int()
        new_id = String()

    ok = Field(ProtectedBool)
    badge = Field(lambda: Badge)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, badge_id, **kwargs):
        # assert caller is admin
        if not get_jwt_claims() == admin_claim:
            return UpdateBadge(badge=None, ok=BooleanField(boolean=False))
        # assert badge exists
        if not BadgeModel.objects(id=badge_id):
            return UpdateBadge(badge=None, ok=BooleanField(boolean=False))
        # get badge to modify
        badge = BadgeModel.objects.get(id=badge_id)
        # get optional parameters
        icon = kwargs.get('picture', None)
        name = kwargs.get('name', None)
        description = kwargs.get('description', None)
        cost = kwargs.get('cost', None)
        new_id = kwargs.get('new_id', None)
        profile_picture = kwargs.get('profile_picture', None)
        if new_id is not None:
            # ensure new badge id is also unique
            if not BadgeModel.objects(id=new_id):
                badge.update(set__id=new_id)
            else:
                return UpdateBadge(badge=None, ok=BooleanField(boolean=False))
        if name is not None:
            badge.update(set__name=name)
        if cost is not None:
            badge.update(set__cost=cost)
        if description is not None:
            badge.update(set__description=description)
        if icon is not None:
            badge.picture.replace(icon, content_type='image/jpeg')
        if profile_picture is not None:
            pic = badge.unlocked_picture
            pic.picture.replace(profile_picture, content_type='image/jpeg')
            pic.save()
            pic.reload()
        badge.save()
        # reload so updated object is returned
        badge.reload()
        return UpdateBadge(badge=badge, ok=BooleanField(boolean=True))


class UpdatePicture(Mutation):
    """
        Updates a Picture.
        Parameters:
            token, String, valid jwt access token with admin claim
            picture_id, String, id of the picture to edit
            picture, Upload, image in jpeg format
            description, String, new description for the picture

        if successful returns the updated picture and true
        if unsuccessful because the token is invalid returns empty value for ok
        returns Null and False if unsuccessful because:
            picture with picture_id does not exist
            token does not belong to admin
    """

    class Arguments:
        picture_id = String(required=True)
        token = String(required=True)
        picture = Upload()
        description = String()

    ok = Field(ProtectedBool)
    picture = Field(lambda: Picture)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, picture_id, **kwargs):
        # assert caller is admin
        if not get_jwt_claims() == admin_claim:
            return UpdatePicture(picture=None, ok=BooleanField(boolean=False))
        # assert picture exists
        if not PictureModel.objects(id=picture_id):
            return UpdatePicture(picture=None, ok=BooleanField(boolean=False))
        # get object to modify
        picture_object = PictureModel.objects.get(id=picture_id)
        # get optional parameters
        picture = kwargs.get('picture', None)
        description = kwargs.get('description', None)

        if description is not None:
            picture_object.update(set__description=description)
        if picture is not None:
            picture_object.picture.replace(picture, content_type='image/jpeg')
        picture_object.save()
        # reload so updated object is returned
        picture_object.reload()
        return UpdatePicture(picture=picture_object, ok=BooleanField(boolean=True))


class UpdateProfilePicture(Mutation):
    """
        Updates a profile picture
        Parameters:
            token, String, valid jwt access token with admin claim
            picture_id, String, id of the profile picture to edit
            picture, Upload, image in jpeg format

        if successful returns the updated profile picture and true
        if unsuccessful because the token is invalid returns empty value for ok
        returns Null and False if unsuccessful because:
            profile picture with picture_id does not exist
            token does not belong to admin
    """

    class Arguments:
        picture_id = String(required=True)
        token = String(required=True)
        picture = Upload()

    ok = Field(ProtectedBool)
    picture = Field(lambda: ProfilePicture)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, picture_id, picture):
        # assert caller is admin
        if not get_jwt_claims() == admin_claim:
            return UpdateProfilePicture(picture=None, ok=BooleanField(boolean=False))
        # assert object exists
        if not ProfilePictureModel.objects(id=picture_id):
            return UpdateProfilePicture(picture=None, ok=BooleanField(boolean=False))
        # get object to modify
        profile_picture = ProfilePictureModel.objects.get(id=picture_id)
        profile_picture.picture.replace(picture, content_type='image/jpeg')
        profile_picture.save()
        # reload so updated object is returned
        profile_picture.reload()
        return UpdateProfilePicture(picture=profile_picture, ok=BooleanField(boolean=True))


class EditCheckpoint(Mutation):
    """
        Allows admins to edit arbitrary checkpoints e.g. to correct spelling mistakes in tours submitted for review
        Parameters:
            token, String, required, valid jwt of an admin
            checkpoint_id, String, required, id of the checkpoint to be edited
            text, String, optional, description text of the checkpoint
            object_id, optional, object_id of a museum object to update the reference of an ObjectCheckpoint
            picture_id, optional, id of a Picture to update the reference of a PictureCheckpoint
            question, String, text to update the question text of a Question or MCQuestion
            linked_objects, List of String, list of object ids to update the references in a Question or MCQuestion
            possible_answers, List of String, update the possible answers of a MCQuestion
            correct_answers, List of Int, update the correct answers of a MCQuestion
            max_choices, Int, new max choices value for a MCQuestion
        if successful returns the updated checkpoint and True
        if unsuccessful because the token was invalid returns emtpy value for ok
        returns Null and False if unsuccessful because
            token did not belong to admin
            checkpoint with checkpoint_id does not exist
            given a picture_id or object_id or linked_objects and the referenced object did not exist

    """

    class Arguments:
        token = String(required=True)
        checkpoint_id = String(required=True)
        text = String()
        object_id = String()
        picture_id = String()
        question = String()
        linked_objects = List(String)
        possible_answers = List(String)
        correct_answers = List(Int)
        max_choices = Int()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    checkpoint = Field(lambda: CheckpointUnion)
    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, checkpoint_id, **kwargs):
        # assert caller is admin
        if not get_jwt_claims() == admin_claim:
            return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # assert checkpoint exists
        if not CheckpointModel.objects(id=checkpoint_id):
            return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # get checkpoint object
        checkpoint = CheckpointModel.objects.get(id=checkpoint_id)
        # get all the optional arguments
        text = kwargs.get('text', None)
        object_id = kwargs.get('object_id', None)
        picture_id = kwargs.get('picture_id', None)
        question = kwargs.get('question', None)
        linked_objects = kwargs.get('linked_objects', None)
        possible_answers = kwargs.get('possible_answers', None)
        correct_answers = kwargs.get('correct_answers', None)
        max_choices = kwargs.get('max_choices', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        # handle fields that all checkpoints share first
        if text is not None:
            checkpoint.update(set__text=text)
        if show_text != checkpoint.show_text:
            checkpoint.update(set__show_text=show_text)
        if show_picture != checkpoint.show_picture:
            checkpoint.update(set__show_picture=show_picture)
        if show_details != checkpoint.show_details:
            checkpoint.update(set__show_details=show_details)
        checkpoint.save()
        checkpoint.reload()
        # treat checkpoint update depending on the type of the checkpoint
        if isinstance(checkpoint, ObjectCheckpointModel):
            # assert new object exists
            if object_id is not None:
                if not MuseumObjectModel.objects(object_id=object_id):
                    return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                checkpoint.update(set__museum_object=museum_object)
            checkpoint.save()
            checkpoint.reload()
            return EditCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))
        elif isinstance(checkpoint, PictureCheckpointModel):
            # assert new picture exists
            if picture_id is not None:
                if not PictureModel.objects(id=picture_id):
                    return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
                pic = PictureModel.objects.get(id=picture_id)
                checkpoint.update(set__picture=pic)
            if text is not None:
                checkpoint.update(set__text=text)
            checkpoint.save()
            checkpoint.reload()
            return EditCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))
        # check MCQuestion first because a MCQuestion would pass the check for isinstance(checkpoint,QuestionModel)
        elif isinstance(checkpoint, MCQuestionModel):
            # question text is inherited from question
            if question is not None:
                checkpoint.update(set__question=question)
            if possible_answers is not None:
                checkpoint.update(set__possible_answers=possible_answers)
            if correct_answers is not None:
                checkpoint.update(set__correct_answers=correct_answers)
            if max_choices is not None:
                checkpoint.update(set__max_choices=max_choices)
            # linked objects are also inherited from question
            if linked_objects is not None:
                new_links = []
                for oid in linked_objects:
                    if not MuseumObjectModel.objects(object_id=oid):
                        return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
                    else:
                        new_links.append(MuseumObjectModel.objects.get(object_id=oid))
                checkpoint.update(set__linked_objects=new_links)
            checkpoint.save()
            checkpoint.reload()
            return EditCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))
        elif isinstance(checkpoint, QuestionModel):
            if question is not None:
                checkpoint.update(set__question=question)
            if linked_objects is not None:
                new_links = []
                for oid in linked_objects:
                    if not MuseumObjectModel.objects(object_id=oid):
                        return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
                    else:
                        new_links.append(MuseumObjectModel.objects.get(object_id=oid))
                checkpoint.update(set__linked_objects=new_links)
            checkpoint.save()
            checkpoint.reload()
            return EditCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))
        # last remaining choice is the checkpoint was a simple text checkpoint
        else:
            return EditCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))


class Mutation(ObjectType):
    create_admin = CreateAdmin.Field()
    auth = Auth.Field()
    refresh = Refresh.Field()
    change_password = ChangePassword.Field()
    create_museum_object = CreateMuseumObject.Field()
    update_museum_object = UpdateMuseumObject.Field()
    delete_museum_object = DeleteMuseumObject.Field()
    create_code = CreateCode.Field()
    demote_user = DemoteUser.Field()
    delete_user = DeleteUser.Field()
    deny_review = DenyReview.Field()
    accept_review = AcceptReview.Field()
    read_feedback = ReadFeedback.Field()
    create_badge = CreateBadge.Field()
    create_picture = CreatePicture.Field()
    create_profile_picture = CreateProfilePicture.Field()
    update_badge = UpdateBadge.Field()
    update_picture = UpdatePicture.Field()
    update_profile_picture = UpdateProfilePicture.Field()
    edit_checkpoint = EditCheckpoint.Field()
