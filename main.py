#!/usr/bin/python3

import telethon, datetime, os, sys
from configparser import ConfigParser

script_path = os.path.realpath(sys.argv[0])
(scriptdir, scriptname) = os.path.split(script_path)
os.chdir(scriptdir)
config = ConfigParser()
config.read('config', encoding='UTF-8')

api_id = config.get('DEFAULT', 'API_ID')
api_hash = config.get('DEFAULT', 'API_HASH')

min_members = int(config.get('DEFAULT', 'MIN_MEMBERS'))
preserve_period = int(config.get('DEFAULT', 'PRESERVE_PERIOD'))
preserve_pinned_messages = config.getboolean('DEFAULT', 'PRESERVE_PINNED_MESSAGES')
scan_only = config.getboolean('DEFAULT', 'SCAN_ONLY')
exclude_chats = []

with open('exclude_chats.txt', 'r') as f:
    for line in f.readlines():
        exclude_chats.append(int(line))

async def analyze_channel(client, channel, groups):
    for chat in channel.chats:
        name = chat.title
        id = chat.id
        if (isinstance(chat, telethon.tl.types.Chat) or chat.megagroup) and id not in exclude_chats:
            if isinstance(chat, telethon.tl.types.Chat):
                if chat.participants_count < min_members:
                    continue
            elif chat.megagroup:
                group = await client(telethon.functions.channels.GetFullChannelRequest(chat))
                if group.full_chat.participants_count < min_members:
                    continue
            if id in exclude_chats:
                print('Exclude', id, ':', name)
                continue
            if id not in groups:
                groups[id] = name

async def run(client):
    offset_datetime = datetime.datetime.now() - datetime.timedelta(hours=preserve_period)

    print('Scanning chats...')

    dialogs = await client.get_dialogs()
    groups = {}

    for dialog in dialogs:
        if isinstance(dialog.entity, telethon.tl.types.Chat):
            if dialog.entity.migrated_to:
                full = await client(telethon.functions.channels.GetFullChannelRequest(dialog.entity.migrated_to.channel_id))
                await analyze_channel(client, full, groups)
                continue
            if dialog.entity.participants_count < min_members:
                continue
            name = dialog.entity.title
            id = dialog.entity.id
            if id in exclude_chats:
                print('Exclude', id, ':', name)
                continue
            if id not in groups:
                groups[id] = name
        
        elif isinstance(dialog.entity, telethon.tl.types.Channel) and dialog.entity.megagroup == False:
            full = await client(telethon.functions.channels.GetFullChannelRequest(dialog.entity))
            await analyze_channel(client, full, groups)
    
    print('Scanning messages...')

    for id in groups:
        messages = []
        async for message in client.iter_messages(id, from_user='me', offset_date=offset_datetime):
            if preserve_pinned_messages and message.pinned:
                continue
            messages.append(message.id)

        if len(messages) == 0:
            continue

        print(id, ':', groups[id],':',len(messages))

        if not scan_only:
            await client.delete_messages(id, message_ids=messages, revoke=True)

with telethon.TelegramClient('anon', api_id, api_hash) as client:
    client.loop.run_until_complete(run(client))