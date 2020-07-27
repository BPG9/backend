import datetime
from flask_graphql_auth import create_access_token, create_refresh_token, mutation_jwt_refresh_token_required, \
    get_jwt_identity, mutation_jwt_required
from graphene import ObjectType, List, Mutation, String, Field, Boolean, Int
from werkzeug.security import generate_password_hash, check_password_hash
from .ProtectedFields import ProtectedBool, BooleanField, ProtectedString, StringField
from app.Fields import User, AppFeedback, Favourites, Tour, Question, Answer, TourFeedback, MCQuestion, \
    MCAnswer, Checkpoint, PictureCheckpoint, ObjectCheckpoint, CheckpointUnion
from models.User import User as UserModel
from models.Code import Code as CodeModel
from models.Tour import Tour as TourModel
from models.Answer import Answer as AnswerModel
from models.Question import Question as QuestionModel
from models.Favourites import Favourites as FavouritesModel
from models.MuseumObject import MuseumObject as MuseumObjectModel
from models.AppFeedback import AppFeedback as AppFeedbackModel
from models.TourFeedback import TourFeedback as TourFeedbackModel
from models.Picture import Picture as PictureModel
from models.Badge import Badge as BadgeModel
from models.MultipleChoiceQuestion import MultipleChoiceQuestion as MCQuestionModel
from models.MultipleChoiceAnswer import MultipleChoiceAnswer as MCAnswerModel
from models.ProfilePicture import ProfilePicture as ProfilePictureModel
from models.Checkpoint import Checkpoint as CheckpointModel
from models.PictureCheckpoint import PictureCheckpoint as PictureCheckpointModel
from models.ObjectCheckpoint import ObjectCheckpoint as ObjectCheckpointModel

"""
These are the mutations available in the App API. 
Tasks: - account creation 
       - login 
       - account management ( change password, delete account) 
       - manage favourite objects and tours 
       - provide feedback for the app 
       - created tours and questions 
       - set session ids 
       - join tours using the session id 
       - create and submit answers 
       - provide feedback for tours 
       
login returns access and refresh token. all other requests require a valid access token.  
"""


class CreateUser(Mutation):
    """Create a user account.
       Parameters: username, String, name of the account. has to be unique
                   password, String, password, no requirements, saved as a hash
       if successful returns the created user and ok=True
       returns Null and False if the username is already taken
    """

    class Arguments:
        username = String(required=True)
        password = String(required=True)

    user = Field(lambda: User)
    ok = Boolean()

    def mutate(self, info, username, password):
        # ensure there is no user with this name
        # making this check here prevents a mongoengine error but uniqueness of the name is also enforced in the model
        if not UserModel.objects(username=username):
            # password is hashed before storing
            user = UserModel(username=username, password=generate_password_hash(password))
            user.save()
            return CreateUser(user=user, ok=True)
        else:
            return CreateUser(user=None, ok=False)


class AddBadgeProgress(Mutation):
    """Award a user a new achievement badge.
            Parameters: token, String, valid jwt access token of a user
                        badge_id, String, the internal id of the badge to be awarded
            if successful returns the updated user object and ok=True
            if unsuccessful because the token was invalid returns empty value for ok
            if unsuccessful because of invalid badge id returns Null and False
            is successful if called when the user already has unlocked the badge.
        """

    class Arguments:
        token = String()
        badge_id = String()
        progress = Int()

    ok = Field(ProtectedBool)
    user = Field(lambda: User)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, badge_id, progress):
        # get the user object to reference
        username = get_jwt_identity()
        user = UserModel.objects.get(username=username)
        # assert the badge exists
        if not BadgeModel.objects(id=badge_id):
            return AddBadgeProgress(user=None, ok=BooleanField(boolean=False))
        else:
            # check the user's current progress towards the badge
            badge = BadgeModel.objects.get(id=badge_id)
            user_progress = user.badge_progress
            current = user_progress[badge_id]
            # if the user progressed past the cost of the badge set the current progress to the badge cost
            if current + progress >= badge.cost:
                user_progress[badge_id] = badge.cost
                # award the user the badge if they do not already own it
                if badge not in user.badges:
                    badges = user.badges
                    badges.append(badge)
                    user.update(set__badges=badges)
                    user.save()
                    user.reload()
            else:
                user_progress[badge_id] = current + progress
            user.update(set__badge_progress=user_progress)
            user.save()
            return AddBadgeProgress(user=user, ok=BooleanField(boolean=True))


class PromoteUser(Mutation):
    """Use a promotion code to promote a user's account to producer status.
       Parameters: token, String, valid jwt access token of a user
                   code, String, 5 character string used as promotion password
        if successful returns the updated user object and ok=True. also deletes the used code from the database
        if unsuccessful because the code was invalid returns Null and False
        if unsuccessful because the token was invalid returns empty value for ok
        """

    class Arguments:
        token = String()
        code = String()

    ok = Field(ProtectedBool)
    user = Field(User)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, code):
        username = get_jwt_identity()
        # assert the code is valid
        if not CodeModel.objects(code=code):
            return PromoteUser(ok=BooleanField(boolean=False), user=None)
        else:
            # get the code object in the database
            code_doc = CodeModel.objects.get(code=code)
            # delete code as they are one time use
            code_doc.delete()
            # get the user object
            user = UserModel.objects.get(username=username)
            # give the user producer access
            user.update(set__producer=True)
            user.save()
            user.reload()
            return PromoteUser(ok=BooleanField(boolean=True), user=user)


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
        user = UserModel.objects.get(username=username)
        # password is hashed before saving
        user.update(set__password=generate_password_hash(password))
        user.save()
        return ChangePassword(ok=BooleanField(boolean=True))


class ChangeUsername(Mutation):
    """
        Change the account name of the current user. New username also has to be unique.
        Parameters:
            token: String, jwt access token
            username: String, new user name
        returns the updated user, a new refresh token bound to the new identity and True if successful
        returns Null and False if username already exists
        returns empty value for ok if token is invalid
    """

    class Arguments:
        token = String(required=True)
        username = String(required=True)

    ok = Field(ProtectedBool)
    user = Field(lambda: User)
    refresh_token = String()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, username):
        if UserModel.objects(username=username):
            return ChangeUsername(ok=BooleanField(boolean=False), user=None, refresh_token=None)
        user = UserModel.objects.get(username=get_jwt_identity())
        user.update(set__username=username)
        user.save()
        user.reload()
        return ChangeUsername(user=user, ok=BooleanField(boolean=True), refresh_token=create_refresh_token(username))


