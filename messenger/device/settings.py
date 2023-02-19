import json
TX_POWER = 22

CURVE = 'secp224r1'
BROADCAST = 0xffffffff
PING_PERIOD = 30
PING_HOST = 'lain-is.online'
DB_NAME = 'loramessenger.db'
VID = 0x16c0
PID = 0x05dc
PROCESS_DELAY = 5
LOAD_CHATS_PERIOD = 30
LOAD_MESSAGES_PERIOD = 10
API_URL = 'https://api.lain-is.online/v1/'
TTL_NEIGHBOR = 30
TTL_TRANSACTION = 36
ASSETS_AVATARS = "./assets/avatars"
ASSETS_ICONS = "./assets/icons"
ASSETS_CERTS = "./assets/certs"
ASSETS_FONTS = "./assets/fonts"
FONT = "Roboto-Regular-Emoji.ttf"
DEFAULT_AVATAR = "anonymus.jpg"
APP_VERSION = "0.5.2"


settings_options = json.dumps([
	{'type': 'title',
	 'title': 'Device settings'},
	{'type': 'bool',
	 'title': 'Force LoRa',
	 'desc': 'Don\'t use Internet to send messages even it\'s available',
	 'section': 'appsettings',
	 'key': 'force_lora'},
	{'type': 'numeric',
	 'title': 'Process interval',
	 'desc': 'How often device have to process new messages',
	 'section': 'appsettings',
	 'key': 'poll_interval'},
	{'type': 'numeric',
	 'title': 'TX Power',
	 'desc': 'Output power of device. Note, that smaller power gives smaller distance your data can be received '
			 'by another users. Change this parameter carefully!',
	 'section': 'appsettings',
	 'key': 'tx_power'},
	{'type': 'title',
	 'title': 'Messenger settings (Note: applied after app restart)'},
	{'type': 'numeric',
	 'title': 'UI chats interval',
	 'desc': 'How often to renew chats',
	 'section': 'appsettings',
	 'key': 'ui_chats_interval'},
	{'type': 'numeric',
	 'title': 'UI messages interval',
	 'desc': 'How often to renew messages in chat',
	 'section': 'appsettings',
	 'key': 'ui_messages_interval'},

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
