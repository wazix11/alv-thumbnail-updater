from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
from dotenv import load_dotenv
import asyncio
import queue
import os

load_dotenv()

APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
USERNAME = os.getenv('USERNAME')

waiting_for_ptz_presets = False
presets_callback = None
chat_instance = None
loop = None
message_queue = queue.Queue()

def set_presets_callback(cb):
    global presets_callback
    presets_callback = cb

# this will be called when the event READY is triggered, which will be on bot start
async def on_ready(ready_event: EventData):
    print('Bot is ready for work, joining channels')
    # join our target channel, if you want to join multiple, either call join for each individually
    # or even better pass a list of channels as the argument
    await ready_event.chat.join_room(TARGET_CHANNEL)

async def ptzlist(cmd: ChatCommand):
    global waiting_for_ptz_presets
    if cmd.user.name == USERNAME.lower():
        print(f'in {cmd.room.name}, {cmd.user.name} ran ptzlist command with parameter: {cmd.parameter}')
        waiting_for_ptz_presets = True  # Set the flag when !ptzlist is run

# this will be called whenever a message in a channel was send by either the bot OR another user
async def on_message(msg: ChatMessage):
    global waiting_for_ptz_presets, presets_callback
    print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')
    message_queue.put(f'{msg.user.name}: {msg.text}')
    if waiting_for_ptz_presets and msg.text.startswith("PTZ Presets:"):
        print("Detected PTZ Presets message!")
        
        presets = msg.text.replace('PTZ Presets:', '').strip()
        presets = presets.split(',')
        print(presets)

        waiting_for_ptz_presets = False  # Reset the flag
        if presets_callback:
            # print("Calling presets_callback with:", presets)
            presets_callback(presets)

async def send_message(message):
    global chat_instance
    print(chat_instance)
    print(message)
    if chat_instance:
        try:
            await chat_instance.send_message(TARGET_CHANNEL, message)
            message_queue.put(f'{USERNAME.lower()}: {message}')
            print("Message sent!")
        except Exception as e:
            print(f"Error sending message: {e}")
    # Send the message to the chat
    # await chat.send_message(message)

# this is where we set up the bot
async def run():
    global chat_instance, loop
    loop = asyncio.get_event_loop()
    # set up twitch api instance and add user authentication with some scopes
    twitch = await Twitch(APP_ID, APP_SECRET)
    auth = UserAuthenticator(twitch, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

    # create chat instance
    chat = await Chat(twitch)
    chat_instance = chat

    # register the handlers for the events you want

    # listen to when the bot is done starting up and ready to join channels
    chat.register_event(ChatEvent.READY, on_ready)
    # listen to chat messages
    chat.register_event(ChatEvent.MESSAGE, on_message)
    # there are more events, you can view them all in this documentation

    # you can directly register commands and their handlers, this will register the !reply command
    chat.register_command('ptzlist', ptzlist)


    # we are done with our setup, lets start this bot up!
    chat.start()

    # lets run till we press enter in the console
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        # now we can close the chat bot and the twitch api client
        chat.stop()
        await twitch.close()

if __name__ == '__main__':
    # lets run our setup
    asyncio.run(run())