class Auth(Mutation):
    """Login. Create a session and jwt access and refresh tokens.
       Parameters: username, String, the username of the account you wish to log in to
                   password, String, the password of the account. password is hashed and compared to the saved hash.
        if successful returns a jwt accessToken (String), a jwt refresh token (String) and True
        if unsuccessful because the user does not exist or the password was invalid returns Null Null and False"""

    class Arguments:
        username = String(required=True)
        password = String(required=True)

    access_token = String()
    refresh_token = String()
    ok = Boolean()

    @classmethod
    def mutate(cls, _, info, username, password):
        # assert the login data is valid
        if not (UserModel.objects(username=username) and check_password_hash(
                UserModel.objects.get(username=username).password, password)):
            return Auth(ok=False, access_token=None, refresh_token=None)
        else:
            # if login data was valid create and return jwt access and refresh tokens
            return Auth(access_token=create_access_token(username), refresh_token=create_refresh_token(username),
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
        return Refresh(new_token=create_access_token(identity=current_user))


class ChooseProfilePicture(Mutation):
    """
        Allows a user to choose a profile picture from the pictures available on the server
        Parameters:
                token, String, valid jwt access token
                picture_id, String, valid object id of the ProfilePicture object on the server
        if successful returns true
        if unsuccessful because the picture id was invalid or picture was not unlocked returns False
        if unsuccessful because the token was invalid returns empty value
        is successful if chosen picture is current picture
    """

    class Arguments:
        token = String(required=True)
        picture_id = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, picture_id):
        user = UserModel.objects.get(username=get_jwt_identity())
        if not ProfilePictureModel.objects(id=picture_id):
            return ChooseProfilePicture(ok=BooleanField(boolean=False))
        else:
            picture = ProfilePictureModel.objects.get(id=picture_id)
            if not picture.locked:
                user.update(set__profile_picture=picture)
                user.save()
                user.reload()
                return ChooseProfilePicture(ok=BooleanField(boolean=True))
            else:
                pics = []
                for badge in user.badges:
                    pics.append(badge.unlocked_picture)
                if picture in pics:
                    user.update(set__profile_picture=picture)
                    user.save()
                    user.reload()
                    return ChooseProfilePicture(ok=BooleanField(boolean=True))
                else:
                    return ChooseProfilePicture(ok=BooleanField(boolean=False))


class DeleteAccount(Mutation):
    """Delete a user account.
       Deleting an account will also delete any tours, questions, answers and favourites created by this user.
       Parameter: token, String, valid jwt access token of the account to be deleted.
       returns True if successful
       returns Null if token was invalid
       returns True if user does not exist
       NOTE: also deletes the user's:
            owned tours
            checkpoints associated with the tours
            answers associated with the questions among the checkpoints
            answers given by the user to other questions
            favourites
        all of this is enforced in data models by the reverse_delete_rule on reference fields
       """

    class Arguments:
        token = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info):
        username = get_jwt_identity()
        if UserModel.objects(username=username):
            user = UserModel.objects.get(username=username)
            user.delete()
        return DeleteAccount(ok=BooleanField(boolean=True))


class SendFeedback(Mutation):
    """Send Feedback about the App to the admins. Feedback is anonymous.
        Feedback consists of a rating on a scale from 1-5 and a text review.
        If the supplied value for rating is outside of the range it is force to be in it.
        Parameters: token, String, valid jwt access token of a user
                    rating, Int, rating on a scale of 1-5
                    review, String, text review / feedback
        returns the feedback object and True if successful
        returns Null and an empty value for ok if the token was invalid
    """

    class Arguments:
        token = String(required=True)
        review = String(required=True)
        rating = Int(required=True)

    ok = Field(ProtectedBool)
    feedback = Field(lambda: AppFeedback)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, review, rating):
        # assert that the rating is on the 1-5 scale
        if rating < 1:
            rating = 1
        elif rating > 5:
            rating = 5
        feedback = AppFeedbackModel(review=review, rating=rating)
        feedback.save()
        # after feedback has been created it will be available to read for admins
        return SendFeedback(ok=BooleanField(boolean=True), feedback=feedback)


class AddFavouriteObject(Mutation):
    """Add an object to a user's favourites.
       Parameters: token, String, valid jwt access token of a user
                   objectId, String, inventory ID of the object to be added
       returns the list of favourites and True if successful
       returns Null and False if the object does not exist
       returns Null and an empty value for ok if the token was invalid """

    class Arguments:
        token = String(required=True)
        object_id = String(required=True)

    ok = Field(ProtectedBool)
    favourites = Field(lambda: Favourites)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, object_id):
        user = UserModel.objects.get(username=get_jwt_identity())
        # assert the object exists
        if MuseumObjectModel.objects(object_id=object_id):
            museum_object = MuseumObjectModel.objects.get(object_id=object_id)
            # check if the user already has a favourites object
            if FavouritesModel.objects(user=user):
                favourites = FavouritesModel.objects.get(user=user)
                # check if user already has other favourite objects
                if favourites.favourite_objects:
                    objects = favourites.favourite_objects
                    # add current object to the list if it is not in it already
                    if museum_object not in objects:
                        objects.append(museum_object)
                        favourites.update(set__favourite_objects=objects)
                        favourites.save()
                # if the user does not already have a list of favourite objects make one and add the current object
                else:
                    objects = [museum_object]
                    favourites.update(set__favourite_objects=objects)
                    favourites.save()
                favourites.reload()
                return AddFavouriteObject(ok=BooleanField(boolean=True), favourites=favourites)
            # if the user does not currently have a Favourites object create one and add the current object to it
            else:
                objects = [museum_object]
                favourites = FavouritesModel(user=user, favourite_objects=objects)
                favourites.save()
                return AddFavouriteObject(ok=BooleanField(boolean=True), favourites=favourites)
        else:
            return AddFavouriteObject(ok=BooleanField(boolean=False), favourites=None)


