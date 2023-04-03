import json
from enum import Enum
import threading

from time import sleep
import usb.util as u
from typing import Union
import queue
from collections.abc import Iterable
import random
from math import ceil, log2
from struct import unpack, pack
import traceback
import pickle
import anytree.cachedsearch
from anytree import Node, LevelOrderIter, LevelGroupOrderIter
import threading
import ssl
from datetime import datetime, timezone, timedelta
import tinyec.ec as ec
import tinyec.registry as reg
from pure_salsa20 import salsa20_xor, xsalsa20_xor
from os import urandom
import settings
from classes import NetPacketDirection, AppID, Chip, TypeSizes, ContentType
from hashlib import sha256, md5
from anytree.exporter import JsonExporter
from os import path, environ
import declarations as s
import requests
import logging
logger = logging.getLogger("loramobgate.device")
from sqlitedict import SqliteDict
pubkeys = SqliteDict(settings.DB_DATA, tablename="pubkeys") #, autocommit=True)

#from kivy.utils import platform
platform = "unknown"

#if platform == "android":
if 'ANDROID_ARGUMENT' in environ: # <- equivalent
	platform = "android"
	from android.permissions import request_permissions, Permission
	request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
						 Permission.READ_EXTERNAL_STORAGE,
						 Permission.RECORD_AUDIO,
						 Permission.INTERNET])
	import usb4a.usb
else:
	import usb.core




def try_pickle(value):
	try:
		return pickle.loads(value)
	except:
		return None

def compress_point(point: ec.Point):
	return str(point.x + point.y % 2 + 461)


lock = threading.Lock()
ltz = datetime.now().astimezone().tzinfo

# класс, добавляющий в наследуемый класс функционал автоудаления объекта через указанное время
class NodeExtended(Node):
	def __init__(self, *args, **kwargs):
		self._ttl = kwargs.pop('ttl', 600)
		super(NodeExtended, self).__init__(*args, **kwargs)
		self._thread = threading.Thread(target = self.delete, daemon = True)
		if not super().is_root:
			self._thread.start()

	def delete(self):
		sleep(self._ttl)
		self.parent = None


class RepeatTimer(threading.Timer):
	def run(self):
		while not self.finished.wait(self.interval):
			self.function(*self.args, **self.kwargs)


class NetPacket:
	dev_addr = 0
	def __init__(self, source_packet=None, **kwargs):
		self.source_packet = source_packet
		self._packet = bytearray()
		self.src_addr = kwargs.get('src_addr', self.dev_addr)
		self.dst_addr = kwargs.get('dst_addr', settings.BROADCAST)
		self.fragm_c = kwargs.get('fragm_c', 0)
		self.fragment = kwargs.get('fragment', 0)
		self.app_id = kwargs.get('app_id', AppID.UNKNOWN)
		self.content_type = kwargs.get('content_type', ContentType.UNKNOWN)
		self.raw_data = kwargs.get('raw_data', bytes())
		self.pydc = kwargs.get('pydc', len(self.raw_data) + 1)
		self.direction = kwargs.get('direction', NetPacketDirection.IN)
		self.try_radio = kwargs.get("try_radio", False)

		if source_packet and isinstance(source_packet, Iterable):
			self.src_addr, self.dst_addr, self.fragm_c, self.fragment, self.app_id, self.pydc, self.content_type = \
				unpack("<2I5B", bytes(source_packet[:13]))
			self.raw_data = bytes(source_packet[13:13 + self.pydc])
			self.update()

	def __str__(self) -> str:
		return ".".join([str(el) for el in self.packet])

	def __eq__(self, other) -> bool:
		if isinstance(other, NetPacket):
			return self.packet == other.packet
		return False

	def __hash__(self) -> int:
		return hash(str(self.packet))

	@property
	def hashsum(self) -> bytes:
		return md5(self.packet).digest()

	def __setattr__(self, key, value):
		if key == "content_type" and not isinstance(value, ContentType):
			value = ContentType(value)
		elif key == "app_id" and not isinstance(value, AppID):
			value = AppID(value)
		elif key == "raw_data" and not isinstance(value, bytes):
			value = bytes(value)
			self.pydc = len(value) + 1

		self.__dict__[key] = value

	@property
	def is_default(self) -> bool:
		return not (set(self.packet) == {255, self.dev_addr})
	# проверяет, что это пустой пакет и создан с нуля без аргументов.

	@property
	def is_valid(self) -> bool:
		return self.content_type.value // 10 == self.app_id.value and \
			   self.pydc == len(self.raw_data) + 1 and \
			   self.content_type != ContentType.INVALID and \
			   self.app_id != AppID.INVALID # encrypted_data
	# проверяет, что пакет, созданный из набора байт, является валидным. Грубый способ отделить LoRa

	@property
	def packet(self):# -> list:
		if self.is_valid:
			# если мы успешно спарсили пакет и это пакет нашего формата
			self.update()
			return bytes(self._packet)
		elif self.source_packet:
			# иначе отдаём то, что пришло изначально пришло на вход
			return self.source_packet
		else:
			return bytes() #[]


	@property
	def dict(self) -> dict:
		return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

	@property
	def is_fragmented(self) -> bool:
		return bool(self.fragm_c)

	def update(self):
		self._packet = bytearray(pack(f"<2I5B", self.src_addr, self.dst_addr, self.fragm_c, self.fragment,
									  self.app_id.value, self.pydc, self.content_type.value))
		self._packet.extend(self.raw_data) # encrypted_data

	def swap_addr(self, from_me = False):
		# меняем местами адреса источника и назначения.
		# если задан адрес этого устройства, то подставляем его в источник
		self.src_addr, self.dst_addr = self.dev_addr if from_me else self.dst_addr, self.src_addr

	def swap_direction(self):
		self.direction = NetPacketDirection(not self.direction.value)

	def duplicate(self):
		return NetPacket(source_packet = self.packet, direction = self.direction)

