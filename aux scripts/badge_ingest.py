import os
import mongoengine
from flask_mongoengine import MongoEngine
from mongoengine import register_connection
from models.Badge import Badge
from models.ProfilePicture import ProfilePicture

"""
Ingestion script for badges. Allows adding profile pictures to the database in bulk. Pictures are assumed to 
be in jpeg format and located at ../data/badges relative to the location of this script.
Name and id for the badge are inferred from file name. Cost for now is fixed for bronze, silver, gold badge levels 
Associated profile pictures are expected to be located in ../data/profilepictures/locked in jpeg format and have the 
same file name as their badge
"""

# connect to database. assumes default port and no password
mongo = MongoEngine()
mongoengine.connect(host='localhost:27017')
register_connection("file", "file")


def ingest_badges():
    dir_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(os.path.dirname(dir_path))
    # data path to badges
    badge_path = os.path.join(dir_path, 'data/badges')
    # data path to profile pictures
    pic_path = os.path.join(dir_path, 'data/profilepictures/locked')

    # iterating through the directory
    with os.scandir(badge_path) as directory:
        for file in directory:
            # ignoring subdirectories
            if file.is_file():
                # ignoring non-png files. for first batch of badges different formats were provided.
                # for later additions if no png files are provided they will have to be converted to png
                if file.path.endswith('jpg'):
                    # get the actual data
                    # using with to ensure to file is closed
                    # mode HAS to be rb for mongoengine to be able to read the file
                    with open(file.path, 'rb') as icon:
                        # getting file name without extension
                        name = file.name[:-4]
                        # based on file name infer level and thus cost of the badge
                        if 'bronze' in name:
                            cost = 3
                        elif 'silber' in name:
                            cost = 10
                        elif 'gold' in name:
                            cost = 30
                        else:
                            cost = 100
                        # find the associated profile picture on the disk and create a ProfilePicture object with it
                        with os.scandir(pic_path) as pic_dir:
                            for profile_pic_file in pic_dir:
                                if profile_pic_file.is_file():
                                    if name in profile_pic_file.path:
                                        with open(profile_pic_file.path, 'rb') as profile_picture:
                                            pic = ProfilePicture()
                                            pic.picture.put(profile_picture, content_type='image/jpeg')
                                            pic.save()
                                            pic.reload()
                                            pic.update(set__locked=True)
                                            pic.save()
                                            pic.reload()
                        badge_name = name.replace('_', ' ')
                        # define document. needs these parameters to be created
                        badge = Badge(id=name, name=badge_name, cost=cost, unlocked_picture=pic)
                        # adding data to GridFS FileField
                        badge.picture.put(icon, content_type='image/png')
                        # saving
                        badge.save()
                        # reloading to get id
                        badge.reload()
                        # TODO: Ideally we would add a new badge to all the user badge_progress dictionaries.
                        #       However this results in a cyclic import here because of the initialization of that dict
                        #       with all badges objects in models.User. The createBadge function in app.WebMutations
                        #       and the upload function in museum_app.file do not have this problem.
                        # for user in User.objects.all():
                        # badges = user.badge_progress
                        # badges[str(id)] = 0
                        # user.update(set__badge_progress=badges)
                        # user.save()
                        # printing id for feedback on if the script is working.
                        print(badge.id)


ingest_badges()