class RemoveFavouriteObject(Mutation):
    """Remove an object from a user's list of favourite objects.
      Parameters: token, String, valid jwt access token of a user
                   objectId, String, inventory ID of the object to be removed
       returns the updated list of favourites and True if successful
       returns None and False if the user does not have any favourites or object does not exist
       returns None and an empty value for ok if the token is invalid
       This operation works and is successful if the object supplied is not part of the user's favourites.
    """

    class Arguments:
        token = String(required=True)
        object_id = String(required=True)

    ok = Field(ProtectedBool)
    favourites = Field(lambda: Favourites)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, object_id):
        # get the user object to reference
        user = UserModel.objects.get(username=get_jwt_identity())
        # get the user's favourites
        if FavouritesModel.objects(user=user):
            favourites = FavouritesModel.objects.get(user=user)
            # assert the MuseumObject exists
            if MuseumObjectModel.objects(object_id=object_id):
                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                # if the object is in the user's favourites remove it
                if museum_object in favourites.favourite_objects:
                    objects = favourites.favourite_objects
                    objects.remove(museum_object)
                    favourites.update(set__favourite_objects=objects)
                    favourites.save()
                    favourites.reload()
                # operation if successful is the object was already not part of the user's favourites
                return RemoveFavouriteObject(ok=BooleanField(boolean=True), favourites=favourites)
        return RemoveFavouriteObject(ok=BooleanField(boolean=False), favourites=None)


class AddFavouriteTour(Mutation):
    """Add a tour to a user's list of favourite tours.
      Parameters: token, String, valid jwt access token of a user
                   tourId, String, document ID of the tour to be added
      returns the updated list of favourites and True if successful.
      returns Null and False if the tour does not exits
      returns Null and an empty value for ok is the token is invalid
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)

    ok = Field(ProtectedBool)
    favourites = Field(lambda: Favourites)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        # get user object to reference
        user = UserModel.objects.get(username=get_jwt_identity())
        # assert that tour exists and get the object to reference
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            # get the users current favourites
            if FavouritesModel.objects(user=user):
                favourites = FavouritesModel.objects.get(user=user)
                if favourites.favourite_tours:
                    tours = favourites.favourite_tours
                    # if the tour is not yet in the user's favourite tours add it
                    if tour not in tours:
                        tours.append(tour)
                        favourites.update(set__favourite_tours=tours)
                        favourites.save()
                # if the user did not have any favourite tours before create a new list and add the tour to it
                else:
                    tours = [tour]
                    favourites.update(set__favourite_tours=tours)
                    favourites.save()
                favourites.reload()
                return AddFavouriteTour(ok=BooleanField(boolean=True), favourites=favourites)
            # if the user did not have any favourites before create a new object and add the tour to favourite tours
            else:
                tours = [tour]
                favourites = FavouritesModel(user=user, favourite_tours=tours)
                favourites.save()
                return AddFavouriteTour(ok=BooleanField(boolean=True), favourites=favourites)
        else:
            return AddFavouriteTour(ok=BooleanField(boolean=False), favourites=None)


class RemoveFavouriteTour(Mutation):
    """Remove a tour to a user's list of favourite tours.
          Parameters: token, String, valid jwt access token of a user
                       tourId, String, document ID of the tour to be removed
          returns the updated list of favourites and True if successful.
          returns None and False if the user does not have any favourites or tour does not exist
          returns None and an empty value for ok if the token is invalid
       This operation works and is successful if the tour supplied is not part of the user's favourites.
        """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)

    ok = Field(ProtectedBool)
    favourites = Field(lambda: Favourites)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        # get user to reference
        user = UserModel.objects.get(username=get_jwt_identity())
        # get the user's favourites
        if FavouritesModel.objects(user=user):
            favourites = FavouritesModel.objects.get(user=user)
            # check if tour exists
            if TourModel.objects(id=tour_id):
                tour = TourModel.objects.get(id=tour_id)
                # check if tour is in the user's favourites. if it is remove it
                if tour in favourites.favourite_tours:
                    tours = favourites.favourite_tours
                    tours.remove(tour)
                    favourites.update(set__favourite_tours=tours)
                    favourites.save()
                    favourites.reload()
                # if the tour was not in the user's favourites the call is still successful
                return RemoveFavouriteTour(ok=BooleanField(boolean=True), favourites=favourites)
        return RemoveFavouriteTour(ok=BooleanField(boolean=False), favourites=None)


class CreateTour(Mutation):
    """ Create a tour
        Parameters: token, String, jwt access token of a user
                    name, String, name of the tour
                    session_id, Int, passcode used to join the tour
                    description, String, short description of the tour
                    difficulty, String, rating of difficulty on a scale of 1-5
                    search_id, String, id by which users can find the tour. has to be unique in the database
        can only be used by users whose 'producer' attribute is True
        if successful returns the created Tour object and "success"
        if unsuccessful because the owner of the token is not a producer returns Null and "user is not producer"
        if unsuccessful because the searchId is already taken returns Null and "search id already in use"
        if unsuccessful because the token is invalid returns an empty value for ok
    """

    class Arguments:
        token = String(required=True)
        name = String(required=True)
        session_id = Int(required=True)
        difficulty = Int(required=True)
        search_id = String(required=True)
        description = String()

    tour = Field(lambda: Tour)
    ok = Field(ProtectedString)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, name, session_id, difficulty, search_id, description=None):
        owner_name = get_jwt_identity()
        # get user object tot reference as owner
        if UserModel.objects(username=owner_name):
            owner = UserModel.objects.get(username=owner_name)
            # owner has to be producer to be allowed to create a tour
            if owner.producer:
                # owner is automatically the first member of the tour
                users = [owner]
                # ensure difficulty rating is on the scale
                if difficulty < 1:
                    difficulty = 1
                elif difficulty > 5:
                    difficulty = 5
                if not TourModel.objects(search_id=search_id):
                    tour = TourModel(owner=owner, name=name, users=users, session_id=session_id, difficulty=difficulty,
                                     description=description, search_id=search_id)
                    tour.save()
                    return CreateTour(tour=tour, ok=StringField(string="success"))
                else:
                    return CreateTour(tour=None, ok=StringField(string="search id already in use"))
        return CreateTour(tour=None, ok=StringField(string="User is not producer"))


class CreateCheckpoint(Mutation):
    """
        Creates a generic checkpoint i.e. a text-only checkpoint
        Parameters:
            token, String, valid jwt access token
            tour_id, String, object id of a valid tour
            text, String, additional optional description text for the checkpoint
            show_text: Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture: Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details: Boolean, optional, default False, indicates to the app if details should be shown
        caller has to be owner of tour
        if successful returns the created checkpoint and True
        if unsuccessful because the tour did not exist or the caller did not own the tour returns Null and False
        if unsuccessful because the token was invalid returns an empty value for ok
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)
        text = String()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    checkpoint = Field(lambda: Checkpoint)
    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, **kwargs):
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
        else:
            return CreateCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        user = UserModel.objects.get(username=get_jwt_identity())
        if not user == tour.owner:
            return CreateCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # add checkpoint to the end of the tour
        current_index = tour.current_checkpoints
        current_index += 1
        tour.update(set__current_checkpoints=current_index)
        tour.save()
        tour.reload()
        # handling optional parameters
        text = kwargs.get('text', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        # creating checkpoint
        checkpoint = CheckpointModel(tour=tour, index=current_index, text=text, show_text=show_text,
                                     show_picture=show_picture, show_details=show_details)
        checkpoint.save()
        checkpoint.reload()
        return CreateCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))


