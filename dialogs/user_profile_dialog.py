# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.dialogs import ComponentDialog, WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, ChoicePrompt, ConfirmPrompt, AttachmentPrompt
from botbuilder.dialogs.prompts import PromptOptions, PromptValidatorContext
from botbuilder.dialogs.choices import Choice
from botbuilder.core import MessageFactory, UserState

from data_models import UserProfile


class UserProfileDialog(ComponentDialog):

    #------------------ Init, Attachement & WaterfallDialog ------------------# 

    def __init__(self, user_state: UserState):
        super(UserProfileDialog, self).__init__(UserProfileDialog.__name__)
        self.user_profile_accessor = user_state.create_property("UserProfile")

        self.add_dialog(
            WaterfallDialog(
                WaterfallDialog.__name__,
                [
                    self.transport_step,
                    self.name_step,
                    self.name_confirm_step,
                    self.age_step,
                    self.city_step,
                    self.picture_step,
                    self.confirm_step,
                    self.summary_step,
                ],))
        
        self.add_dialog(TextPrompt(TextPrompt.__name__) )
        self.add_dialog(NumberPrompt(NumberPrompt.__name__, UserProfileDialog.age_prompt_validator))
        self.add_dialog(ChoicePrompt(ChoicePrompt.__name__))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(AttachmentPrompt(AttachmentPrompt.__name__, UserProfileDialog.picture_prompt_validator))
        self.initial_dialog_id = WaterfallDialog.__name__


    #------------------ Transport Car ------------------# 

    async def transport_step( self, step_context: WaterfallStepContext) -> DialogTurnResult:
        return await step_context.prompt(
            ChoicePrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Quel est votre moyen de transport."),
                choices=[Choice("Voiture"), Choice("Bus"), Choice("Vélo/trotinette")]))
    

    #------------------ Transport Step ------------------# 

    async def name_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["transport"] = step_context.result.value
        
        return await step_context.prompt(
            TextPrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Veillez entrer votre nom.")))
    

    #------------------ Name Step ------------------# 

    async def name_confirm_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["name"] = step_context.result
        await step_context.context.send_activity(MessageFactory.text(f"Thanks {step_context.result}"))

        return await step_context.prompt(ConfirmPrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Voulez-vous donner votre age ?")))
    
    #------------------ Age Step ------------------# 

    async def age_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if step_context.result:
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(prompt=MessageFactory.text("Entrez votre age."),
                    retry_prompt=MessageFactory.text("The value entered must be greater than 0 and less than 150.")))

        return await step_context.next(-1)
    
    #------------------ Age confirmation Step ------------------# 
    
    async def city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        age = step_context.result
        step_context.values["age"] = age
        msg = ("No age given." if step_context.result == -1 else f"I have your age as {age}.")
        await step_context.context.send_activity(MessageFactory.text(msg))
        
        return await step_context.prompt(
            TextPrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Quel est votre ville ?")))
    
    #------------------ City & picture Step ------------------# 

    async def picture_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["city"] = step_context.result

        if step_context.context.activity.channel_id == "msteams":
            # This attachment prompt example is not designed to work for Teams attachments, so skip it in this case
            await step_context.context.send_activity("Skipping attachment prompt in Teams channel...")

            return await step_context.next(None)

        # WaterfallStep always finishes with the end of the Waterfall or with another dialog; here it is a Prompt Dialog.
        prompt_options = PromptOptions(prompt=MessageFactory.text("Please attach a profile picture (or type any message to skip)."),
            retry_prompt=MessageFactory.text("The attachment must be a jpeg/png image file."))
        return await step_context.prompt(AttachmentPrompt.__name__, prompt_options)
    

    #------------------ Picture & Confirmation Step ------------------# 

    async def confirm_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["picture"] = (None if not step_context.result else step_context.result[0])

        return await step_context.prompt(ConfirmPrompt.__name__,
            PromptOptions(prompt=MessageFactory.text("Is this ok?")))

    async def summary_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if step_context.result:
            user_profile = await self.user_profile_accessor.get(step_context.context, UserProfile)

            user_profile.transport = step_context.values["transport"]
            user_profile.name = step_context.values["name"]
            user_profile.age = step_context.values["age"]
            user_profile.city = step_context.values["city"]
            user_profile.picture = step_context.values["picture"]

            msg = f"I have your mode of transport as {user_profile.transport}, {user_profile.city} is your City and your name as {user_profile.name}."
            
            if user_profile.age != -1:msg += f" And age as {user_profile.age}."

            await step_context.context.send_activity(MessageFactory.text(msg))

            if user_profile.picture:await step_context.context.send_activity(
                    MessageFactory.attachment(user_profile.picture, "This is your profile picture."))
                
            else:await step_context.context.send_activity("A profile picture was saved but could not be displayed here.")
        else:
            await step_context.context.send_activity(MessageFactory.text("Thanks. Your profile will not be kept."))

        # WaterfallStep always finishes with the end of the Waterfall or with another
        # dialog, here it is the end.
        return await step_context.end_dialog()
    


    #------------------ Fonctions de vérification ------------------# 

    @staticmethod
    async def age_prompt_validator(prompt_context: PromptValidatorContext) -> bool:

        # This condition is our validation rule. You can also change the value at this point.
        return (prompt_context.recognized.succeeded
            and 0 < prompt_context.recognized.value < 150)


    @staticmethod
    async def picture_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        if not prompt_context.recognized.succeeded:
            await prompt_context.context.send_activity("No attachments received. Proceeding without a profile picture...")
            # We can return true from a validator function even if recognized.succeeded is false.
            return True

        attachments = prompt_context.recognized.value
        valid_images = [
            attachment
            for attachment in attachments
            if attachment.content_type in ["image/jpeg", "image/png"]
        ]
        prompt_context.recognized.value = valid_images

        # If none of the attachments are valid images, the retry prompt should be sent.
        return len(valid_images) > 0
