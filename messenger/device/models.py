import pickle

from peewee import SqliteDatabase, IntegerField, DateTimeField, \
	ForeignKeyField, CompositeKey, BooleanField, BlobField, CharField, SmallIntegerField, VirtualField
from settings import DB_NAME, BROADCAST
from datetime import datetime, timedelta, timezone
from playhouse.signals import pre_save, Model
from enum import Enum
from classes import ContentType, MessageStatus
from peewee import Field
from typing import Union
from hashlib import md5
from kivy.utils import platform

#from zoneinfo import ZoneInfo
#utc = #ZoneInfo('UTC')

#if platform == "android":
localtz = datetime.now().astimezone().tzinfo
#else:
#	import usb.core
#	localtz = ZoneInfo('localtime')

db = SqliteDatabase(DB_NAME, pragmas={ 'journal_mode': 'wal', 'cache_size': -1024 * 64 })


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
			return value.replace(tzinfo=timezone.utc).isoformat()

	def python_value(self, value: str) -> datetime:
		if value:
			return datetime.fromisoformat(value).astimezone(localtz)

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
	avatar = CharField(default="assets/icons/anonymus.jpg")

	class Meta:
		table_name = 'chats'
		database = db

class Message(Model):
	alternative_id = CompositeKey('sender', 'recipient', 'date_sent')
	sender = IntegerField(column_name='sender', index=True, default=BROADCAST)
	recipient = IntegerField(column_name='recipient', index=True, default=BROADCAST)
	chat = ForeignKeyField(model=Chat, on_delete='CASCADE', backref='messages')
	#CharField(column_name='chat', index=True)
	#timestamp_sent = IntegerField(column_name='timestamp_sent', default=0, help_text=
	#																			"""Числовое поле, в которое последние
	#																			2 цифры означают десятки миллисекунд,
	#																			а остальные означают секунды, прошедшие
	#																			от начала суток (относительно UTC)""")
	date_sent = TimestampTzField(column_name='date_sent', default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
	date_received = TimestampTzField(column_name='date_received', default=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
	status = EnumField(enum=MessageStatus, column_name='status', default=MessageStatus.UNKNOWN)
	edited = BooleanField(column_name='edited', default=False)
	reply_to = IntegerField(column_name='reply_to', null=True)
	forwarded_from = IntegerField(column_name='forwarded_from', null=True)
	message_hash = CharField(column_name="message_hash")
	#content_id = IntegerField(column_name='content_id', null=True)


	class Meta:
		table_name = 'messages'
		database = db

@pre_save(sender = Message)
def fill_message(model_class, message, created):
	if created:
		pass
		#my_timestamp = str(message.timestamp_sent)
		#new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)
		#new_date += timedelta(seconds=int(my_timestamp[:-2]), milliseconds=(int(my_timestamp) % 100) * 10)
		#now = datetime.utcnow()
		#if new_date > now:
		#	new_date = new_date.replace(day = now.day - 1)
		#message.date_sent = new_date
		#message.chat = f"{message.sender}_{message.recipient}"

class Content(Model):
	#id = ForeignKeyField(model=Message, field=Message.content_id, primary_key=True, on_delete='CASCADE', backref="content")
	message = ForeignKeyField(model=Message, on_delete='CASCADE', backref='content')
	ready = BooleanField(column_name='ready', index=True, default=True)
	content_type = EnumField(enum=ContentType, column_name='content_type', default=ContentType.UNKNOWN)
	content = BlobField(column_name='content_storage', null=True)

	class Meta:
		table_name = 'content'
		database = db

db.connect()
db.create_tables([Message, Content, Chat])
db.close()