class CreatePictureCheckpoint(Mutation):
    """
        Creates a Picture Checkpoint
        Parameters:
            token, String, valid jwt access token
            tour_id, String, object id of a valid tour
            text, String, additional optional description text for the checkpoint
            show_text: Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture: Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details: Boolean, optional, default False, indicates to the app if details should be shown
            picture_id, String, optional, id of an existing picture in the database to turn into a checkpoint
            #picture, Upload, optional, image in png format to create a checkpoint with a new image
            #picture_description, String, optional, description of the uploaded picture (NOT of the checkpoint)
        caller has to be owner of tour
        if successful returns the created checkpoint and True
        if unsuccessful because the tour did not exist or the caller did not own the tour or the picture id was invalid
            returns Null and False
        if unsuccessful because the token was invalid returns an empty value for ok
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)
        picture_id = String()
        # picture = Upload()
        # picture_description = String()
        text = String()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    checkpoint = Field(lambda: PictureCheckpoint)
    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, **kwargs):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
        else:
            return CreatePictureCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # get user and assert user owns the tour
        user = UserModel.objects.get(username=get_jwt_identity())
        if not user == tour.owner:
            return CreatePictureCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # picture = kwargs.get('picture', None)
        # picture_description = kwargs.get('picture_description', None)

        # get optional arguments
        picture_id = kwargs.get('picture_id', None)
        text = kwargs.get('text', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        # add checkpoint to the end of the tour
        current_index = tour.current_checkpoints
        current_index += 1
        tour.update(set__current_checkpoints=current_index)
        tour.save()
        tour.reload()
        if picture_id is not None:
            if PictureModel(id=picture_id):
                pic = PictureModel.objects.get(id=picture_id)
                checkpoint = PictureCheckpointModel(picture=pic, tour=tour, text=text, index=current_index,
                                                    show_details=show_details, show_picture=show_picture,
                                                    show_text=show_text)
                checkpoint.save()
                return CreatePictureCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))
        return CreatePictureCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # if picture is not None:
        # x = PictureModel(description=picture_description)
        # x.picture.put(picture, content_type='image/png')
        # x.save()
        # checkpoint = PictureCheckpointModel(picture=x, tour=tour, text=text, index=current_index)
        # checkpoint.save()
        # return CreatePictureCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))


class CreateObjectCheckpoint(Mutation):
    """
        Creates a Checkpoint referencing an Object.
        Parameters:
            token, String, valid jwt access token of the tour owner
            tour_id, String, id of a tour to add the checkpoint to
            object_id, String, object_id of the object to reference
            text, String, additional optional description text for the checkpoint
            show_text: Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture: Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details: Boolean, optional, default False, indicates to the app if details should be shown
        if successful returns the created checkpoint and True
        if unsuccessful because the token was invalid returns an empty value for ok
        returns Null and False if unsuccessful because
            user did not own the tour
            tour reference did not exist
            referenced object did not exist
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)
        object_id = String(required=True)
        text = String()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    ok = Field(ProtectedBool)
    checkpoint = Field(lambda: ObjectCheckpoint)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, object_id, **kwargs):
        # get optional arguments
        text = kwargs.get('text', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
        else:
            return CreateObjectCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        user = UserModel.objects.get(username=get_jwt_identity())
        if not user == tour.owner:
            return CreateObjectCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        if not MuseumObjectModel.objects(object_id=object_id):
            return CreateObjectCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # add checkpoint to the end of the tour
        current_index = tour.current_checkpoints
        current_index += 1
        tour.update(set__current_checkpoints=current_index)
        tour.save()
        tour.reload()
        museum_object = MuseumObjectModel.objects.get(object_id=object_id)
        checkpoint = ObjectCheckpointModel(tour=tour, museum_object=museum_object, text=text, index=current_index,
                                           show_details=show_details, show_picture=show_picture, show_text=show_text)
        checkpoint.save()
        return CreateObjectCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))


class CreateAnswer(Mutation):
    """
        Creates an Answer to a regular text question
        Parameters:
            token, String, valid jwt access token
            answer, String, text answer to the question
            question, String, id of the question
        returns the answer and True if successful
        returns empty value because token was invalid
        returns Null and False if unsuccessful because
            user is not member of the tour the question is in
            question reference was invalid
    """

    class Arguments:
        token = String(required=True)
        answer = String(required=True)
        question_id = String(required=True)

    answer = Field(lambda: Answer)
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, answer, question_id):
        # get user object to reference
        username = get_jwt_identity()
        if UserModel.objects(username=username):
            user = UserModel.objects.get(username=username)
            # assert question exists
            if QuestionModel.objects(id=question_id):
                question = QuestionModel.objects.get(id=question_id)
            else:
                return CreateAnswer(answer=None, ok=BooleanField(boolean=False))
            # ensure user is member of the tour
            tour = question.tour
            if user not in tour.users:
                return CreateAnswer(answer=None, ok=BooleanField(boolean=False))
            # creating and submitting a new answer
            if not AnswerModel.objects(question=question, user=user):
                answer = AnswerModel(question=question, user=user, answer=answer)
                answer.save()
                return CreateAnswer(answer=answer, ok=BooleanField(boolean=True))
            # if the user previously answered the question update the answer
            else:
                prev = AnswerModel.objects.get(question=question, user=user)
                prev.update(set__answer=answer)
                prev.reload()
                return CreateAnswer(answer=prev, ok=BooleanField(boolean=True))
        else:
            return CreateAnswer(answer=None, ok=BooleanField(boolean=False))


