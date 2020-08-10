from flask import Flask
from flask_graphql_auth import GraphQLAuth
import os
from .extensions import mongo
from app.Schema import web_schema, app_schema
from graphene_file_upload.flask import FileUploadGraphQLView
from .file import fileBP
from flask_jwt_extended import JWTManager


def create_app(config_object='museum_app.settings'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    mongo.init_app(app)
    # flask-graphql-auth bind
    auth = GraphQLAuth(app)
    # flask-jwt-extended bind
    jwt = JWTManager(app)

    # Endpoints
    app.add_url_rule(
        '/web/',
        view_func=FileUploadGraphQLView.as_view(
            'web',
            schema=web_schema,
            graphiql=True
        )
    )
    app.add_url_rule(
        '/app/',
        view_func=FileUploadGraphQLView.as_view(
            'app',
            schema=app_schema,
            graphiql=True
        )
    )
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # bind for alternative file up&download. routes found in museum_app.file
    app.register_blueprint(fileBP)
    return app