class Transaction(threading.Thread):
	def __init__(self, *args, transaction_dict: dict, packet: NetPacket, ttl, queue: queue.Queue = None,**kwargs: dict):
		self.ttl = ttl
		self.transaction_dict = transaction_dict
		self.packet = packet
		self.packet_hash = packet.hashsum
		self._queue = queue
		super(Transaction, self).__init__(*args, **kwargs)

	def run(self):
		self.transaction_dict.update({self.packet_hash: self.packet})
		for i in range(4):
			sleep(self.ttl >> 2) # ttl/4
			if self.packet_hash in self.transaction_dict and self._queue \
					and self.packet.direction == NetPacketDirection.OUT \
					and self.packet.app_id == AppID.MESSENGER:
				logger.debug(f"No confirmation received for {self.packet.packet}")
				dupl = self.packet.duplicate()
				if i % 2: # 1,3
					dupl.try_radio = True
				self._queue.put(dupl)
		else:
			if self.packet_hash in self.transaction_dict:
				del self.transaction_dict[self.packet_hash]

class InternetConnection:
	def __init__(self, username, password, ping_interval = settings.PING_INTERVAL):
		self._avail = False
		self._username = username
		self._password = password
		self._ping_interval = ping_interval
		self._token = None
		self._check_inet_thread = RepeatTimer(self._ping_interval, self._check_inet)
		self._token_update_interval = 60
		self._token_thread = None
		self._check_inet_thread.start()
		self._update_token()

	@property
	def available(self):
		return self._avail

	def _check_inet(self):
		try:
			r = requests.head(settings.PING_URL)
			if r.status_code == 200:
				self._avail = True
				return
			raise
		except Exception:
			self._avail = False

	def _update_token(self):
		try:
			r = requests.post(settings.API_URL + "/token", data = {"username": self._username, "password": self._password})
		except: self._token_update_interval = 60
		else:
			self._avail = True
			self._token = r.json().get("access_token")
			self._token_update_interval = r.json().get("expires_in")
		finally:
			if not self._token_thread:
				self._token_thread = RepeatTimer(self._token_update_interval, self._update_token) 
				self._token_thread.start()

	def request(self, uri = "/", packet: NetPacket = None):
		try:
			func = requests.post if packet else requests.get
			r = func(settings.API_URL + uri, data = json.dumps({
					"sender": packet.src_addr,
					"recipient": packet.dst_addr,
					"timestamp": datetime.now().replace(tzinfo = ltz).isoformat(),
					"packet": packet.packet.hex()
			}) if packet else None,
				headers = {"Authorization": f"Bearer {self._token}"})
			if r.status_code == 401: # unauthorized
				self._update_token()
			if r.status_code != 200:
				raise
		except:
			logger.error(traceback.format_exc())
		else:
			self._avail = True
			return r.json()
		return False

	def stop(self):
		self._check_inet_thread.cancel()
		self._token_thread.cancel()