class CreateMCAnswer(Mutation):
    """
        Creating and submitting a multiple choice answer. Answer may only be submitted once and is immediately evaluated
        Parameters:
            token, String, valid jwt access token
            question, id of a multiple choice question
            answer, List of Int, indices of the correct answers in the question.possible_answers
        if successful returns the answer, ok=True and the number of correct answers
        if unsuccessful because the token was invalid returns empty value for ok
        if unsuccessful because the question did not exist returns Null and False
        if unsuccessful because the number of submitted answers was too high returns Null False and -1 for correct
    """

    class Arguments:
        token = String(required=True)
        answer = List(of_type=Int, required=True)
        question_id = String(required=True)

    answer = Field(lambda: MCAnswer)
    correct = Int()
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, answer, question_id):
        # get user object to reference
        username = get_jwt_identity()
        if UserModel.objects(username=username):
            user = UserModel.objects.get(username=username)
            # assert question exists
            if MCQuestionModel.objects(id=question_id):
                question = MCQuestionModel.objects.get(id=question_id)
            else:
                return CreateAnswer(answer=None, ok=BooleanField(boolean=False), correct=0)
            # ensuring user is member of the tour
            tour = question.tour
            if user not in tour.users:
                return CreateAnswer(answer=None, ok=BooleanField(boolean=False), correct=0)
            # creating and submitting a new answer
            # if not MCAnswerModel.objects(question=question, user=user):
            # number of answers may not be more than permitted by the question
            # if len(answer) <= question.max_choices:
            correct = 0
            correct_answers = question.correct_answers
            for single_answer in answer:
                if single_answer in correct_answers:
                    correct += 1
            if not MCAnswerModel.objects(question=question, user=user):
                answer_ = MCAnswerModel(question=question, user=user, answer=answer)
            else:
                answer_ = MCAnswerModel.objects.get(question=question, user=user)
                answer_.update(set__answer=answer)
            answer_.save()
            answer_.reload()
            return CreateMCAnswer(answer=answer_, ok=BooleanField(boolean=True), correct=correct)
            # else:
            # return CreateMCAnswer(answer=None, ok=BooleanField(boolean=False), correct=-1)
        else:
            return CreateMCAnswer(answer=None, ok=BooleanField(boolean=False), correct=0)


class CreateQuestion(Mutation):
    """
        Creating text Question and adding it to the end of the tour
        Parameters:
            token, String, valid jwt access token
            question_text, String, the text of the question
            tour_id, String, id of the tour to add the checkpoint to
            linked_objects, List of String, list of object_id of objects the question references
            text, String, additional optional description text for the checkpoint
            show_text: Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture: Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details: Boolean, optional, default False, indicates to the app if details should be shown
        if successful returns the created question and ok=True
        if unsuccessful because the token was invalid returns empty value for ok
        returns Null and False if unsuccessful because
            tour did not exist
            user did not own the tour
            an object referenced in linked_objects did not exist
    """

    class Arguments:
        token = String(required=True)
        linked_objects = List(of_type=String)
        question_text = String(required=True)
        tour_id = String(required=True)
        text = String()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    question = Field(lambda: Question)
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, question_text, tour_id, **kwargs):
        # get optional arguments
        linked_objects = kwargs.get('linked_objects', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        text = kwargs.get('text', None)
        if linked_objects is None:
            linked_objects = []
        # get the current user object to check for permissions
        username = get_jwt_identity()
        if UserModel.objects(username=username):
            user = UserModel.objects.get(username=username)
            # assert that tour exists
            if TourModel.objects(id=tour_id):
                tour = TourModel.objects.get(id=tour_id)
                # assert user is owner of the tour
                if tour.owner == user:
                    # resolve references to linked objects if any are given:
                    links = []
                    if linked_objects:
                        for object_id in linked_objects:
                            if MuseumObjectModel.objects(object_id=object_id):
                                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                                links.append(museum_object)
                            else:
                                return CreateQuestion(question=None, ok=BooleanField(boolean=False))

                    # add checkpoint to the end of the tour
                    current_index = tour.current_checkpoints
                    current_index += 1
                    tour.update(set__current_checkpoints=current_index)
                    tour.save()
                    tour.reload()
                    question = QuestionModel(linked_objects=links,
                                             question=question_text, text=text, tour=tour, index=current_index,
                                             show_details=show_details, show_picture=show_picture, show_text=show_text)
                    question.save()
                    return CreateQuestion(question=question,
                                          ok=BooleanField(boolean=True))

        return CreateQuestion(question=None, ok=BooleanField(boolean=False))


class CreateMCQuestion(Mutation):
    """
        Creating  MCQuestion and adding it to the end of the tour
        Parameters:
            token, String, valid jwt access token
            question_text, String, the text of the question
            tour_id, String, id of the tour to add the checkpoint to
            linked_objects, List of String, list of object_id of objects the question references
            max_choices, Int, maximum numbers of answers that can be chosen
            possible_answers, List of String, list of possible answers to the question
            correct_answers, List of Int, indices of the answers in possible_answers that are correct
            text, String, additional optional description text for the checkpoint
            show_text: Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture: Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details: Boolean, optional, default False, indicates to the app if details should be shown
        if successful returns the created multiple choice question and ok=True
        if unsuccessful because the token was invalid returns empty value for ok
        returns Null and False if unsuccessful because
            tour did not exist
            user did not own the tour
            an object referenced in linked_objects did not exist
    """

    class Arguments:
        token = String(required=True)
        linked_objects = List(of_type=String)
        question_text = String(required=True)
        possible_answers = List(of_type=String, required=True)
        correct_answers = List(of_type=Int, required=True)
        max_choices = Int(required=True)
        tour_id = String(required=True)
        text = String()
        show_text = Boolean()
        show_picture = Boolean()
        show_details = Boolean()

    question = Field(lambda: MCQuestion)
    ok = ProtectedBool()

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, question_text, possible_answers, correct_answers, max_choices, tour_id, **kwargs):
        # get optional arguments
        linked_objects = kwargs.get('linked_objects', None)
        show_text = kwargs.get('show_text', False)
        show_picture = kwargs.get('show_picture', False)
        show_details = kwargs.get('show_details', False)
        text = kwargs.get('text', None)
        # get the current user object to check for permissions
        username = get_jwt_identity()
        if UserModel.objects(username=username):
            user = UserModel.objects.get(username=username)
            # assert that tour exists
            if TourModel.objects(id=tour_id):
                tour = TourModel.objects.get(id=tour_id)
                # assert user is owner of the tour
                if tour.owner == user:
                    links = []
                    if linked_objects:
                        for object_id in linked_objects:
                            if MuseumObjectModel.objects(object_id=object_id):
                                museum_object = MuseumObjectModel.objects.get(object_id=object_id)
                                links.append(museum_object)
                            else:
                                return CreateMCQuestion(question=None, ok=BooleanField(boolean=False))

                    # add checkpoint to the end of the tour
                    current_index = tour.current_checkpoints
                    current_index += 1
                    tour.update(set__current_checkpoints=current_index)
                    tour.save()
                    tour.reload()
                    question = MCQuestionModel(linked_objects=links,
                                               question=question_text, possible_answers=possible_answers,
                                               correct_answers=correct_answers, max_choices=max_choices, tour=tour,
                                               index=current_index, show_text=show_text, show_picture=show_picture,
                                               show_details=show_details, text=text)
                    question.save()
                    return CreateMCQuestion(question=question,
                                            ok=BooleanField(boolean=True))

        return CreateMCQuestion(question=None, ok=BooleanField(boolean=False))


