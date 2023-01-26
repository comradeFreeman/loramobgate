from enum import Enum

class MessageStatus(Enum):
	UNKNOWN = 0
	SENDING = 1
	SEND_ERROR = 2
	SENT = 3
	READ = 4
	INVALID = 127

	@classmethod
	def _missing_(cls, value):
		return cls.INVALID

	def __bool__(self):
		return self not in {self.UNKNOWN, self.INVALID}

class ContentType(Enum):
	UNKNOWN = 0
	TEXT = 10
	VOICE = 11
	IMAGE = 12
	AUDIO = 13
	MESSAGE_STATUS = 14
	MESSAGE_OPTIONS = 15
	EMERGENCY = 19
	# 10-19 всё, что касается моего мессенджера
	L3NEIGHBORINFO = 20
	L3KEYEX = 21 # периодическая отправка своего ключа или ретрансляция ответа на L3KEYRQ
	L3KEYRQ = 22 # запрос ключа по dev_addr
	L3CNFRP = 23
	# 20-29 всё, что касается сети
	LORA = 30
	# 30-39 всё, что касается Лоры
	INVALID = 255

	@classmethod
	def _missing_(cls, value):
		return cls.INVALID

	def __bool__(self):
		return self not in {self.UNKNOWN, self.INVALID}


class AppID(Enum):
	UNKNOWN = 0  # fallback
	MESSENGER = 1  # моё приложение для коммуникации
	NETWORK = 2  # сообщения о состоянии сети
	LORA = 3  # пересылка принятых от датчиков сообщений
	INVALID = 15

	@classmethod
	def _missing_(cls, value):
		return cls.INVALID

	def __bool__(self):
		return self not in {self.UNKNOWN, self.INVALID}


class Chip(Enum):
	UNKNOWN = 0
	SX126X = 6
	SX127X = 7
	SX1262 = 62
	SX1268 = 68
	SX1278 = 78

	@classmethod
	def _missing_(cls, value):
		return cls.UNKNOWN

	def __bool__(self):
		return self is not self.UNKNOWN


class TypeSizes(Enum):
	B = 1
	H = 2
	I = 4

	@classmethod
	def _missing_(cls, value):
		return cls.B


class NetPacketDirection(Enum):
	IN = 0
	OUT = 1

	@classmethod
	def _missing_(cls, value):
		return cls.IN