class Network:
	dev_addr = 0
	def __init__(self, packets_queue, keys, ttl_neighbor=settings.TTL_NEIGHBOR, ttl_transactions=settings.TTL_TRANSACTION):
		self._keys: Keys = keys
		self._last_transactions = {}
		self._packets_queue: queue.Queue = packets_queue
		self.ttl_neighbor = ttl_neighbor
		self.ttl_transactions = ttl_transactions
		self._share_neighbors_thread = RepeatTimer(self.ttl_neighbor, self._share_neighbors)
		self._share_pubkey_thread = RepeatTimer(self.ttl_neighbor * 2, self._share_my_pubkey)
		self._root_node = NodeExtended(name = self.dev_addr)
		self._share_neighbors_thread.start()
		self._share_pubkey_thread.start()

	def stop(self):
		self._share_pubkey_thread.cancel()
		self._share_neighbors_thread.cancel()

	################################### NEIGHBORS
	def neighbors(self, maxlevel: Union[int, None] = 5, include_root = False, jsonify = False) -> Union[list, str]:
		if jsonify:
			return JsonExporter(sort_keys = True).export(self._root_node)
		return [ node.name for node in LevelOrderIter(self._root_node, maxlevel = maxlevel) ][int(not include_root):]

	def add_neighbor(self, source, new_neighbor):
		# если такого соседа нет
		if not anytree.cachedsearch.find(self._root_node, lambda node: node.name == new_neighbor):
			# есть предок нового соседа есть в дереве
			if source_node := anytree.cachedsearch.find(self._root_node, lambda node: node.name == source):
				NodeExtended(name = new_neighbor,
							 parent = source_node,
							 ttl = self.ttl_neighbor * 3)

			# значит, это сосед первого ранга
			# не факт, конечно. может так статься, что более дальний сосед пошлёт пакет раньше, чем ближний
			# и выйдет, что они в дереве будут на одном уровне (хотя в действительности нет).
			# но есть надежда, что спустя время это будет исправлено автоматически.
			# а с другой стороны почему бы не считать всех, от кого в состоянии принять данные напрямую, первым рангом?
			else:
				# добавляем прежде всего источник
				new_node = NodeExtended(name = source,
										parent = self._root_node,
										ttl =self.ttl_neighbor * 3)
				# если новая запись тоже источник, то пропускаем, иначе заносим к узлу источника
				if source != new_neighbor:
					NodeExtended(name = new_neighbor,
								 parent = new_node,
								 ttl =self.ttl_neighbor * 3)

			# коррекция дерева. если на более отдалённом уровне есть такой же сосед, то мы его оттуда убираем
			# all_neighbors = list(LevelGroupOrderIter(self._root_node))[1:]
			# for level, neighbors in enumerate(all_neighbors, 1):
			# 	for neighbor in neighbors:
			# 		if neighbor in all_neighbors[level - 1]:
			# 			neighbor.parent = None

	def remove(self, name):
		if source_node := anytree.cachedsearch.find(self._root_node, lambda node: node.name == name):
			source_node.parent = None

	def _share_neighbors(self):
		self._packets_queue.put(NetPacket(
				src_addr = self.dev_addr,
				app_id = AppID.NETWORK,
				content_type = ContentType.L3NEIGHBORINFO,
				raw_data = pickle.dumps(self.neighbors(include_root = True)),
				direction = NetPacketDirection.OUT
			))

	################################### NETWORK
	def process_network_event(self, packet):
		logger.info(f"New network event of type {packet.app_id}")
		if packet.is_valid and packet.app_id == AppID.NETWORK and packet.direction == NetPacketDirection.IN:
			logger.debug(f"Proccessing: {packet.content_type} {packet.raw_data.hex()}")
			match packet.content_type:
				case ContentType.L3CNFRP:
					if packet.raw_data in self._last_transactions: # =hash in last_transactions
						del self._last_transactions[packet.raw_data]
					return
				case ContentType.L3NEIGHBORINFO:
					# сначала обработать (обновить своё дерево),
					# а потом уже слать своё!
					# ни в коем случае не пересылать этот пакет.
					for record in (try_pickle(packet.raw_data) or []):
						self.add_neighbor(packet.src_addr, record)
					return # выходим, чтобы не пересылать дальше
					# информация о соседях, пускай 10 записей таблицы
				case ContentType.L3KEYEX:
					# опасно. обновляем хранилище ключей на пришедший распарсеный словарь
					if data:= try_pickle(packet.raw_data):
						for dev_addr, public_key in data.items():
							# пускай цикл, чем костыли, чтобы получить из словаря 2 аргумента
							# ну и на будущее задел, вдруг решу по несколько слать.
							self._keys.add_key(dev_addr = dev_addr, public_key = public_key)
						# обработка периодической рассылки ключей/ретрансляция ответов на запросы
				case ContentType.L3KEYRQ:
					if value := self._keys.get_pk(int.from_bytes(packet.raw_data, byteorder='little')):
						packet.swap_addr(from_me = True)
						packet.content_type = ContentType.L3KEYEX
						packet.raw_data = pickle.dumps({packet.raw_data: value})
						# сформировать пакет L3KEYEX, в который поместить сериализованный словарь "адрес-ключ"
			# поменять направление на отправку
			packet.swap_direction()
			# переслать дальше
			self._packets_queue.put(packet)
			# запрос к соседям о публичных ключах для нужного devAddr. или переслать чей-то запрос дальше

	def _share_my_pubkey(self):
		self._packets_queue.put(NetPacket(
			src_addr = self.dev_addr,
			app_id = AppID.NETWORK,
			content_type = ContentType.L3KEYEX,
			raw_data = pickle.dumps({self.dev_addr: self._keys.public_key_tr}),
			direction = NetPacketDirection.OUT
		))
	"""
	Думаю, что каждое устройство должно совершить Н циклов отправки своего публичного ключа с периодичностью М.
	Устройства принимают его, записывают себе в случае необходимости и отправляют дальше
	
	Если предположить, что некое устройство А не знает ключа устройства Б, то оно даёт запрос,
	отправляя широковещательный пакет L3KEYRQ с devAddr пользователя. Предположим, никому этот ID неизвестен и 
	в какой-то момент запрос до него доходит. Нужный devAddr также отвечает широковещательным пакетом L3KEYEX со своим 
	публичным ключом. Путём ретрансляций нужный устройству А публичный ключ устройства Б доходит до А и в качестве 
	приятного бонуса бОльшая часть сети тоже знает этот публичный ключ.
	"""

	################################### TRANSACTIONS
	def new_transaction_event(self, packet: NetPacket, custom_ttl = None):
		try:
			Transaction(transaction_dict = self._last_transactions,
						packet = packet,
						queue = self._packets_queue,
						ttl = custom_ttl or self.ttl_transactions * 3).start()
		except Exception:
			logger.error(traceback.format_exc())

	def is_recent(self, packet: NetPacket) -> bool:
		return packet.hashsum in self._last_transactions


