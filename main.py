import telebot
import openai
import boto3
import config
from libs.stabilityApi import text_to_image
from pathlib import Path

openai.api_key = config.openai_api_key
def generate_response(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        temperature=0.7,
    )
    return response["choices"][0]["text"]

if config.voice_enabled:
    polly_client = boto3.Session(
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
        region_name=config.region_name
    ).client('polly')

    Path("audio").mkdir(parents=True, exist_ok=True)
    open("audio/response.mp3", "a").close()

bot = telebot.TeleBot(token=config.telegram_token)

engine_id = config.sd_engine_id
api_host = config.sd_api_host
api_key = config.sd_api_key

def generate_image(prompt):
    image = text_to_image(engine_id, api_host, api_key, prompt)
    return image

bot.set_my_commands([
    {
        "command": "/ask",
        "description": "You can ask anything"
    },
    {
        "command": "/draw",
        "description": "get the image content"
    },
    {
        "command": "/voice",
        "description": "question passed to ChatGPT and voice generated from Polly"
    }
])

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    AUTHORIZED_USER_IDS = config.telegram_users
    if message.from_user.id in AUTHORIZED_USER_IDS:
        text = message.text

        if text.startswith("/draw"):
            image = generate_image(text[len("/draw"):].strip())
            bot.send_photo(chat_id=message.chat.id, photo=image)
        else:
            if text.startswith("/ask") :
                response = generate_response(text)
                bot.send_message(chat_id=message.chat.id, text=response)
            elif text.startswith('/voice'):
                response = generate_response(text)
                bot.send_message(chat_id=message.chat.id, text=response)

                if text.startswith("/voice"):
                    audio = polly_client.synthesize_speech(
                        Text=response,
                        VoiceId='Lucia',
                        LanguageCode='en-GB',
                        Engine = 'neural',
                        OutputFormat="mp3"
                    )

                    audio_stream = audio["AudioStream"]
                    with open("audio/response.mp3", "wb") as file:
                        file.write(audio_stream.read())
                    with open("audio/response.mp3", "rb") as f:
                        bot.send_voice(chat_id=message.chat.id, voice=f)
            else:
                bot.send_message(chat_id=message.chat.id, text='Invalid Command')   
    else:
        bot.send_message(chat_id=message.chat.id, text='[you are not allowed]', parse_mode='MarkdownV2')

bot.polling()