class AddMember(Mutation):
    """Join a Tour using its session code. Featured tours can be joined without session code.
       Parameters: token, String, access token of a user
                   tour_id, String, document id of an existing Tour object
                   session_id, Int, current session id of the tour
       if successful returns the Tour object the user joined and a Boolean True
       if unsuccessful because the Tour does not exist or the session code is invalid returns Null and False
       if unsuccessful because the token was invalid returns an empty value for ok
    """

    class Arguments:
        tour_id = String(required=True)
        token = String(required=True)
        session_id = Int()

    ok = Field(ProtectedBool)
    tour = Field(lambda: Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, **kwargs):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            # assert the provided session id is valid for the tour
            session_id = kwargs.get('session_id', None)
            # featured tours can also be joined by anyone without session id
            if tour.session_id == session_id or tour.status == 'featured':
                username = get_jwt_identity()
                # get user object to reference in the users list of the tour
                if UserModel.objects(username=username):
                    user = UserModel.objects.get(username=username)
                    users = tour.users
                    # add user to tour
                    if user not in users:
                        users.append(user)
                        tour.update(set__users=users)
                        tour.save()
                        tour.reload()
                    # if the user was already a member of the tour nothing changes and the call is still successful
                    return AddMember(ok=BooleanField(boolean=True), tour=tour)
                else:
                    return AddMember(ok=BooleanField(boolean=False), tour=None)
            else:
                return AddMember(ok=BooleanField(boolean=False), tour=None)
        else:
            return AddMember(ok=BooleanField(boolean=False), tour=None)


class SubmitReview(Mutation):
    """Submit a tour for review by the administrators.
    Parameters: token, String, access token of a user, owner must be the creator of the tour
                tour_id, String, document id of an existing Tour
    if successful returns the Tour object and a Boolean True
    if unsuccessful because the Tour does not exist or the token does not belong to the owner of
        the tour returns Null and False
    if unsuccessful because the token was invalid returns an empty value for ok
    """

    class Arguments:
        tour_id = String(required=True)
        token = String(required=True)

    ok = Field(ProtectedBool)
    tour = Field(lambda: Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            username = get_jwt_identity()
            # assert user is the owner of the tour
            if tour.owner.username == username:
                # setting status of the tour to pending will make the request for review show up for admins
                tour.update(set__status='pending')
                tour.save()
                tour.reload()
                return SubmitReview(ok=BooleanField(boolean=True), tour=tour)
            else:
                return SubmitReview(ok=BooleanField(boolean=False), tour=None)
        else:
            return SubmitReview(ok=BooleanField(boolean=False), tour=None)


class UpdateSessionId(Mutation):
    """Change the session id of a tour.
       Parameters: token, String, access token of a user, owner must be the owner of the tour
                   tour, String, document id of an existing Tour owned by the owner of the token
                   session_id, Int, value the session id should be updated to
       if successful returns the Tour and a Boolean True
       if unsuccessful because the Tour does not exist or the token does not belong to the owner of the tour
            returns Null and False
       if unsuccessful because the token was invalid returns an empty value for ok
       """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)
        session_id = Int(required=True)

    ok = Field(ProtectedBool)
    tour = Field(lambda: Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, session_id):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            username = get_jwt_identity()
            # assert caller is the owner of the tour
            if tour.owner.username == username:
                tour.update(set__session_id=session_id)
                tour.save()
                tour.reload()
                return UpdateSessionId(tour=tour, ok=BooleanField(boolean=True))
            else:
                return UpdateSessionId(tour=None, ok=BooleanField(boolean=False))
        else:
            return UpdateSessionId(tour=None, ok=BooleanField(boolean=False))


