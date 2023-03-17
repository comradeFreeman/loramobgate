import uuid
from peewee import SqliteDatabase, IntegerField, DateTimeField, \
	ForeignKeyField, CompositeKey, BooleanField, BlobField, CharField, SmallIntegerField, VirtualField

import settings
from settings import DB_MESSENGER, BROADCAST, ASSETS_CERTS, ASSETS_FONTS, ASSETS_AVATARS, DEFAULT_AVATAR
from os import path
from datetime import datetime, timedelta, timezone
from playhouse.signals import pre_save, Model
from enum import Enum
from classes import ContentType, MessageStatus
from peewee import Field
from typing import Union
from hashlib import md5
import pickle
import random
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

def generate_avatar(text, prev_name = None):
	if prev_name and settings.DEFAULT_AVATAR not in prev_name:
		name = prev_name
	else:
		name = path.join(ASSETS_AVATARS, f"{uuid.uuid4().hex}.png")
	font = ImageFont.truetype(path.join(ASSETS_FONTS, "Roboto-Regular-Emoji.ttf"), 144)
	img = Image.new("RGBA", (200,200),tuple(random.choices(range(160, 256), k=3)))
	draw = ImageDraw.Draw(img)
	draw.text((55, 15),text,tuple(random.choices(range(0,96), k=3)),font=font)
	draw = ImageDraw.Draw(img)
	img.save(name)
	return name

localtz = datetime.now().astimezone().tzinfo

db = SqliteDatabase(DB_MESSENGER, pragmas={'journal_mode': 'wal', 'cache_size': -1024 * 64, 'foreign_keys': 1})


class EnumField(SmallIntegerField):
	"""This class enables a Enum like field for Peewee."""
	def __init__(self, enum, *args, **kwargs):
		if not issubclass(enum, Enum):
			raise TypeError((f"{self.__class__.__name__} Argument enum must be"
							 f" subclass of enum.Enum: {enum} {type(enum)}."))
		self.enum = enum
		super().__init__(*args, **kwargs)

	def db_value(self, member):
		return member.value

	def get_enum(self):
		return self.enum

	def python_value(self, value):
		enum = self.get_enum()
		return enum(value)

	def coerce(self, value):
		enum = self.get_enum()
		if value not in enum:
			raise ValueError((f"{self.__class__.__name__} the value must be "
							  f"member of the enum: {value}, {enum}."))


class TimestampTzField(Field):
	"""
	A timestamp field that supports a timezone by serializing the value
	with isoformat.
	"""

	field_type = "TEXT"

	def db_value(self, value: datetime) -> str:
		if value:
			#print("DB_VALUE", value)
			return value.astimezone(timezone.utc).isoformat()

	def python_value(self, value: str) -> datetime:
		if value:
			#print("PYTHON_VALUE", value)
			return datetime.fromisoformat(value).astimezone(timezone.utc) #  localtz

class DictField(Field):
	"""
	MSG Pack in Blob field as Dict
	"""
	field_type = 'blob'
	_dict = {}

	class Dict:
		def __init__(self, data=None, dct=None):
			if dct:
				self.data = dct
				pass
			else:
				self.data: dict = pickle.loads(data) if data else {} # msgpack. , raw=False
				pass
			pass

		def __getitem__(self, item):
			return self.data.get(item, None)

		def __setitem__(self, key, value):
			self.data[key] = value
			pass

		def __repr__(self):
			return f"<DictField, keys: {', '.join(map(str, self.keys()))}>"

		def __iter__(self):
			return iter(self.data)

		def __delitem__(self, key):
			del self.data[key]

		def __bool__(self):
			return bool(self.data)

		def __dict__(self):
			return self.data

		def dump(self):
			return pickle.dumps(self.data) #msgpack

		def keys(self):
			return self.data.keys()

		def items(self):
			return self.data.items()

		def values(self):
			return self.data.values()

		def dict(self):
			return self.data
		pass

	def db_value(self, value: Union[Dict, dict]):
		return value.dump() if isinstance(value, self.Dict) else (self.Dict(dct=value)).dump()

	def python_value(self, value):
		return self.Dict(value)
	pass


class Chat(Model):
	id = IntegerField(unique=True, primary_key=True, column_name="chat")
	display_name = CharField(column_name='display_name', index=True, null=True)
	participants = DictField(column_name="participants")
	last_message_id = IntegerField(column_name="last", null=True)
	unread = IntegerField(column_name="unread", default=0)
	avatar = CharField(default = path.join(ASSETS_AVATARS,DEFAULT_AVATAR))

	class Meta:
		table_name = 'chats'
		database = db

@pre_save(sender = Chat)
def update_avatar(model_class, chat_obj: Chat, created):
	if not created: # and (DEFAULT_AVATAR in chat_obj.avatar or "custom" not in chat_obj.avatar):
		chat_prev: Chat = Chat.get(Chat.id == chat_obj.id)
		if chat_obj.display_name != chat_prev.display_name and "custom" not in chat_obj.avatar:
			chat_obj.avatar = generate_avatar(chat_obj.display_name[0], chat_prev.avatar)


class Message(Model):
	alternative_id = CompositeKey('sender', 'recipient', 'date_sent')
	sender = IntegerField(column_name='sender', index=True, default=BROADCAST)
	recipient = IntegerField(column_name='recipient', index=True, default=BROADCAST)
	chat = ForeignKeyField(model=Chat, on_delete='CASCADE', backref='messages')
	date_sent = TimestampTzField(column_name='date_sent', default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
	date_received = TimestampTzField(column_name='date_received', default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
	status = EnumField(enum=MessageStatus, column_name='status', default=MessageStatus.UNKNOWN)
	edited = BooleanField(column_name='edited', default=False)
	reply_to = IntegerField(column_name='reply_to', null=True)
	forwarded_from = IntegerField(column_name='forwarded_from', null=True)
	message_hash = CharField(column_name="message_hash",null=True, index=True)

	class Meta:
		table_name = 'messages'
		database = db

@pre_save(sender = Message)
def update_last(model_class, message_obj: Message, created):
	#if created:
	if message_obj.sender != message_obj.chat.id:
		message_obj.chat.unread = 0
		message_obj.chat.save()
	message_obj.chat.last_message_id = message_obj.id


class Content(Model):
	message = ForeignKeyField(model=Message, on_delete='CASCADE', backref='content')
	ready = BooleanField(column_name='ready', index=True, default=True)
	content_type = EnumField(enum=ContentType, column_name='content_type', default=ContentType.UNKNOWN)
	content = BlobField(column_name='content_storage', null=True)

	class Meta:
		table_name = 'content'
		database = db

@pre_save(sender = Content)
def update_messagehash(model_class, content_obj: Content, created):
	message_obj = Message.get(Message.id == content_obj.message)
	message_obj.message_hash = md5(
			message_obj.date_sent.isoformat()[:19].encode('utf-8') +
			pickle.dumps(content_obj.content)
	).hexdigest()
	message_obj.save()

db.connect()
db.create_tables([Message, Content, Chat])
db.close()
