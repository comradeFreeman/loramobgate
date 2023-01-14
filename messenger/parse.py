import sys
sys.path.insert(0, "device")
from dateutil import parser
from datetime import datetime, timedelta
from models import Chat, Message, Content
from classes import ContentType
from hashlib import md5
import json

with open('assets/test/data/chats.json') as f_obj:
    chats = json.load(f_obj)
    for chat in chats:
        part = {}
        for k,v in chats[chat]['participants'].items():
            part[int(k, 16)] = v
        chat_obj = Chat.get_or_create(id = int(chat, 16), defaults={"participants": part, "id": int(chat, 16), "display_name": chats[chat]['display_name']})[0]
        messages = chats[chat]['messages']
        for message in messages:
            text = chats[chat]['messages'][message]['message']
            m = Message.create(sender = int(chats[chat]['messages'][message]['from'], 16),
                                            recipient = 0xacde73bf,
                                            date_sent = parser.parse(chats[chat]['messages'][message]['timestamp']),
                                            date_received = parser.parse(chats[chat]['messages'][message]['timestamp']),
                                            forwarded_from = 0,
                                            reply_to = 0,
                                            chat = chat_obj,
                                            message_hash = md5(text.encode('utf-8')).hexdigest())
            c = Content.create(message = m,
                                            content_type = ContentType.TEXT,
                                            content = text) # TODO?
            m.save()
            c.save()

        chat_obj.last_message_id = m.get_id()
        chat_obj.save()