class RemoveUser(Mutation):
    class Arguments:
        """Kick a user from a Tour.
        Parameters: token, String, access token of a user, owner must be the creator of the tour
                   tour_id, String, document id of an existing Tour
                   username, String, name of the user to be removed
        if successful returns the updated Tour object and a Boolean True
            note this operation is successful if the user was already not part of the tour
        if unsuccessful because the Tour does not exist or the token does not belong to the owner of
            the tour or the username does not exist returns Null and False
        if unsuccessful because the token was invalid returns an empty value for ok

        """
        token = String(required=True)
        tour_id = String(required=True)
        username = String(required=True)

    ok = Field(ProtectedBool)
    tour = Field(lambda: Tour)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, username):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            owner = get_jwt_identity()
            # assert caller is the owner of the tour
            if tour.owner.username == owner:
                # assert the user the caller wants to kick exists
                if UserModel.objects(username=username):
                    user = UserModel.objects.get(username=username)
                    users = tour.users
                    # if user is a member remove him
                    if user in users:
                        users.remove(user)
                    # if the user was not a member of the tour nothing changes and the function call is still successful
                    tour.update(set__users=users)
                    tour.save()
                    tour.reload()
                    return RemoveUser(tour=tour, ok=BooleanField(boolean=True))
                else:
                    return RemoveUser(tour=None, ok=BooleanField(boolean=False))
            else:
                return RemoveUser(tour=None, ok=BooleanField(boolean=False))
        else:
            return RemoveUser(tour=None, ok=BooleanField(boolean=False))


class SubmitFeedback(Mutation):
    """Submit feedback for a Tour.
    Parameters: token, String, access token of a user
                   tour_id, String, document id of an existing Tour
                   rating, Int, rating on a scale of 1-5
                   review, String, text review for the tour
        Feedback is anonymous i.e. the user is submitting the feedback is not logged
        Also note that a user has to be part of a tour in order to submit feedback about it
        if successful returns the Feedback object and a Boolean True
        if unsuccessful because the Tour does not exist or the user does not exits or is not a member of the tour
            or the rating value is invalid returns Null and False
        if unsuccessful because the token was invalid returns an empty value for ok """

    class Arguments:
        tour_id = String(required=True)
        token = String(required=True)
        rating = Int(required=True)
        review = String(required=True)

    ok = Field(ProtectedBool)
    feedback = Field(lambda: TourFeedback)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, rating, tour_id, review):
        # assert tour exists
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            # get user object to use as reference in the feedback
            if UserModel.objects(username=get_jwt_identity()):
                user = UserModel.objects.get(username=get_jwt_identity())
                if user in tour.users:
                    # assert rating is valid on the 1-5 scale
                    if rating < 1:
                        rating = 1
                    elif rating > 5:
                        rating = 5
                    feedback = TourFeedbackModel(rating=rating, review=review, tour=tour)
                    feedback.save()
                    return SubmitFeedback(ok=BooleanField(boolean=True), feedback=feedback)

                else:
                    return SubmitFeedback(ok=BooleanField(boolean=False), feedback=None)
            else:
                return SubmitFeedback(ok=BooleanField(boolean=False), feedback=None)
        else:
            return SubmitFeedback(ok=BooleanField(boolean=False), feedback=None)


class MoveCheckpoint(Mutation):
    """
        Change the index of a given checkpoint in its tour. Can only be used by the tour owner. Indices of other
        checkpoints in the tour are automatically adjusted accordingly.
        Parameters:
                token: String, valid jwt access token
                checkpoint_id: String, document id of the checkpoint to move
                index: Int, the index to put the checkpoint at. values greater than the current_checkpoints field of the
                    tour move the checkpoint to the end. -1 also moves the checkpoint to the end
        if successful returns the updated checkpoint and True
        if unsuccessful because the id was invalid or the user is not the owner of the tour returns Null and False
    """

    class Arguments:
        token = String(required=True)
        checkpoint_id = String(required=True)
        index = Int(required=True)

    ok = Field(ProtectedBool)
    checkpoint = Field(lambda: CheckpointUnion)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, checkpoint_id, index):
        user = UserModel.objects.get(username=get_jwt_identity())
        # assert checkpoint exists
        if not CheckpointModel.objects(id=checkpoint_id):
            return MoveCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        checkpoint = CheckpointModel.objects.get(id=checkpoint_id)
        tour = checkpoint.tour
        # assert user owns the tour
        if tour.owner != user:
            return MoveCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        current_index = checkpoint.index
        max_index = tour.current_checkpoints
        checkpoints = CheckpointModel.objects(tour=tour)
        checkpoints = checkpoints(id__ne=checkpoint_id)
        # move checkpoint to the end of the list
        if index == -1 or index >= max_index:
            checkpoint.update(set__index=max_index)
            checkpoint.save()
            checkpoint.reload()
            for cp in checkpoints():
                # move all checkpoints coming after the old index one back
                if cp.index > current_index:
                    cpidx = cp.index
                    cpidx -= 1
                    cp.update(set__index=cpidx)
                    cp.save()
                    cp.reload()
        # move all checkpoints between the new and old
        elif index < current_index:
            checkpoint.update(set__index=index)
            checkpoint.save()
            checkpoint.reload()
            for cp in checkpoints():
                if current_index > cp.index >= index:
                    cpidx = cp.index
                    cpidx += 1
                    cp.update(set__index=cpidx)
                    cp.save()
                    cp.reload()
        # move all checkpoints between old and new index one
        elif index > current_index:
            checkpoint.update(set__index=index)
            checkpoint.save()
            checkpoint.reload()
            for cp in checkpoints():
                if current_index < cp.index <= index:
                    cpidx = cp.index
                    cpidx -= 1
                    cp.update(set__index=cpidx)
                    cp.save()
                    cp.reload()
        return MoveCheckpoint(checkpoint=checkpoint, ok=BooleanField(boolean=True))


class DeleteCheckpoint(Mutation):
    """
        Delete a Checkpoint from a Tour
        Parameters:
            token, String, valid jwt access token of the owner of the tour the checkpoint belongs to
            checkpoint_id, String, document id of the checkpoint to delete
        returns True if successful
        returns empty value if token was invalid
        returns False if token owner was not the owner of the tour
        IS SUCCESSFUL if the checkpoint does not exist
    """

    class Arguments:
        token = String(required=True)
        checkpoint_id = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, checkpoint_id):
        if CheckpointModel.objects(id=checkpoint_id):
            checkpoint = CheckpointModel.objects.get(id=checkpoint_id)
        # successful if checkpoint does not exist
        else:
            return DeleteCheckpoint(ok=BooleanField(boolean=True))
        tour = checkpoint.tour
        user = UserModel.objects.get(username=get_jwt_identity())
        # assert user owns the tour and thus the checkpoint
        if user == tour.owner:
            index = checkpoint.index
            checkpoints = CheckpointModel.objects(tour=tour)
            # update the indices of following checkpoints accordingly
            for cp in checkpoints:
                if cp.index > index:
                    cpidx = cp.index
                    cpidx -= 1
                    cp.update(set__index=cpidx)
                    cp.save()
                    cp.reload()
            # update the total number of checkpoints in the tour
            max_index = tour.current_checkpoints
            max_index -= 1
            tour.update(set__current_checkpoints=max_index)
            checkpoint.delete()
            return DeleteCheckpoint(ok=BooleanField(boolean=True))
        else:
            return DeleteCheckpoint(ok=BooleanField(boolean=False))