class UsbConnection:
	def __init__(self, vid=settings.VID, pid=settings.PID):
		self._vid = vid
		self._pid = pid
		self._buffer = bytearray(b'\0'*2048)
		self._usb = None
		self.open_device()

	def open_device(self) -> bool:
		if platform == "android":
			if candidates:= [device for device in usb4a.usb.get_usb_device_list() if
							 device.getVendorId() == self._vid and device.getProductId() == self._pid]:
				device = usb4a.usb.get_usb_device(candidates[0].getDeviceName())
				if not usb4a.usb.has_usb_permission(device):
					usb4a.usb.request_usb_permission(device)
					self.open_device()
				self._usb = usb4a.usb.get_usb_manager().openDevice(device)
		else:
			self._usb = usb.core.find(idVendor=self._vid, idProduct=self._pid)
		return self._usb != None

	# u.ENDPOINT_IN      device to host requests: Mega       -> PC   (e.g. retrieve message from buffer)
	# u.ENDPOINT_OUT     host to device requests: PC Payload -> Mega (e.g. module command + args)

	def send_to_device(self, command, endp=u.ENDPOINT_IN, wValue=0, wIndex=0, data = None):
		retry = 0
		while retry < 10:
			try:
				if self._usb and lock.acquire(True):
					if platform == "android":
						res = self._usb.controlTransfer(u.CTRL_TYPE_VENDOR | u.CTRL_RECIPIENT_DEVICE | endp,
														command, wValue, wIndex, data or self._buffer,
														(data and len(data)) or len(self._buffer), 5000)
						if endp == u.ENDPOINT_IN:
							return self._buffer[:res]
						return res
					else:
						return self._usb.ctrl_transfer(
							u.CTRL_TYPE_VENDOR | u.CTRL_RECIPIENT_DEVICE | endp,
										command, wValue, wIndex, data or 2048, 5000)
				else:
					raise usb.core.USBError
			except usb.core.USBError:
				sleep(1)
				self.open_device()
			except:
				logger.error(traceback.format_exc())
				return None
			finally:
				if lock.locked():
					lock.release()
				retry += 1


	def close_device(self):
		if self._usb:
			if platform == "android":
				self._usb.close()
			else:
				u.dispose_resources(self._usb)

	def __str__(self):
		if self._usb:
			if platform == "android":
				pass
			else:
				return f"{self._usb.manufacturer} {self._usb.product} on {self._usb.bus}.{self._usb.address}"
		return "Device not initialized or not found!"

	def __bool__(self):
		return self._usb != None


