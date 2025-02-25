from aiogram import Dispatcher
from aiogram import types
from aiogram.dispatcher.filters import CommandStart, CommandHelp
from action_sender import ChatActionSender
from helpers import *
import subprocess
from aiogram.types import ParseMode
import operator
from functools import reduce, partial
import io
import asyncio
import logging
import re
import os

try:
    import chat_gpt_handlers
    allow_openai = True
except:
    allow_openai = False

try:
    import whisper_voice
except:
    logging.warning('whisper not imported')

def random_action_needed():
    return random_bool(0.05)

TG_MAX_MESSAGE_LEN = 3900

def setup(dp: Dispatcher):
    dp.register_message_handler(bot_help, CommandHelp())
    dp.register_message_handler(cmd_call, commands=['call'])
    dp.register_message_handler(ask_call, commands=['ask'])
    dp.register_message_handler(version_call, commands=['version'])
    dp.register_message_handler(logs_call, commands=['logs'])
    dp.register_message_handler(cmd_groups, commands=['groups'])
    dp.register_message_handler(cmd_create, commands=['create'])
    dp.register_message_handler(
        voice_listener, content_types=types.ContentTypes.VOICE)
    dp.register_message_handler(
        video_listener, content_types=types.ContentTypes.VIDEO)
    dp.register_message_handler(
        message_listener, content_types=types.ContentTypes.ANY)


async def bot_help(msg: types.Message):
    text = [
        'Список команд: ',
        '/call \- вызвать группу',
        '/groups \- посмотреть группы',
        '/create \- создать группу',
        '/version \- узнать версию',
        '/ask \- спросить',
    ]
    groups = get_groups(msg.chat.id)
    res = []
    for key, items in sorted(groups.items(), key=lambda x: x[0]):
        res.append('/'+key + ' \- Призвать ' +
                   group_to_str(items, not_call=True, sep=', '))

    text += res

    await msg.reply('\n'.join(text))


async def cmd_call(msg: types.Message):
    groups = get_groups(msg.chat.id)

    command, group_name = msg.get_full_command()

    logging.info('group name:', group_name)
    if group_name in groups:
        await msg.reply(group_to_str(groups[group_name]))
    else:
        await msg.reply('Такой группы пользователей не существует')


async def version_call(msg: types.Message):
    result = subprocess.Popen(
        'git log -1 --pretty="by <b>%cN</b>, %ar%ntitle: %Bcommit: <i>%H</i>"',
        shell=True, stdout=subprocess.PIPE).stdout.read()
    result = result.decode('utf-8', errors='ignore')
    await msg.reply(result, ParseMode.HTML)

async def logs_call(msg: types.Message):
    if msg.from_user.username not in {'avdosev', 'unterumarmung'}:
        return
    result = subprocess.Popen(
        'tail -n 20 bot_logs.txt',
        shell=True, stdout=subprocess.PIPE).stdout.read()
    result = result.decode('utf-8', errors='ignore')

    await msg.reply(logs_prepare(result), ParseMode.HTML)

def logs_prepare(s: str) -> str:
    lines = s.split('\n')
    for i in indexes(lines):
        if lines[i].startswith(tuple(str(i) for i in range(10))):
            subsline = lines[i].split()
            lines[i] = ' '.join([f'<b>{subsline[0]}</b>', *subsline[1:]])
    return '\n'.join(lines)


def get_group(chat_id, group_name):
    groups = get_groups(chat_id)
    if group_name in groups:
        return groups[group_name]
    return None


def group_to_str(group: list[str], not_call=False, sep=' '):
    res = []
    for username in sorted(group):
        if username.startswith('@') or not_call:
            res.append(username)
        else:
            res.append('@'+username)
    return sep.join(res).replace('_', '\_')


async def cmd_groups(msg: types.Message):
    groups = get_groups(msg.chat.id)
    res = []
    for key, items in sorted(groups.items(), key=lambda x: x[0]):
        res.append(key + ' \- ' + group_to_str(items, not_call=True))

    if len(res):
        await msg.reply('\n'.join(res))
    else:
        await msg.reply('групп нет')


async def cmd_create(msg: types.Message):
    command, text = msg.get_full_command()
    args = text.split()
    group_name = args[0]
    values = args[1:]

    for i in range(len(values)):
        value = values[i]
        if value.startswith('@'):
            value = value[1:]
            values[i] = value

    if len(group_name) and len(values):
        add_groups(msg.chat.id, group_name, values)
        await msg.reply('группа создана')


