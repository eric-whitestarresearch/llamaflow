#     Llamaflow - A self service portal with runbook automation
#     Copyright (C) 2024  Whitestar Research LLC
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.


import yaml
from pymongo import MongoClient
from bson import ObjectId, json_util
import urllib.parse
import json
import re

class DocumentNotFound(Exception):
    pass

class Database:
    """
    This is a class used for accessing the database. When initialize it it open a connection to the database. 
    The config for the database connection comes from /opt/self-service-portal/conf/db.conf

    Attributes:
        mongo_client (MongoClient): The client class for the db connection
        datbase (Database): The database the client is connected to
        collection (Collection): The collection that the client is connect to
    """
    conf_home = "/opt/llamaflow/conf"

    def __init__(self) -> None:
        """
        The constructor for the Database class.

        Parameters:
            self (Database): The object itself
        """
        with open(self.conf_home+"/db.yaml",'r') as file:
            db_config = yaml.safe_load(file)

        username = urllib.parse.quote_plus(db_config['username'])
        password = urllib.parse.quote_plus(db_config['password'])
        self.mongo_client = MongoClient('mongodb://%s:%s@%s:%s' % (username, password, db_config['host'], db_config['port']))
        self.app = None

    def init_app(self, app):
        ""

        ""
        self.app = app
        
    def get_mongo_client(self):
        """
        Get a client to connect to the database

        Parameters:
            self (Database): The object itself
        """
        
        return self.mongo_client
    

    def find_by_id(self, database, collection, object_id):
        """
        A method to find a document by its object id. 
        
        Parameters:
            self (Database): The instantiation of the Database class
            databse (str): The name of the database to search in
            collection (str): The name of the collection to search in
            object_id (Str): The id of the document to find. The id must be 24 hexadecimal characters with lowercase letters

        Returns:
            Dict: A dict with the document if the document is found. 
            None: If the document is not found.
        """

        database_conn = self.mongo_client[database]
        collection_conn = database_conn[collection]

        if not re.match('^[0-9a-f]{24}$',object_id):
            raise "Object id must be 24 chacters hexadecimal string with lowercase letters"

        object_instance =  ObjectId(object_id)
        result = collection_conn.find_one({"_id": object_instance})

        return json.loads(json_util.dumps(result))

    def find_one_by_query(self, database, collection, query):
        """
        A function to find one record using a query

        Parameters:
            self (Database): The instantiation of the Database class
            databse (str): The name of the database to search in
            collection (str): The name of the collection to search in
            query (Dict): A dictonary with the query
        
        Returns:
            Dict: A dict with the document if document is found
            None: If the document is not found        
        """
        database_conn = self.mongo_client[database]
        collection_conn = database_conn[collection]
        result = collection_conn.find_one(query)

        return json.loads(json_util.dumps(result))
    
    def insert_document(self, database, collection, document):
        """
        A function to insert a new doument

        Parameters:
            self (Database): The instantiation of the Database class
            databse (str): The name of the database to insert into
            collection (str): The name of the collection to insert into
            document (Dict): A dictonary with the document to inset into a collection

        Returns:
            object_id (Str): A 24 character hexadecmal string that represents the id of the new object
        """

        database_conn = self.mongo_client[database]
        collection_conn = database_conn[collection]
        result = collection_conn.insert_one(document)

        return str(result.inserted_id)

    def update_one(self, database, collection, query, document):
        """
        A function to update a document

        Parameters:
            self (Database): The instantiation of the Database class
            databse (str): The name of the database the document resides in
            collection (str): The name of the collection the document resides in
            query (Dict): The query to find the document
            document (Dict): The data to update with

        Returns:
            (Str): The document ID of the updated document
        """

        database_conn = self.mongo_client[database]
        collection_conn = database_conn[collection]

        result = collection_conn.update_one("workflow-engine", "workflowExecution", query, {'$set':document}, upsert=True)
        return str(result.upserted_id)
    


        