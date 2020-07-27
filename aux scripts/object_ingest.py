import os
import mongoengine
from models.MuseumObject import MuseumObject
import pandas as pd
from flask_mongoengine import MongoEngine
from mongoengine import register_connection
from models.Picture import Picture
"""
Ingestion script for museum objects. Allows adding objects to the database in bulk. Does not make any updates to
existing objects. If a objectId in the supplied data already exists in the database this will fail. Expects object data 
to be located in data/objects.xlsx and pictures to be located at data/pictures. Paths are relative to the location of 
this script. Script is run from the command line. Mongod service has to be running.  
"""


mongo = MongoEngine()
# defining the connection to the database. This assumes default port and no password.
mongoengine.connect(host='localhost:27017')
register_connection("object", "object")
register_connection("file", "file")


def object_ingest(picture_dict):
    """
    Object ingestion function. Iterates through a pandas DataFrame created from the object data. Has to run after
    picture_ingest as it needs its output.
    :param picture_dict:  output of picture_ingest, dictionary where keys are files names of pictures and values are the
                          document id of the Picture object in the database holding that file
    """
    # file path
    dir_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(os.path.dirname(dir_path))
    file_name = os.path.join(dir_path, 'data/objects.xlsx')
    # reading data as a pandas dataframe. needs dependencies pandas and xlrd to read excel data
    df = pd.read_excel(file_name, index_col=0)
    # iterating through objects
    for idx, row in df.iterrows():
        # all required fields have to be passed here
        museum_object = MuseumObject(object_id=str(row['Inventarnummer']), category=row['Abteilung'],
                                     sub_category=row['Sammlungsbereich'], title=row['Titel'])
        # need to save once before we can call update()
        museum_object.save()
        description = str(row['Objektbeschreibung'])
        description = description.replace('\n', ' ')
        if description == 'nan':
            description = ''
        museum_object.update(set__description=description)
        additional_information = str(row['additional'])
        if additional_information == 'nan':
            additional_information = ''
        additional_information = additional_information.replace('\n', ' ')
        museum_object.update(set__additional_information=additional_information)

        # mostly the same procedure for each field. explained once
        # convert to string because pandas will read numbers in cells as int or float
        inter = str(row['Interdisciplinary'])
        # strip whitespaces left and right
        inter = inter.strip()
        if inter == 'nan':
            inter = ''
        museum_object.update(set__interdisciplinary_context=inter)

        year = str(row['Datierung'])
        # some fields had \xa0 characters in them. this is a non-line-breaking space so it's replaced by space
        year = year.replace(u'\xa0', u' ')
        year = year.strip()
        if year == 'nan':
            year = ''
        museum_object.update(set__year=year)

        art_type = str(row['Objektgattung'])
        art_type = art_type.strip()
        if art_type == 'nan':
            art_type = ''
        museum_object.update(set__art_type=art_type)

        creator = str(row['Hersteller'])
        creator = creator.replace(u'\xa0', u' ')
        creator = creator.strip()
        if creator == 'nan':
            creator = ''
        museum_object.update(set__creator=creator)

        material = str(row['Material'])
        material = material.strip()
        if material == 'nan':
            material = ''
        museum_object.update(set__material=material)

        size = str(row['Size'])
        size = size.strip()
        if size == 'nan':
            size = ''
        museum_object.update(set__size_=size)

        location = str(row['Verortung'])
        location = location.strip()
        if location == 'nan':
            location = ''
        museum_object.update(set__location=location)

        # museumObject.picture is a list of references to Picture documents.
        # this creates the list by going from table entry -> file name -> document id -> object to add to list
        pictures = []
        # split the table entry to get all file names associated with the currrent object
        for picture_name in [name.strip() for name in row['Bild'].replace('\n', '').split(',')]:
            # get the document id from the input dictionary created by picture_ingest
            pid = picture_dict[picture_name]
            # get the actual database object and append the reference
            pic = Picture.objects.get(id=pid)
            pictures.append(pic)
        museum_object.update(set__picture=pictures)
        museum_object.save()


def picture_ingest():
    """ Ingestion for object pictures. Allows ingestion of pictures in bulk. Only creates picture objects and does not
        link them to MuseumObject entries. Pictures are assumed to be located in data/pictures relative to the location
         of this script and saved in jpg format."""
    picture_directory = 'data/pictures'
    # defining output var
    id_dict = {}
    # iterating through all files in the directory
    # using with to ensure closing
    with os.scandir(picture_directory) as directory:
        for file in directory:
            # ignore sub directories
            if file.is_file():
                # ignore random png files that were in sample data.
                # convert before running the script if any are in the wrong format
                if file.path.endswith('jpg'):
                    # opening actual file to get the data
                    # again using with to ensure closing
                    # mode HAS to be rb for mongoengine to be able to read the bytes
                    with open(file.path, 'rb') as picture:
                        # defining document to hold the file
                        pic = Picture()
                        # storing data in GridFS FileField
                        pic.picture.put(picture, content_type='image/jpeg')
                        pic.save()
                        # reloading to access id
                        pic.reload()
                        # add to output
                        id_dict[str(file.name)] = str(pic.id)

    return id_dict


# first run picture ingest to get the dictionary
picture_dict = picture_ingest()
# then give the dictionary to object ingest
object_ingest(picture_dict)