class UsbPacket:  # тут будет формирование и хранение сообщений для/с устройства по формату
	def __init__(self, source_packet=None, **kwargs):
		self._packet = bytearray()
		self.align = kwargs.get('align', False)
		# формируем новый по пришедшим параметрам или просто пакет по умолчанию.
		self.opcode = kwargs.get('opcode', s.USB_VOID)
		self.argc = kwargs.get('argc', 0)
		self.pydst = kwargs.get('pydst', 0)
		# а нужен ли он? сами посчитаем?
		self.pydc = kwargs.get('pydc', 0)
		self.args = kwargs.get('args', [])
		self.payload = kwargs.get('payload', [])

		# конвертация из готового пакета в объект класса возможна пока лишь для принимаемого пакета
		# в случае с отправляемым надо знать размеры аргументов, а это пока не сделано.
		# возможно, надо через match-case детальнее разобраться с типом source_packet

		# если это уже готовый пакет и его можно распарсить
		if source_packet and isinstance(source_packet, Iterable): #(isinstance(source_packet, list) or isinstance(source_packet, u.array.array)):
			self.opcode = source_packet[s.OPCI]
			if self.opcode >= 200:  # если это опкод пакета на приём (т.е. без арг)
				self.pydc = unpack("<H", bytes(source_packet[s.RET_PYDC:s.RET_PYDC + 2]))[0]
				self.payload = source_packet[s.RET_PYD:s.RET_PYD + self.pydc]
				if len(self.payload) == 1:
					self.payload = self.payload[0]
		# else: опускаем случай отправляемого пакета
		# при передаче Payload в потоке (без сохранения в буфер МК) обязательно нужно выравнивание 8 байт

	@property
	def args_size(self):
		return sum([p[1] for p in self.args])

	@property
	def packet(self):
		self.update()
		return self._packet

	@property
	def is_default(self) -> bool:
		return not (set(self.packet) == {s.USB_VOID, 0})
	# если это пакет, созданный с параметрами по умолчанию, то False, иначе - True

	def __str__(self) -> str:
		return ".".join([str(el) for el in self.packet])

	def update(self):
		self.pydc = len(self.payload)
		if self.opcode >= 200:
			self._packet = bytearray(pack("<BH", self.opcode, self.pydc))
		else:
			if self.payload:
				self.pydst = 2**ceil(log2(s.ASI + self.args_size)) if self.align else s.ASI + self.args_size
			self._packet = bytearray(pack("<3BH", self.opcode, self.argc, self.pydst, self.pydc))
			for arg, size in self.args:
				self._packet.extend(pack("<" + TypeSizes(size).name, arg))
			self._packet.extend([0] * (self.pydst - len(self._packet)))
		# если нет Payload и self.pydst = 0, то ничего не добавится к пакету
		self._packet.extend(list(self.payload))


class Keys:
	def __init__(self, private_key, packets_queue: queue.Queue):
		self.curve = reg.get_curve(settings.CURVE)
		self._keys = dict(pubkeys.items())
		self._private_key = int.from_bytes(private_key, byteorder='big')
		self._public_key = self.curve.g * self._private_key
		self._packets_queue = packets_queue
		self.last_renewed = None
		self.renew_session_keys()
		a = datetime.utcnow()
		b = a.replace(day = a.day+1, hour=0, minute=0, second=0, microsecond=0)
		self.rsk = RepeatTimer((b-a).total_seconds(), self.renew_session_keys)
		self.rsk.start()

	@property
	def private_key(self):
		return self._private_key

	@property
	def public_key(self):
		return self._public_key

	@property
	def public_key_tr(self):
		return [self._public_key.x, self.public_key.y]

	def __getitem__(self, target_addr):
		if res := self._keys.get(target_addr, None):
			return res['session_key']
		else:
			self._packets_queue.put(NetPacket(
											app_id = AppID.NETWORK,
											content_type = ContentType.L3KEYRQ,
											raw_data = target_addr.to_bytes(4, byteorder='little')
								))
			return None

	def add_key(self, dev_addr, public_key):
		if not isinstance(public_key, ec.Point) and isinstance(public_key, list):
			public_key = ec.Point(self.curve, *public_key)
		self._keys[dev_addr] = { 'public_key': public_key,
			  					 'session_key': self.generate_session_key(public_key) }

	def get_pk(self, dev_addr):
		if dev_addr in self._keys.keys():
			return self._keys[dev_addr]['public_key']
		return None

	def encrypt(self, recipient, data):
		if isinstance(data, str) and (session_key := self[recipient]):
			nonce = urandom(8)
			return nonce + salsa20_xor(key = session_key, nonce = nonce, message = data.encode())
		return None

	def decrypt(self, sender, data):
		if isinstance(data, bytes) and (session_key := self[sender]):
			return salsa20_xor(key = session_key, nonce = data[:8], message = data[8:])
		return None

	def generate_session_key(self, public_key: ec.Point):
		date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y%m%d")
		return sha256(compress_point(self._private_key * public_key).encode() + date.encode()).digest()

	def renew_session_keys(self):
		if not self.last_renewed or datetime.now().day - self.last_renewed.day >= 1:
			for dev_addr in self._keys.keys():
				self._keys[dev_addr].update({'session_key': self.generate_session_key(self._keys[dev_addr]['public_key'])})
			else:
				self.last_renewed = datetime.now()
				return True
		return False

	def stop(self):
		self.rsk.cancel()
		# if "keys" not in self._keys:
		# 	pubkeys['keys'] = {}
		# print("keys: ", self._keys.items())
		for dev_addr, data in self._keys.items():
			pubkeys[dev_addr] = data
		else:
			pubkeys.commit()
			#TODO


