import json
TX_POWER = 22

CURVE = 'secp224r1'
BROADCAST = 0xffffffff
PING_INTERVAL = 30
PING_URL = 'https://lain-is.online/ping'
DB_MESSENGER = 'loramessenger.db'
DB_DATA = "data.db"
VID = 0x16c0
PID = 0x05dc
CHECK_INTERVAL = 0.8
PROCESS_INTERVAL = 5
UI_CHATS_INTERVAL = 30
UI_MESSAGES_INTERVAL = 10
API_URL = 'https://api.lain-is.online/v1/lmg'
PACKET_ENDPOINT = "/device/packets/"
API_POLL_INTERVAL = 10
TTL_NEIGHBOR = 30
TTL_TRANSACTION = 36
ASSETS_AVATARS = "./assets/avatars"
ASSETS_ICONS = "./assets/icons"
ASSETS_CERTS = "./assets/certs"
ASSETS_FONTS = "./assets/fonts"
FONT = "Roboto-Regular-Emoji.ttf"
DEFAULT_AVATAR = "anonymous.jpg"
APP_VERSION = "0.8.3"

DEBUG = True

settings_options = json.dumps([
	{'type': 'title',
	 'title': 'Device settings'},
	{'type': 'bool',
	 'title': 'Force LoRa',
	 'desc': 'Don\'t use Internet to send messages even it\'s available (applied immediately)',
	 'section': 'appsettings',
	 'key': 'FORCE_LORA'},
	{'type': 'numeric',
	 'title': 'Process interval',
	 'desc': 'How often device have to process packets in queues',
	 'section': 'appsettings',
	 'key': 'PROCESS_INTERVAL'},
	{'type': 'numeric',
	 'title': 'TX Power',
	 'desc': 'Output power of device. Note, that smaller power gives smaller distance your data can be received '
			 'by another users. Change this parameter carefully!',
	 'section': 'appsettings',
	 'key': 'TX_POWER'},
	{'type': 'numeric',
	 'title': 'Poll interval',
	 'desc': 'How often to poll packets from server (if Internet available)',
	 'section': 'appsettings',
	 'key': 'API_POLL_INTERVAL'},
	{'type': 'title',
	 'title': 'Messenger settings'},
	{'type': 'numeric',
	 'title': 'UI chats interval',
	 'desc': 'How often to renew chats',
	 'section': 'appsettings',
	 'key': 'UI_CHATS_INTERVAL'},
	{'type': 'numeric',
	 'title': 'UI messages interval',
	 'desc': 'How often to renew messages in chat',
	 'section': 'appsettings',
	 'key': 'UI_MESSAGES_INTERVAL'},


	{'type': 'options',
	 'title': 'An options setting',
	 'desc': 'Options description text',
	 'section': 'appsettings',
	 'key': 'optionsexample',
	 'options': ['option1', 'option2', 'option3']},
	{'type': 'string',
	 'title': 'A string setting',
	 'desc': 'String description text',
	 'section': 'appsettings',
	 'key': 'stringexample'},
	{'type': 'path',
	 'title': 'A path setting',
	 'desc': 'Path description text',
	 'section': 'appsettings',
	 'key': 'pathexample'},
	{'type': 'title',
	 'title': f'LoraMessenger: {APP_VERSION}'}
])


LOGGING_CONF = {
	"disable_existing_loggers": False,
	"version": 1,
	"formatters": {
		"verbose": {
			"format": "%(levelname)-8s %(asctime)s.%(msecs)03d [%(name)s.%(filename)s:%(funcName)s:%(lineno)d] %(message)s",
			"datefmt": "%Y-%m-%d %H:%M:%S",
		},
		"brief": {
			"format": "%(levelname)-8s %(asctime)s %(name)-16s %(message)s",
		}
	},
	"handlers": {
		"console": {
			"level": "DEBUG",
			"class": "logging.StreamHandler",
			"formatter": "verbose" if DEBUG else "brief",
		},
		"file": {
			"level": "DEBUG",
			"class": "logging.FileHandler",
			"formatter": "verbose" if DEBUG else "brief",
			"filename": "loramobgate.log",
			"mode": "w"
		},
	},
	"loggers": {
		"loramobgate": {
			"level": "DEBUG" if DEBUG else "INFO",
			"handlers": ["console", "file"],
		},
	},
}