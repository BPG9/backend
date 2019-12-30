from flask_graphql_auth import create_access_token, create_refresh_token, mutation_jwt_refresh_token_required, \
    get_jwt_identity, AuthInfoField, mutation_jwt_required
from graphene import ObjectType, Schema, List, Mutation, String, Field, Boolean, Union
from graphene_mongo import MongoengineObjectType
from werkzeug.security import generate_password_hash, check_password_hash
from models.Code import Code
from models.User import User as UserModel

"""
GraphQL Schema for user management. 
Supports user creation, password changes, user - teacher promotion, login / auth and jwt management. 
login returns access and refresh token. all other requests require a valid refresh token. 
"""


# TODO: queries


class BooleanField(ObjectType):
    boolean = Boolean()


class ProtectedBool(Union):
    class Meta:
        types = (BooleanField, AuthInfoField)

    @classmethod
    def resolve_type(cls, instance, info):
        return type(instance)


class StringField(ObjectType):
    string = String()


class ProtectedString(Union):
    class Meta:
        types = (StringField, AuthInfoField)

    @classmethod
    def resolve_type(cls, instance, info):
        return type(instance)


class User(MongoengineObjectType):
    class Meta:
        model = UserModel


class CreateUser(Mutation):
    class Arguments:
        username = String(required=True)
        password = String(required=True)
        teacher = Boolean()

    user = Field(lambda: User)
    ok = Boolean()

    def mutate(self, info, username, password):
        if not UserModel.objects(username=username):
            user = UserModel(username=username, password=generate_password_hash(password))
            user.save()
            return CreateUser(user=user, ok=True)
        else:
            return CreateUser(user=None, ok=False)


class PromoteUser(Mutation):
    class Arguments:
        token = String()
        code = String()

    ok = Field(ProtectedBool)
    user = Field(User)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, code):
        username = get_jwt_identity()
        if not Code.objects(code=code):
            return PromoteUser(ok=BooleanField(boolean=False))
        else:
            code_doc = Code.objects.get(code=code)
            code_doc.delete()
            user = UserModel.objects.get(username=username)
            user.update(set__teacher=True)
            user.save()
            user = UserModel.objects.get(username=username)
            return PromoteUser(ok=BooleanField(boolean=True), user=user)


class ChangePassword(Mutation):
    class Arguments:
        token = String()
        password = String()

    ok = Field(ProtectedBool)

    @classmethod
    @mutation_jwt_required
    def mutate(cls, _, info, password):
        username = get_jwt_identity()
        user = UserModel.objects(username=username)[0]
        user.update(set__password=generate_password_hash(password))
        user.save()
        return ChangePassword(ok=BooleanField(boolean=True))


class Auth(Mutation):
    class Arguments:
        username = String(required=True)
        password = String(required=True)

    access_token = String()
    refresh_token = String()
    ok = Boolean()

    @classmethod
    def mutate(cls, _, info, username, password):
        if not (UserModel.objects(username=username) and check_password_hash(
                UserModel.objects(username=username)[0].password, password)):
            return Auth(ok=False)
        else:

            return Auth(access_token=create_access_token(username), refresh_token=create_refresh_token(username),
                        ok=True)


class Refresh(Mutation):
    class Arguments(object):
        refresh_token = String()

    new_token = String()

    @classmethod
    @mutation_jwt_refresh_token_required
    def mutate(cls, info):
        current_user = get_jwt_identity()
        return Refresh(new_token=create_access_token(identity=current_user))


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    auth = Auth.Field()
    refresh = Refresh.Field()
    change_password = ChangePassword.Field()
    promote_user = PromoteUser.Field()


class Query(ObjectType):
    users = List(User)
    user = List(User, username=String())

    def resolve_user(self, info, username):
        return list(UserModel.objects.get(username=username))

    def resolve_users(self, info):
        return list(UserModel.objects.all())


user_schema = Schema(query=Query, mutation=Mutation)