async def message_listener(msg: types.Message):
    command = msg.get_command()
    if command is not None:
        group_name = command[1:]
        group = get_group(msg.chat.id, group_name)
        if group:
            message = msg.reply_to_message if msg.reply_to_message else msg
            await do_call(message, group_name)
            return

    msg_text = msg.caption if msg.text is None else msg.text
    if msg_text is None:
        logging.info(msg)
        return

    groups = get_groups(msg.chat.id)
    msg_text = msg_text.lower()
    
    if 'ты лох' in msg_text or 'лох ты' in msg_text or msg_text == 'лох':
        await msg.reply('нет, ты лох')

    if 'некит лох' in msg_text:
        await msg.reply('сам лох')

    if 'некит обосрался' in msg_text or 'некит опять обосрался' in msg_text:
        await msg.reply('не обосрался, а провел внеплановую дефекацию')

    if 'ты обосрался' in msg_text:
        await msg.reply('пока куча дерьма только у тебя в штанах')

    if 'ладно' == msg_text:
        await msg.reply('ебать ты лох, а гонора то было')
    
    if 'я лох' in msg_text:
        if msg.from_user.username == 'unterumarmung':
            await msg.reply('да, ты лох')
        else:
            await msg.reply('нет, ты пупсик')

    if '?' == msg_text:
        await msg.reply('что тебе неясно, хуила?')
    
    if '!' == msg_text:
        await msg.reply('\.')
    
    if 'извините' == msg_text:
        await msg.reply('Рамзан Кадыров услышал тебя')

    if 'да' == msg_text:
        if random_action_needed():
            await msg.reply('пизда') 
    
    if 'нет' == msg_text:
        if random_action_needed():
            await msg.reply('пидора ответ') 

    if any((variant == msg_text or len(re.findall(f'(^|\\s){variant}{{1,}}\\?$', msg_text)) for variant in  ('чо', 'че', 'чё'))):
        await msg.reply('Хуй через плечо')
    
    if msg_text.endswith('300'):
        if random_action_needed():
            await msg.reply('отсоси у тракториста') 

    groups_to_call = []
    for group_name in groups:
        if ('@'+group_name.lower()) in msg_text:
            groups_to_call.append(group_name)


    if not len(groups_to_call):
        return

    message = msg.reply_to_message if msg.reply_to_message else msg
    group = list(
        reduce(
            operator.or_, 
            map(lambda x: set(get_group(message.chat.id, x)), groups_to_call),
            set()
        )
    )
    
    await do_call_group(message, group)



async def do_call(msg: types.Message, group_name):
    group = get_group(msg.chat.id, group_name)
    await do_call_group(msg, group)

async def do_call_group(msg: types.Message, group):
    group = exclude_msg_author(group, msg.from_user)

    if not len(group):
        await msg.reply('Ты ни кого не призвал, дебилыч')
        return

    logging.info('Group: ', group_to_str(group))
    await msg.reply(group_to_str(group))


def exclude_msg_author(group, user: types.User):
    return [username for username in group if user.username != username]

async def ask_call(msg: types.Message):
    if not allow_openai:
        await msg.reply('пока не ебу')
        return
    
    command, text = msg.get_full_command()

    context = []
    if msg.reply_to_message:
        context_msg = msg.reply_to_message
        role = 'assistant' if context_msg.from_user.is_bot else 'user'
        context_text = context_msg.caption if context_msg.text is None else context_msg.text
        context = chat_gpt_handlers.simple_context(context_text, role=role)
        logging.info(context)

    try:
        response = chat_gpt_handlers.get_answer(text, context=context)
        logging.info(response)
        await msg.reply(response, parse_mode=ParseMode.MARKDOWN)
    except Exception as err:
        await msg.reply('я завершился с ошибкой, попробуй ещё раз')
        await msg.answer(prepare_text(str(err)))


def prepare_text(text: str):
    return text.replace('-', '\-').replace('_', '\_').replace('.', '\.')


async def voice_listener(msg: types.Message):
    logging.info(msg)
    async with ChatActionSender.typing(bot=msg.bot, chat_id=msg.chat.id):
        voice = io.BytesIO()
        _ = await msg.voice.download(destination_file=voice, timeout=180)
        text = await whisper_voice.transcribe(voice, f"voice:{msg.voice.file_id}")
        answer_message(msg, text)

async def video_listener(msg: types.Message):
    logging.info(msg)
    async with ChatActionSender.typing(bot=msg.bot, chat_id=msg.chat.id):
        video = io.BytesIO()
        await msg.video.download(destination_file=video, timeout=180)
        audio = video_to_audio(video)
        text = await whisper_voice.transcribe(audio, f"video:{msg.video.file_id}")
        answer_message(msg, text)

async def video_to_audio(video: io.BytesIO):
    logging.info("starting to convert video...")
    with open("temp_video", "wb") as f:
        f.write(video.getbuffer())

    # extract audio stream without re-encoding
    command = "ffmpeg -i ./temp_video -vn -acodec copy temp_audio.wav"
    proc = asyncio.create_subprocess_shell(command)
    await proc.communicate()

    with open("temp_audio.wav", "rb") as f:
        audio = BytesIO(f.read())

    os.remove("temp_video")
    os.remove("temp_audio.wav")

    logging.info("video converted")
    return audio

async def answer_message(msg, text):
    if len(text) <= TG_MAX_MESSAGE_LEN:
        await msg.reply('<b>' + msg.from_user.username + '</b>:\n' + text, ParseMode.HTML)
    else:
        chunks = split_text_to_chunks(text, TG_MAX_MESSAGE_LEN) 
        first_chunk = chunks[0]
        answer = await msg.reply('<b>' + msg.from_user.username + '</b>:\n' + first_chunk + ' ...', ParseMode.HTML)    
        for chunk in chunks[1:]:
            answer = await answer.reply(chunk, ParseMode.HTML)
