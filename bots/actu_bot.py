# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import requests, bs4, pickle

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext, CardFactory, ConversationState, UserState
from botbuilder.schema import ChannelAccount, HeroCard, CardImage, CardAction, ActionTypes, SuggestedActions, AudioCard, MediaUrl
from botbuilder.dialogs import Dialog 

from config import DataBase, db, ActuBot
from helpers.dialog_helper import DialogHelper


# This bot's main dialog.
class YnovBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState, dialog: Dialog):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.dialog = dialog
        self.bot = ActuBot()
        self.fonctionality = None
        self.database = DataBase()
        self.database.create_table('User', 
                                   id_user=db.String, 
                                   name=db.String, 
                                   age=db.Integer, 
                                   city=db.String, 
                                   transport=db.String, 
                                   picture=db.PickleType)
    
    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        # Save any state changes that might have ocurred during the turn.
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added:[ChannelAccount], turn_context:TurnContext):
        self.first_dialog = True #utilisé pour vérifier si le multi-turn est terminé
        
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self.__send_intro_card(turn_context)
                await self.connexion(turn_context)
                

    # Ne pas modifier cette fonction
    async def on_message_activity(self, turn_context: TurnContext):

        if turn_context.activity.text in ["menu", "help", "info", 'aide', "intro", 'exit', 'quit']:
            await self.intro(turn_context)
            self.fonctionality = None

        elif self.first_dialog: await self.create_user_profile(turn_context)

        # Fonctionnalité Actualité du menu principal
        elif turn_context.activity.text in ["Actualité", "Traduction", "Profil"]:
            self.fonctionality = turn_context.activity.text
            message = ("Quelle actualité souhaitez-vous voir ?" if self.fonctionality == "Actualité" else None 
                        or "Que souhaitez-vous traduire ?" if self.fonctionality == "Traduction" else "Que souhaitez-vous faire ?")
            await turn_context.send_activity(MessageFactory.text(message))

        # Appel des fonctionnalités
        if self.fonctionality == "Actualité" and turn_context.activity.text!= "Actualité": await self.actuality(turn_context)
        elif self.fonctionality == "Profil": return await self.profil(turn_context)
        elif self.fonctionality == "Traduction" and turn_context.activity.text!= "Traduction":return await self.traduction(turn_context)



    #------------------ Traduction ------------------# 

    async def traduction(self, turn_context: TurnContext):

        traduction = self.bot.trad(turn_context.activity.text)
        await turn_context.send_activity(MessageFactory.text(traduction))
        
        self.fonctionality = None
        await self.audio_card(turn_context, './trad.mp3')

        return await self.intro(turn_context)


    #------------------ Gestion du profil utilisateur ------------------# 


    async def profil(self, turn_context: TurnContext):
        # Afficher une card_actions avec 3 options : Modifier le profil, Supprimer le profil, Afficher le profil   
        card_actions = [
            CardAction(type=ActionTypes.im_back, title="Modifier le profil", value="Modifier le profil"),
            CardAction(type=ActionTypes.im_back, title="Afficher le profil", value="Afficher le profil"),
            CardAction(type=ActionTypes.im_back, title="Supprimer le profil", value="Supprimer le profil"),
            ]

        reply_activity = MessageFactory.text("")
        reply_activity.suggested_actions = SuggestedActions(actions=card_actions)

        
        # Si Modifier le profil -> Supprimer de la database et relancer le user_profile
        if turn_context.activity.text == "Modifier le profil":
            self.database.delete_row_by_id('User', turn_context.activity.recipient.id)
            self.fonctionality = None
            self.first_dialog = True
            return await self.create_user_profile(turn_context)

        # Si Afficher le profil -> Afficher le profile avec une card
        if turn_context.activity.text == "Afficher le profil":
            self.fonctionality = None
            try:
                card = HeroCard(
                title="Profil utilisateur",
                text="Nom : " + self.user.name + "\n \n"
                "Age : " + str(self.user.age) + "\n \n"
                "City : " + str(self.user.city) + "\n \n"
                "Moyen de transport : " + self.user['transport'] + "\n \n",
                images=[CardImage(url=pickle.loads(self.user['picture']).content_url)])

                await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))
                return await self.intro(turn_context)
            except:
                await turn_context.send_activity(MessageFactory.text("Vous n'avez pas encore de profil !"))
                return await self.intro(turn_context)

        # Si Supprimer le profil -> Supprimer de la database et supprimer le profil self.user
        if turn_context.activity.text == "Supprimer le profil":
            try:
                self.database.delete_row_by_id('User', self.user[0])
                self.fonctionality = None
                self.user = None
                await turn_context.send_activity(MessageFactory.text("Votre profil a bien été supprimé !"))
                return await self.intro(turn_context)
            except:
                await turn_context.send_activity(MessageFactory.text("Il n'y aucun profil à supprimer !"))
                return await self.intro(turn_context)
     
        return await turn_context.send_activity(reply_activity)


    #------------------ Menu Principal ------------------#


    async def intro(self, turn_context: TurnContext):
        card_actions = [
                CardAction(type=ActionTypes.im_back, title="Profil", value="Profil"),
                CardAction(type=ActionTypes.im_back, title="Actualité", value="Actualité"),
                CardAction(type=ActionTypes.im_back, title="Traduction", value="Traduction"),
                ]

        reply_activity = MessageFactory.text("Quelle fonctionnalité souhaitez-vous utiliser ?")
        reply_activity.suggested_actions = SuggestedActions(actions=card_actions)     
        await turn_context.send_activity(reply_activity)



    #------------------ Création du profil utilisateur ------------------# 


    async def create_user_profile(self, turn_context: TurnContext):
        if turn_context.activity.text == "Non ":
            self.first_dialog = False
            await turn_context.send_activity(MessageFactory.text(f"C'est noté ! Commençons la discussion !"))
            return await self.intro(turn_context)
            
        await DialogHelper.run_dialog(self.dialog,turn_context,self.conversation_state.create_property("DialogState"))
        user_state = UserState(turn_context.adapter).get(turn_context)

        if user_state:
            self.first_dialog = False
            self.user_profile = user_state['UserProfile']
            self.database.add_row('User', 
                                    id_user=str(turn_context.activity.recipient.id), 
                                    name=str(self.user_profile.name), 
                                    age=int(self.user_profile.age), 
                                    city=str(self.user_profile.city),
                                    transport=str(self.user_profile.transport), 
                                    picture=pickle.dumps(self.user_profile.picture))
            self.user = self.database.read_table_by_id('User', 'id_user', turn_context.activity.recipient.id)
            return await self.intro(turn_context)


    #------------------ Gestion de l'actualité ------------------# 

    async def actuality(self, turn_context: TurnContext):
        key_user = turn_context.activity.text
        await turn_context.send_activity(
            MessageFactory.text(f"Voici les actualités du jour sur la thématique : {key_user}."))
        
        response = self.bot.actualities(key_user)
        await self.audio_card(turn_context, f'./{key_user}.mp3')

        for text in response.split('. '):
            await turn_context.send_activity(MessageFactory.text(text + "."))

        self.fonctionality = None
        return await self.intro(turn_context)
    

    #------------------ Card Introduction ------------------#

    
    async def __send_intro_card(self, turn_context:TurnContext):
        self.user = self.database.read_table_by_id('User', 'id_user', turn_context.activity.recipient.id)

        try:city = self.user.city
        except: city = 'Paris'

        soup = bs4.BeautifulSoup(requests.get(f'https://www.msn.com/fr-fr/meteo/previsions/in-{city}').text, 'html.parser' )
        img = soup.find('div', class_='summaryLineGroupCompact-E1_1').find('img').attrs['src']
        temp = soup.find('div', class_='summaryLineGroupCompact-E1_1').find('a').attrs['title'].replace('\u200e', ' ')
        prévison = soup.find('div', class_='summaryDescContainer-E1_1').find('p').text

        card = HeroCard(
            title="Bienvenue sur le bot de synthèse d'actualités !",
            subtitle=f'Température actuelle à {city} : {temp}',
            text="Bienvenue sur le bot de synthèse d'actualités !"
            "\n \n Prévious du jour : " + prévison + "\n \n"
            "Ce bot est basé sur la technologie GPT-4."
            "Avant de débuter, je vais vous poser quelques questions afin de personnaliser votre expérience.",
            
            images=[CardImage(url=img)],
            buttons=[
                CardAction(
                    type=ActionTypes.open_url,
                    title="En savoir plus sur GPT-3.5Turbo",
                    text="En savoir plus sur GPT-3.5Turbo",
                    display_text="En savoir plus sur GPT-3.5Turbo",
                    value="https://openai.com/")])

        return await turn_context.send_activity(MessageFactory.attachment(CardFactory.hero_card(card)))



    #------------------ Connexion à la base de données ------------------# 

    async def connexion(self, turn_context: TurnContext):
        if self.user:
            self.first_dialog = False
            await turn_context.send_activity(MessageFactory.attachment(pickle.loads(self.user.picture)))
            await turn_context.send_activity(MessageFactory.text(f"Bonjour {self.user.name}, Ravi de vous revoir !"))
            return await self.intro(turn_context)
            
        else:
            card_actions = [
                CardAction(type=ActionTypes.im_back, title="Oui", value="Oui"),
                CardAction(type=ActionTypes.im_back, title="Non ", value="Non "),
                ]

            reply_activity = MessageFactory.text("Souhaitez-vous personneliser l'expérience ?")
            reply_activity.suggested_actions = SuggestedActions(actions=card_actions)     
            await turn_context.send_activity(reply_activity)


    #------------------ Card Audio ------------------# 

    async def audio_card(self, turn_context: TurnContext, url_file:str):

        media_url = MediaUrl(url=url_file)
        audio_card = AudioCard(
            title="Titre de la carte audio",
            media=[media_url],
            autostart=True,
            image=None,
            buttons=[CardAction(
                    type="openUrl",
                    title="Lien vers la source de la piste audio",
                    value=url_file)])
        
        message = MessageFactory.attachment(CardFactory.audio_card(audio_card))

        return await turn_context.send_activity(message)