class Device:
	def __init__(self, messenger_queue: queue.Queue,  vid=settings.VID, pid=settings.PID,
				 process_interval=settings.PROCESS_INTERVAL, check_interval=settings.CHECK_INTERVAL,
				 api_poll_interval = settings.API_POLL_INTERVAL, force_radio = True):
		self._device = UsbConnection(vid, pid)
		self._dev_info, self._dev_addr, _ = self.retrieve_info()
		self.force_radio = bool(force_radio)
		self._inet = InternetConnection(username = self._dev_addr, password = _.hex())
		self._messenger_queue = messenger_queue
		self._process_interval = process_interval
		self._check_interval = check_interval
		self._api_poll_interval = api_poll_interval
		self._check_msg_thread = RepeatTimer(self._check_interval, self._check_incoming_msg)
		self._check_msg_thread_inet = RepeatTimer(self._api_poll_interval, self._check_incoming_msg_inet)
		self._route_thread = RepeatTimer(self._process_interval, self._route_net_packets)
		self._packets_queue = queue.Queue()
		self._keys = Keys(private_key=_, packets_queue = self._packets_queue)
		self._net = Network(packets_queue = self._packets_queue, keys = self._keys)
		self._partial_packets = {}
		self._initialize()

	@property
	def dev_info(self):
		return self._dev_info

	@property
	def dev_addr(self):
		return self._dev_addr

	@property
	def neighbors(self):
		return self._net.neighbors()

	@property
	def queue_size(self):
		return self._packets_queue.qsize()

	@property
	def device_available(self):
		return bool(self._device)

	def reopen_device(self):
		self._device.open_device()

	def stop(self):
		# TODO сохранить содержимое очередей. подумать о порядке
		self._net.stop()
		self._check_msg_thread.cancel()
		self._check_msg_thread_inet.cancel()
		self._route_thread.cancel()
		self._inet.stop()
		self._keys.stop()
		self._device.close_device()

	def get_key(self, key):
		return self._keys[key]

	def encrypt(self, dst_addr, raw_data):
		return self._keys.decrypt(dst_addr, raw_data)

	def decrypt(self, src_addr, raw_data):
		return self._keys.decrypt(src_addr, raw_data)


	def retrieve_info(self):
		self._device.open_device()
		dev_addr, lora_sync_word, country = 0x0, s.LORA_SYNC_WORD, 804
		private_key = random.randbytes(28)
		chip = Chip.SX126X
		try:
			dev_addr, lora_sync_word, country = unpack('<IHH', bytes(UsbPacket(source_packet =
																self.send_command(command=s.USB_GET_DEVINFO)).payload))
			private_key = bytes(UsbPacket(source_packet=self.send_command(command=s.USB_GET_PRIVATE_KEY)).payload)
			chip = Chip(UsbPacket(source_packet=self.send_command(command=s.USB_GET_MODULE)).payload)
		except Exception:
			logger.error(traceback.format_exc())
		finally:
			dev_info = \
				{
					'dev_addr': dev_addr,
					'lora_sync_word': lora_sync_word,
					'country': country,
					'chip': chip
				}
			NetPacket.dev_addr = dev_addr
			Network.dev_addr = dev_addr
			return dev_info, dev_addr, private_key

	# чтобы объект мог менять отправителя

	def _initialize(self):
		try:
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETFREQUENCY, argc = 1, args = [[s.LORA_FREQUENCY, 4]]))
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETLORAMODULATION, argc = 4, args = [[s.LORA_SPREADING_FACTOR, 1], [s.LORA_BANDWIDTH, 4], [s.LORA_CODERATE, 1], [False, 1]]))
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETLORAPACKET, argc = 5, args = [[s.SX126X_HEADER_EXPLICIT, 1], [s.LORA_PREAMBLE_LENGTH, 2], [s.LORA_PAYLOAD_LENGTH, 1], [s.LORA_CRC_ENABLE, 1], [0, 1]]))
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETSYNCWORD, argc = 1, args = [[s.LORA_SYNC_WORD, 2]]))
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETTXPOWER, argc = 2, args = [ [17, 1], [s.SX126X_TX_POWER_SX1262, 1]]))
			self.send_command(usb_packet = UsbPacket(opcode = s.M_SETRXGAIN, argc = 1, args = [[s.SX126X_RX_GAIN_BOOSTED, 1]]))
			# приём
			self.send_command(usb_packet = UsbPacket(opcode = s.M_REQUEST, argc = 2, args = [[s.SX126X_RX_CONTINUOUS, 4], [True, 1]]))
		except:
			logger.error(traceback.format_exc())
		else:
			if not self._route_thread.is_alive():
				self._route_thread.start()
			if not self._check_msg_thread.is_alive():
				self._check_msg_thread.start()
			if not self._check_msg_thread_inet.is_alive():
				self._check_msg_thread_inet.start()


	# u.ENDPOINT_IN      device to host | requests: Mega       -> PC   (e.g. retrieve message from buffer)
	# u.ENDPOINT_OUT     host to device | requests: PC Payload -> Mega (e.g. module command + args). UsbPacket = Payload!
	"""
	 Control requests may or may not have a data payload to write/read.
        In cases which it has, the direction bit of the bmRequestType
        field is used to infer the desired request direction. For
        host to device requests (OUT), data_or_wLength parameter is
        the data payload to send_to_device, and it must be a sequence type convertible
        to an array object. In this case, the return value is the number
        of bytes written in the data payload. For device to host requests
        (IN), data_or_wLength is either the wLength parameter of the control
        request specifying the number of bytes to read in data payload, and
        the return value is an array object with data read, or an array
        object which the data will be read to, and the return value is the
        number of bytes read.
    """
	def send_command(self, usb_packet: UsbPacket = None, command=s.MODULE_CTRL_MESSAGE):
		if self._device.open_device():
			# UsbPacket = Payload!
			return self._device.send_to_device(command=command,
											   endp=u.ENDPOINT_OUT if usb_packet else u.ENDPOINT_IN,
											   data=usb_packet and usb_packet.packet)
		return None

	def transmit_data(self, packet: NetPacket):
		#  write() method must be placed between beginPacket() and endPacket()
		#  в прошивке при вызове write() они автоматически вызываются
		bytes_sent = self.send_command(usb_packet = UsbPacket(
														opcode = s.M_WRITE,
														align = True, # !!!
														payload = packet.packet
													))
		# снова перевести в режим приёма
		self.send_command(usb_packet = UsbPacket(opcode = s.M_REQUEST, argc = 2, args = [[s.SX126X_RX_CONTINUOUS, 4], [True, 1]]))
		return bytes_sent

	def get_data(self):
		return self.send_command(command = s.USB_RADIO_RETRIEVE_MESSAGE)

	def add_packet(self, packet: NetPacket):
		if isinstance(packet, NetPacket):
			self._packets_queue.put(packet)

	def _check_incoming_msg_inet(self):
		try:
			if answer:= self._inet.request(settings.PACKET_ENDPOINT):
				for net_packet_ip in answer['packets']:
					if (packet:= NetPacket(source_packet = bytes.fromhex(net_packet_ip['packet']))).is_valid:
						self._packets_queue.put(packet)
		except:
			logger.error(traceback.format_exc())

	# при отправке заносить хэш сумму пакета в self._last_transactions и новый ttl
	# также можно при поступлении уже отправленного пакета отклонять его. но тогда вероятно нужен timestamp
	def _check_incoming_msg(self):
		try:
			if packet := self.get_data():
				if NetPacket(source_packet = packet).is_valid: # если мой формат
					self._packets_queue.put(NetPacket(source_packet = packet))
				else:       							   # если это LoRa
					self._packets_queue.put(NetPacket(
						src_addr = self._dev_addr,
						app_id = AppID.LORA,
						content_type = ContentType.LORA,
						raw_data = packet
					))
				# Если спарсили и не валид, то это - Лора, помещаем её опять в Нетпакет,
				# но уже в качестве полезной нагрузки
				logger.debug(f"New packet from device: {packet}")
		except Exception:
			logger.error(traceback.format_exc())

	def _route_net_packets(self):  # возможно переделать в повторяемый поток через Х время
		try:
			while not self._packets_queue.empty(): # and self.device_available:
				packet: NetPacket = self._packets_queue.get() # если это не отправленный нами вернувшийся пакет
				logger.info(f"New packet")
				if not self._net.is_recent(packet):
					# запомнили на время, что мы что-то приняли или отправили
					self._net.new_transaction_event(packet)
					# не совсем корректно делать это ДО, а не ПОСЛЕ, но пакет меняется дальше и меняется его хэш
					if packet.direction == NetPacketDirection.IN: # если это принятый пакет
						match packet.app_id:
							case AppID.NETWORK: # события сети
								self._net.process_network_event(packet)
							case AppID.MESSENGER: # события мессенджера
								# или всё равно отправляем в месседж_квек, а там уже мессенджер будет периодически
								# ходить по нерасшифрованным сообщениям и давать запросы на ключ
								if packet.is_fragmented:
									logger.debug(f"Messenger fragmented packet: {packet.packet.hex()}")
									if packet.raw_data[:16].hex() not in self._partial_packets.keys():
										self._partial_packets[packet.raw_data[:16].hex()] = [0] * packet.fragm_c
									self._partial_packets[packet.raw_data[:16].hex()][packet.fragment] = packet.raw_data[16:]
									if all(self._partial_packets[packet.raw_data[:16].hex()]):
										full = packet.duplicate()
										full.raw_data = b''.join(self._partial_packets[packet.raw_data[:16].hex()])
										self._messenger_queue.put(full)
										del self._partial_packets[packet.raw_data[:16].hex()]
										logger.debug(f"All fragments of fragmented packet are collected. Packet: {full.packet.hex()}")
								else:
									self._messenger_queue.put(packet)
								if (packet.dst_addr == settings.BROADCAST):
									copy = packet.duplicate()
									copy.swap_direction()
									self._packets_queue.put(copy)
									# приём файлов по фрагментам, их сборка в кучу, пересылка
							case AppID.LORA: # события ЛоРа
								pass
								# переслать сообщение от ЛоРа девайсов в сеть, если она доступна
					else: # если это пакет на отправку
					# здесь как-то надо сделать развилку, что, мол, если есть сеть, то через неё слать, а иначе - в эфир
						if not self._inet.available or self.force_radio or packet.try_radio:
							logger.debug(f"About to transmit {packet.packet.hex()}")
							if not self.transmit_data(packet):
								self._packets_queue.put(packet)
							sleep(.2)
						else:
							if not self._inet.request(settings.PACKET_ENDPOINT, packet):
								self._packets_queue.put(packet)
							logger.debug(f"Internet transmit of {packet.packet.hex()}")

				logger.debug(("-->" if packet.direction == NetPacketDirection.IN else "<--") + " process: " + packet.packet.hex())

		except Exception:
			logger.error(traceback.format_exc())