class EditCheckpoint(Mutation):
    """
        Allows tour owners to edit checkpoints in their tours.
        Parameters:
            token, String, required
            checkpoint_id, String, required, id of the checkpoint to be edited
            text, String, optional, description text of the checkpoint
            object_id, optional, object_id of a museum object to update the reference of an ObjectCheckpoint
            picture_id, optional, id of a Picture to update the reference of a PictureCheckpoint
            question, String, text to update the question text of a Question or MCQuestion
            linked_objects, List of String, list of object ids to update the references in a Question or MCQuestion
            possible_answers, List of String, update the possible answers of a MCQuestion
            correct_answers, List of Int, update the correct answers of a MCQuestion
            max_choices, Int, new max choices value for a MCQuestion
            show_text, Boolean, optional, default False, indicates to the app if object text fields should be shown
            show_picture, Boolean, optional, default False, indicates to the app if object pictures should be shown
            show_details, Boolean, optional, default False, indicates to the app if details should be shown
        if successful returns the updated checkpoint and True
        if unsuccessful because the token was invalid returns emtpy value for ok
        returns Null and False if unsuccessful because
            token did not belong to the tour owner
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
        # assert checkpoint exists
        if not CheckpointModel.objects(id=checkpoint_id):
            return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
        # get checkpoint object
        checkpoint = CheckpointModel.objects.get(id=checkpoint_id)
        # assert caller owns the tour and thus the checkpoint
        tour = checkpoint.tour
        user = UserModel.objects.get(username=get_jwt_identity())
        if user != tour.owner:
            return EditCheckpoint(checkpoint=None, ok=BooleanField(boolean=False))
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


class DeleteTour(Mutation):
    """
        Allows the owner of a Tour to delete it. Also deletes all associated checkpoints and answers linked to questions
        Parameters:
            token, String, valid jwt access token of the tour owner
            tour_id, String, document id of the tour to delete
        returns True if successful, notably returns true if tour did not exist
        returns False if user is not the owner of the tour
        returns empty value if token is invalid
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id):
        user = UserModel.objects.get(username=get_jwt_identity())
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            if tour.owner == user:
                tour.delete()
                return DeleteTour(ok=BooleanField(boolean=True))
            return DeleteTour(ok=BooleanField(boolean=False))
        return DeleteTour(ok=BooleanField(boolean=True))


class UpdateTour(Mutation):
    """
        Update a Tour object. Allows the tour owner to change name difficulty and description.
        Parameters:
                token, String, valid jwt access token of the tour owner
                tour_id, String, document id of the tour
                name, String, new name for the tour
                description, String, new description for the tour
                difficulty, String, new difficulty of the tour. forced to be in a range of 1-5
        returns the updated tour object and True if successful
        returns None and False if tour did not exist or user did not own the tour
        returns {} if token was invalid
    """

    class Arguments:
        token = String(required=True)
        tour_id = String(required=True)
        difficulty = Int()
        name = String()
        description = String()

    tour = Field(lambda: Tour)
    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, tour_id, **kwargs):
        user = UserModel.objects.get(username=get_jwt_identity())
        if TourModel.objects(id=tour_id):
            tour = TourModel.objects.get(id=tour_id)
            if user == tour.owner:
                name = kwargs.get('name', None)
                difficulty = kwargs.get('difficulty', None)
                description = kwargs.get('description', None)
                if name is not None:
                    tour.update(set__name=name)
                if difficulty is not None:
                    # force difficulty to be on the scale
                    if difficulty < 1:
                        difficulty = 1
                    if difficulty > 5:
                        difficulty = 5
                    tour.update(set__difficulty=difficulty)
                if description is not None:
                    tour.update(set__description=description)
                tour.update(set__lastEdit=datetime.datetime.now)
                tour.save()
                tour.reload()
                return UpdateTour(tour=tour, ok=BooleanField(boolean=True))
            else:
                return UpdateTour(tour=None, ok=BooleanField(boolean=False))
        else:
            return UpdateTour(tour=None, ok=BooleanField(boolean=False))


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    auth = Auth.Field()
    refresh = Refresh.Field()
    change_password = ChangePassword.Field()
    promote_user = PromoteUser.Field()
    delete_account = DeleteAccount.Field()
    add_favourite_tour = AddFavouriteTour.Field()
    remove_favourite_tour = RemoveFavouriteTour.Field()
    add_favourite_object = AddFavouriteObject.Field()
    remove_favourite_object = RemoveFavouriteObject.Field()
    app_feedback = SendFeedback.Field()
    create_tour = CreateTour.Field()
    create_question = CreateQuestion.Field()
    create_answer = CreateAnswer.Field()
    create_mc_answer = CreateMCAnswer.Field()
    create_mc_question = CreateMCQuestion.Field()
    add_member = AddMember.Field()
    submit_for_review = SubmitReview.Field()
    update_session_id = UpdateSessionId.Field()
    remove_user = RemoveUser.Field()
    submit_tour_feedback = SubmitFeedback.Field()
    add_badge_progress = AddBadgeProgress.Field()
    choose_profile_picture = ChooseProfilePicture.Field()
    create_checkpoint = CreateCheckpoint.Field()
    create_picture_checkpoint = CreatePictureCheckpoint.Field()
    create_object_checkpoint = CreateObjectCheckpoint.Field()
    edit_checkpoint = EditCheckpoint.Field()
    move_checkpoint = MoveCheckpoint.Field()
    delete_checkpoint = DeleteCheckpoint.Field()
    change_username = ChangeUsername.Field()
    delete_tour = DeleteTour.Field()
    update_tour = UpdateTour.Field()
