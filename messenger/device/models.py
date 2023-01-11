from peewee import SqliteDatabase, IntegerField, DateTimeField, \
	ForeignKeyField, CompositeKey, BooleanField, BlobField, CharField, SmallIntegerField
from settings import DB_NAME, BROADCAST
from datetime import datetime, timedelta
from playhouse.signals import pre_save, Model
from enum import Enum
from classes import ContentType, MessageStatus

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


class Message(Model):
	alternative_id = CompositeKey('sender', 'recipient', 'date_sent')
	sender = IntegerField(column_name='sender', index=True, default=BROADCAST)
	recipient = IntegerField(column_name='recipient', index=True, default=BROADCAST)
	chat = CharField(column_name='chat', index=True)
	timestamp_sent = IntegerField(column_name='timestamp_sent_my', default=0, help_text=
																				"""Числовое поле, в которое последние
																				2 цифры означают десятки миллисекунд,
																				а остальные означают секунды, прошедшие 
																				от начала суток (относительно UTC)""")
	date_sent = DateTimeField(column_name='date_sent', default=datetime.utcnow())
	date_received = DateTimeField(column_name='date_received', default=datetime.utcnow())
	status = EnumField(enum=MessageStatus, column_name='status', default=MessageStatus.UNKNOWN)
	edited = BooleanField(column_name='edited', default=False)
	reply_to = IntegerField(column_name='reply_to', null=True)
	forwarded_from = IntegerField(column_name='forwarded_from', null=True)
	#content_id = IntegerField(column_name='content_id', null=True)


	class Meta:
		#primary_key = CompositeKey('sender', 'recipient', 'date_sent')
		table_name = 'messages'
		database = db

@pre_save(sender = Message)
def fill_message(model_class, message, created):
	if created:
		my_timestamp = str(message.timestamp_sent)
		new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)
		new_date += timedelta(seconds=int(my_timestamp[:-2]), milliseconds=(int(my_timestamp) % 100) * 10)
		now = datetime.utcnow()
		if new_date > now:
			new_date = new_date.replace(day = now.day - 1)
		message.date_sent = new_date
		message.chat = f"{message.sender}_{message.recipient}"

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
db.create_tables([Message, Content])
db.close()
