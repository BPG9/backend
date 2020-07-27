"""Dictionary of MongoDB settings.""" 
MONGODB_SETTINGS = {
                        'host': '127.0.0.1',
                        'port': 27017
                    }
"""Secret key used for the generation of the JWTs."""
JWT_SECRET_KEY = "MRTFms24xN5zh4"
"""Time the created refresh tokens remain valid if no new session is created in days. """
REFRESH_EXP_LENGTH = 3
"""Time the created access tokens remain valid if it is not refreshed and no new session is created in minutes."""
ACCESS_EXP_LENGTH = 20
"""Secret key for the Flask server"""
SECRET_KEY = "2HyFpwHAwFkUUn"
"""Name of the file that contains the app factory function"""
FLASK_APP = "__init__.py"
STATIC_FOLDER = "static"
