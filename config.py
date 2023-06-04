#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sqlalchemy as db
import requests, openai, bs4, os
from transformers import pipeline
from gtts import gTTS


""" Bot Configuration """

class DefaultConfig:
    """ Bot Configuration """

    PORT = 8000
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    OPENAI_KEY = os.getenv('OPENAI_KEY')



""" Base de données """

import sqlalchemy as db

class DataBase():
    """
    Retour un objet de type sqlalchemy gérant la connexion à une base de données sqlite.
    name_database : str --> Nom de la base de donnée
    """
    
    def __init__(self, name_database:str='database', my_sql=False):
        self.name = name_database
        self.url = (f"mysql://root:root@127.0.0.1:3306/{name_database}" if my_sql 
                    else f"sqlite:///{name_database}.db") # Connexion à la base de données MySQL
        self.engine = db.create_engine(self.url)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.table = self.engine.table_names()
       
    # Méthode pour créer une table
    def create_table(self, name_table:str, **kwargs):
        """
        Crée une Table dans la base de données.
        name_table : str   --> Nom de la base de données
        **kwargs :  nom_de_colonne=db.String, nom_de_colonne=db.Integer
        """
        try:
            colums = [db.Column(k, v, primary_key = True) 
            if 'id_' in k else db.Column(k, v) for k,v in kwargs.items()]
            db.Table(name_table, self.metadata, *colums)
            self.metadata.create_all(self.engine)
            print(f"Table : '{name_table}' are created succesfully")
        except:
            print(f"La Table{name_table} existe déjà !")
        
    # Méthode pour lire une table
    def read_table(self, name_table:str, return_keys=False):
        """
        Lecture de la base de données, retourne les colonnes et lignes de la base de données.
        name_table : str   --> Nom de la base de données
        """
        
        table = db.Table(name_table, 
                         self.metadata, 
                         autoload=True, 
                         autoload_with=self.engine)
        
        if return_keys:table.columns.keys() 
        else : return table
        
    # Méthode pour ajouter une ligne dans une table
    def add_row(self, name_table:str, **kwarrgs):
        """
        Ajout d'une ligne dans la base de données
        name_table : str   --> Nom de la base de données
        **kwarrgs:  nom_de_colonne1 = valeur_à_ajoutée, nom_de_colonne2 = valeur_à_ajoutée
        """
        
        name_table = self.read_table(name_table)
        stmt = (
            db.insert(name_table).
            values(kwarrgs)
        )
        self.connection.execute(stmt)
        print(f'Row id added')
        
    # Méthode pour supprimer une ligne dans une table en fonction de son id
    def delete_row_by_id(self, name_table:str, id_:int):
        """
        Supprime du contenu de la base de données
        name_database : str --> Nom de la base de donnée
        id_ : int. --> numéro id de la ligne à supprimer
        """

        table = self.read_table(name_table) 
        id = table.c.keys()[0]
        
        stmt = (
            db.delete(table).
            where(table.c[id] == id_)
            )
        self.connection.execute(stmt)
        print(f'Row id {id_} deleted')
        
    # Méthode pour afficher une table
    def select_table(self, name_table:str):
        """
        Retour l'ensemble du contenu de la base de données
        name_database : str --> Nom de la base de donnée
        """
        
        name_table = self.read_table(name_table)       
        stm = db.select([name_table])
        return self.connection.execute(stm).fetchall()
    
    # Méthode pour afficher une ligne en fonction de son id
    def read_table_by_id(self, name_table:str, coloumn, id_:int, return_keys=False):
        """
        Lecture de la base de données, retourne les colonnes et lignes de la base de données.
        name_table : str   --> Nom de la base de données
        id : int   --> ID de la ligne à sélectionner
        """
        
        table = db.Table(name_table, 
                         self.metadata, 
                         autoload=True, 
                         autoload_with=self.engine)
        
        query = table.select().where(table.c[coloumn] == id_)
        result = self.connection.execute(query).fetchone()
        
        if return_keys:
            return table.columns.keys() 
        else:
            return result
    
    # Méthode pour modifier une ligne en fonction de son id
    def update_row_by_id(self, name_table:str, id_:int, **kwarrgs):
        """
        Ajout d'une ligne dans la base de données
        name_table : str   --> Nom de la base de données
        **kwarrgs:  nom_de_colonne1 = valeur_à_ajoutée, nom_de_colonne2 = valeur_à_ajoutée
        """
        
        name_table = self.read_table(name_table)
        id = name_table.c.keys()[0]
        
        stmt = (
            db.update(name_table).
            where(name_table.c[id] == id_).
            values(kwarrgs)
        )
        self.connection.execute(stmt)
        print(f'Row id {id_} updated')

""" ActuBot/TradBot """

class ActuBot():
    def entity_(self, phrase:str):
        self.entity_recognition = pipeline("ner")
        return self.entity_recognition(phrase)
  
    def trad(self, phrase:str):
        openai.api_key = DefaultConfig().OPENAI_KEY
        reponse = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
            {"role": "system", "content": "Tu es un traducteur professionnel qui traduit du Français vers l'anglais"},
            {"role": "user", "content": f"Traduire le texte suivant de français : '{phrase}'"}],
            temperature=0.5,
            max_tokens=50,
        )['choices'][0]['message']["content"]

        tts = gTTS(text=reponse, lang="en")
        tts.save("trad.mp3")
        return reponse
    
    def actualities(self, query):
        
        openai.api_key = DefaultConfig().OPENAI_KEY
        text = requests.get(f'https://www.bing.com/news/search?q={query}').text
        soup = bs4.BeautifulSoup(text, 'html.parser')
        
        actu = ' '.join(["- " + article.text+ f" | Sources : {article.attrs['href']}"+' \n'  
                         for article in soup.find_all('a', 'title')])

        reponse = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
            {"role": "system", 
            "content": f"Tu es un rédacteur web qui synthétise l'actualité en 100 mots sur différentes thématiques en fournissant les liens des sources et le lien de l'article. Tu fais des liaisons entre les articles avec des mots tel que 'mais', 'donc', 'or', 'par contre', 'en revanche', 'en effet', 'cependant', 'toutefois', 'par ailleurs', 'par contre', 'par contre, 'enfin'"},
            {"role": "user", 
            "content": f"Thématique abbordée : '{query}'. Voici la liste des actualités à synthétiser : " + actu},
            ],
            max_tokens=300,
            temperature=0.9,
            )['choices'][0]['message']["content"]
        
        tts = gTTS(text=reponse, lang="fr")
        tts.save(f"{query}.mp3")
        
        return reponse