"""

	Message:
		*id (src_addr + target_addr + date.unix)
		*chat (src_addr + target_addr)
		sender (src_addr)
		recipient (target_addr)
		my_timestamp_sent
		*date_sent
		*date_received
		*status (on_change -> generate MESSAGE_READ event)
		forwarded_from (src_addr)
		*content_id
		
	identification -> forwarded_from, reply_to, msg_hash of previous fragment

	| my_timestamp_sent |  flags   |   identification   | content |
	|      3 bytes      |  1 byte  |     4/16 bytes     |         |
	

	flags:
			bit #     7 6 5    4     3     2     1    0
			value      		  2**4        2**2      
			meaning	  x x x reply_to x forwarded x    x
		
	Content:
		*id
		*ready (фрагментация)
		content_type
		content (blob)
	
	
	*- это то, что создаётся программно
		
	Как передать длинное сообщение?
	Сначала фрагментируем текст по Х байт, формируем Н сетевых пакетов с соотв. fragm и fragmC.
	В обработчике если видим фрагментацию, то сразу делаем ready = False.
	Когда приняли один из таких фрагментов, то смотрим на его поле identification - в данном случае там будет содержаться
	хэш предыдущего фрагмента. Признаком того, что это фрагменты одного и того же сообщения будет один и тот же timestamp.
	
	
"""
