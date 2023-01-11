from enum import Enum
import threading
from time import sleep
import usb.util as u
#####
from parse_settings import SettingsParser
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

from datetime import datetime
###
import tinyec.ec as ec
import tinyec.registry as reg
from pure_salsa20 import salsa20_xor, xsalsa20_xor
from os import urandom
#####
import settings as settings
import http.client as http_client
from classes import NetPacketDirection, AppID, Chip, TypeSizes, ContentType
from models import Message, Content
from hashlib import sha256

from kivy.utils import platform

if platform == "android":
	from android.permissions import request_permissions, Permission
	request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
						 Permission.READ_EXTERNAL_STORAGE,
						 Permission.RECORD_AUDIO,
						 Permission.INTERNET])
	import usb4a.usb
else:
	import usb.core



def print_with_date(string):
	print(datetime.now(), string)

def try_pickle(value):
	try:
		return pickle.loads(value)
	except:
		return None

def compress_point(point: ec.Point):
	return str(point.x + point.y % 2 + 461)


s = SettingsParser(filepaths=['./settings.h',
							  '../LoRaRF-Arduino-2.1.1/src/SX126x.h',
							  '../LoRaRF-Arduino-2.1.1/src/SX126x_API.h',
							  '../LoRaRF-Arduino-2.1.1/src/SX127x.h',
							  '../LoRaRF-Arduino-2.1.1/src/BaseLoRa.h',
							  '../LoRaRF-Arduino-2.1.1/src/SX126x_driver.h'])


lock = threading.Lock()



class InternetConnection:
	def __init__(self):
		self._avail = False
		self._check_inet_thread = RepeatTimer(settings.PING_PERIOD, self._check_inet)
		self._check_inet_thread.start()

	@property
	def available(self):
		return self._avail

	def _check_inet(self):
		conn = http_client.HTTPSConnection("8.8.8.8", timeout=5)
		try:
			conn.request("HEAD", "/")
			self._avail = True
		except Exception:
			self._avail = False
		finally:
			conn.close()

	def send(self):
		pass

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


class Transaction(threading.Thread):
	def __init__(self, *args, transaction_list: set, transaction, ttl, **kwargs: dict):
		self.ttl = ttl
		self.transaction_list = transaction_list
		self.transaction = transaction
		super(Transaction, self).__init__(*args, **kwargs)

	def run(self):
		self.transaction_list.update([self.transaction])
		sleep(self.ttl)
		if self.transaction in self.transaction_list:
			self.transaction_list.remove(self.transaction)


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
		self.dst_addr = kwargs.get('target_addr', settings.BROADCAST) # broadcast
		self.fragm_c = kwargs.get('fragm_c', 0)
		self.fragment = kwargs.get('fragment', 0)
		self.app_id = kwargs.get('app_id', AppID.UNKNOWN)
		self.content_type = kwargs.get('content_type', ContentType.UNKNOWN)
		self.raw_data = kwargs.get('raw_data', bytes())
		self.pydc = kwargs.get('pydc', len(self.raw_data) + 1)
		self.direction = kwargs.get('direction', NetPacketDirection.IN)

		if source_packet and isinstance(source_packet, Iterable):
			self.src_addr, self.dst_addr, _, self.app_id, self.pydc, self.content_type = \
				unpack("<2I4B", bytes(source_packet[:12]))
			self.fragm_c, self.fragment, self.app_id = _ >> 4, _ & 0xf, AppID(self.app_id)
			self.raw_data = bytes(source_packet[12:12 + self.pydc])
			self.update()

	def __str__(self) -> str:
		return ".".join([str(el) for el in self.packet])

	def __eq__(self, other) -> bool:
		if isinstance(other, NetPacket):
			return self.packet == other.packet
		return False

	def __hash__(self) -> int:
		return hash(str(self.packet)) #hash(frozenset(self.packet))

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
	def packet(self) -> list:
		if self.is_valid:
			# если мы успешно спарсили пакет и это пакет нашего формата
			self.update()
			return list(self._packet)
		elif self.source_packet:
			# иначе отдаём то, что пришло изначально пришло на вход
			return list(self.source_packet)
		else:
			return []


	@property
	def dict(self) -> dict:
		return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


	def update(self):
		self._packet = bytearray(pack(f"<2I4B", self.src_addr, self.dst_addr, (self.fragm_c << 4) + self.fragment,
									  self.app_id.value, self.pydc, self.content_type.value))
		self._packet.extend(self.raw_data) # encrypted_data

	def swap_addr(self, from_me = False):
		# меняем местами адреса источника и назначения.
		# если задан адрес этого устройства, то подставляем его в источник
		self.src_addr, self.dst_addr = self.dev_addr if from_me else self.dst_addr, self.src_addr

	def swap_direction(self):
		self.direction = NetPacketDirection(not self.direction.value)

	def duplicate(self):
		return NetPacket(source_packet = self.packet)


class Routing:
	dev_addr = 0
	def __init__(self, packets_queue, keys, ttl_neighbor=30, ttl_transactions=36):
		self._keys: Keys = keys
		self._last_transactions = set()
		self._packets_queue: queue.Queue = packets_queue
		self.ttl_neighbor = ttl_neighbor
		self.ttl_transactions = ttl_transactions
		self._share_neighbors_thread = RepeatTimer(self.ttl_neighbor, self._share_neighbors)
		self._share_pubkey_thread = RepeatTimer(self.ttl_neighbor * 2, self._share_my_pubkey)
		self._root_node = NodeExtended(name = self.dev_addr)
		self._share_neighbors_thread.start()
		self._share_pubkey_thread.start()


	################################### NEIGHBORS
	def neighbors(self, maxlevel: Union[int, None] = 5, include_root = False) -> list:
		return [ node.name for node in LevelOrderIter(self._root_node, maxlevel = maxlevel) ][int(not include_root):]

	def add_neighbor(self, source, new_neighbor):
		# если такого соседа нет
		if not anytree.cachedsearch.find(self._root_node, lambda node: node.name == new_neighbor):
			# есть предок нового соседа есть в дереве
			if source_node := anytree.cachedsearch.find(self._root_node, lambda node: node.name == source):
				NodeExtended(name = new_neighbor,
							 parent = source_node,
							 ttl =self.ttl_neighbor * 3)

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
		if packet.is_valid and packet.app_id == AppID.NETWORK and packet.direction == NetPacketDirection.IN:
			#match packet.content_type:
			if packet.content_type == ContentType.L3NEIGHBORINFO:
				#case ContentType.L3NEIGHBORINFO:
					# сначала обработать (обновить своё дерево),
					# а потом уже слать своё!
					# ни в коем случае не пересылать этот пакет.
				for record in (try_pickle(packet.raw_data) or []):
					self.add_neighbor(packet.src_addr, record)
				return # выходим, чтобы не пересылать дальше
					# информация о соседях, пускай 10 записей таблицы
			elif packet.content_type == ContentType.L3KEYEX:
				#case ContentType.L3KEYEX:
					# опасно. обновляем хранилище ключей на пришедший распарсеный словарь
				if data:= try_pickle(packet.raw_data):
					for dev_addr, public_key in data.items():
								# пускай цикл, чем костыли, чтобы получить из словаря 2 аргумента
								# ну и на будущее задел, вдруг решу по несколько слать.
						self._keys.add_key(dev_addr = dev_addr, public_key = public_key)
					# обработка периодической рассылки ключей/ретрансляция ответов на запросы
			elif packet.content_type == ContentType.L3KEYRQ:
				#case ContentType.L3KEYRQ:
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
	def new_transaction_event(self, packet: Union[NetPacket, int], custom_ttl = None):
		try:
			Transaction(transaction_list = self._last_transactions,
						transaction = hash(packet) if isinstance(packet, NetPacket) else packet,
						ttl =custom_ttl or self.ttl_transactions * 3).start()
		except Exception:
			print(traceback.format_exc())

	def is_recent(self, packet: NetPacket) -> bool:
		return hash(packet) in self._last_transactions


class UsbConnection:
	def __init__(self, vid=0x16c0, pid=0x5dc):
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

	def send_to_device(self, command, endp=u.ENDPOINT_IN, wValue=0, wIndex=0, data = None): #wLengthOrData: Union[int, Iterable] = 2048):
		if self._usb:
			if platform == "android":
				res = self._usb.controlTransfer(u.CTRL_TYPE_VENDOR | u.CTRL_RECIPIENT_DEVICE | endp,
												command, wValue, wIndex, data or self._buffer, (data and len(data)) or len(self._buffer), 5000)
				if endp == u.ENDPOINT_IN:
					return self._buffer[:res]
				return res
			else:
				return self._usb.ctrl_transfer(
					u.CTRL_TYPE_VENDOR | u.CTRL_RECIPIENT_DEVICE | endp,
								command, wValue, wIndex, data or 2048, 5000)
		return -1

		# retry = 0
		# while retry < 10:
		# 	try:
		# 		if self._usb and lock.acquire(True):
		# 			return self._usb.ctrl_transfer(
		# 				u.CTRL_TYPE_VENDOR | u.CTRL_RECIPIENT_DEVICE | endp,
		# 				command, wValue, wIndex, wLengthOrData or 2048, 5000)
		# 		else:
		# 			raise usb.core.USBError
		# 	except usb.core.USBError:
		# 		sleep(5)
		# 		self.open_device()
		# 	except Exception:
		# 		print(traceback.format_exc())
		# 		return None
		# 	# TODO log!
		# 	finally:
		# 		lock.release()
		# 		retry +=1
		#TODO Всё это выглядит по-ебанутому, подумать, как это можно нормально сделать
	# если передача, то возвращается кол-во записанных байт, если приём - буфер с прочитанными данными

	def __str__(self):
		if self._usb:
			if platform == "android":
				pass
			else:
				return f"{self._usb.manufacturer} {self._usb.product} on {self._usb.bus}.{self._usb.address}"
		# ещё бы больше технических хар-к, а-ля шины
		return "Device not initialized or not found!"


# TODO Обязательно в случае командных пакетов с Payload нужно чтобы pydst был кратен 8!
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
		if source_packet and (isinstance(source_packet, list) or isinstance(source_packet, u.array.array)):
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
	def packet(self) -> list:
		self.update()
		return list(self._packet)

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
		self._keys = {}
		self._private_key = int.from_bytes(private_key, byteorder='big')
		self._public_key = self.curve.g * self._private_key
		self._packets_queue = packets_queue
		#self._update_thread
		self.last_renewed = None
		self.renew_session_keys()

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
		# TODO заставить работать генерацию ключа сессии и создание ключа сессии

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

	#TODO поток, срабатывающий раз в сутки, либо в 00:00, либо в первый заход за день, обновляющий сессионные ключи


class Device:
	def __init__(self, messenger_queue: queue.Queue, inet: InternetConnection,
				 vid=0x16c0, pid=0x5dc, process_delay=10, check_delay=0.8):
		self._device = UsbConnection(vid, pid)
		self._dev_info, self._dev_addr, _ = self.retrieve_info()
		#
		self.force_radio = True
		self._inet = inet
		#
		self._messenger_queue = messenger_queue
		self._process_delay = process_delay
		self._check_delay = check_delay
		self._check_msg_thread = RepeatTimer(self._check_delay, self._check_incoming_msg)
		self._route_thread = RepeatTimer(self._process_delay, self._route_net_packets)
		self._packets_queue = queue.Queue()
		self._keys = Keys(private_key=_, packets_queue = self._packets_queue)
		self._routing = Routing(packets_queue = self._packets_queue, keys = self._keys)
		self._initialize()

	@property
	def dev_info(self):
		return self._dev_info

	@property
	def dev_addr(self):
		return self._dev_addr

	@property
	def neighbors(self):
		return self._routing.neighbors()
		# TODO. Сделать параметр jsonify для того, чтобы отдавать инфу на сервер

	@property
	def queue_size(self):
		return self._packets_queue.qsize()

	def __str__(self):
		return ""

	def retrieve_info(self):
		self._device.open_device()
		dev_addr, lora_sync_word, country = random.getrandbits(32), s.LORA_SYNC_WORD, 804
		private_key = random.randbytes(28) #, random.randbytes(32)
		chip = Chip.SX126X
		try:
			dev_addr, lora_sync_word, country = unpack('<IHH', bytes(UsbPacket(source_packet =
																self.send_command(command=s.USB_GET_DEVINFO)).payload))
			private_key = bytes(UsbPacket(source_packet=self.send_command(command=s.USB_GET_PRIVATE_KEY)).payload)
			chip = Chip(UsbPacket(source_packet=self.send_command(command=s.USB_GET_MODULE)).payload)
		except Exception:
			print(traceback.format_exc())
		finally:
			dev_info = \
				{
					'dev_addr': dev_addr,
					'lora_sync_word': lora_sync_word,
					'country': country,
					'chip': chip
				}
			NetPacket.dev_addr = dev_addr
			Routing.dev_addr = dev_addr
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
			print_with_date(traceback.format_exc())
		else:
			if not self._route_thread.is_alive():
				self._route_thread.start()
			if not self._check_msg_thread.is_alive():
				self._check_msg_thread.start()


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
	def send_command(self, usb_packet: UsbPacket = None, command=s.MODULE_CTRL_MESSAGE): # , endp=u.ENDPOINT_OUT
		if self._device.open_device():
			# UsbPacket = Payload!
			return self._device.send_to_device(command=command,
											   endp=u.ENDPOINT_OUT if usb_packet else u.ENDPOINT_IN,
											   data=usb_packet and usb_packet.packet) # usb_packet.packet if usb_packet else None
		return None

	def transmit(self, packet: NetPacket):
		#  write() method must be placed between beginPacket() and endPacket()
		#  в прошивке при вызове write() они автоматически вызываются
		bytes_sent = self.send_command(usb_packet = UsbPacket(
														opcode = s.M_WRITE,
														align = True, # !!!
				 										#pydc = len(packet.packet),
														payload = packet.packet
													))
		# снова перевести в режим приёма
		self.send_command(usb_packet = UsbPacket(opcode = s.M_REQUEST, argc = 2, args = [[s.SX126X_RX_CONTINUOUS, 4], [True, 1]]))
		return bytes_sent

	def get_message(self):
		return self.send_command(command = s.USB_RADIO_RETRIEVE_MESSAGE) #, endp = u.ENDPOINT_IN)

	# при отправке заносить хэш сумму пакета в self._last_transactions и новый ttl
	# также можно при поступлении уже отправленного пакета отклонять его. но тогда вероятно нужен timestamp
	def _check_incoming_msg(self):
		try:
			if msg := self.get_message():
				if NetPacket(source_packet = msg).is_valid: # если мой формат
					self._packets_queue.put(NetPacket(source_packet = msg))
				else:       							   # если это LoRa
					self._packets_queue.put(NetPacket(
						src_addr = self._dev_addr,
						app_id = AppID.LORA,
						content_type = ContentType.LORA,
						raw_data = msg
					))
				# TODO подумать, как правильно обработать ЛОРУ и обычный пакет по формату
				# Придумал.
				# Если спарсили и не валид, то это - Лора, помещаем её опять в Нетпакет,
				# но уже в качестве полезной нагрузки
				print_with_date("check: " + str(msg))
		except Exception:
			print(traceback.format_exc())

	def _route_net_packets(self):  # возможно переделать в повторяемый поток через Х время
		try:
			while not self._packets_queue.empty():
				packet: NetPacket = self._packets_queue.get() # если это не отправленный нами вернувшийся пакет
				if not self._routing.is_recent(packet):
					# запомнили на время, что мы что-то приняли или отправили
					self._routing.new_transaction_event(packet)
					# не совсем корректно делать это ДО, а не ПОСЛЕ, но пакет меняется дальше и меняется его хэш
					if packet.direction == NetPacketDirection.IN: # если это принятый пакет
						if packet.app_id == AppID.NETWORK:
						#match packet.app_id:
							#case AppID.NETWORK: # события сети
							self._routing.process_network_event(packet)
								# TODO отправить этот пакет дальше и не забыть занести в транзакции
						elif packet.app_id == AppID.MESSENGER:
							#case AppID.MESSENGER: # события мессенджера
								# или всё равно отправляем в месседж_квек, а там уже мессенджер будет периодически
								# ходить по нерасшифрованным сообщениям и давать запросы на ключ
							self._messenger_queue.put(packet)
							if (packet.dst_addr == settings.BROADCAST):
								copy = packet.duplicate()
								copy.swap_direction()
								self._packets_queue.put(copy)
								# приём файлов по фрагментам, их сборка в кучу, пересылка
						elif packet.app_id == AppID.LORA:
							#case AppID.LORA: # события ЛоРа
							pass
								# переслать сообщение от ЛоРа девайсов в сеть, если она доступна
					else: # если это пакет на отправку
					# здесь как-то надо сделать развилку, что, мол, если есть сеть, то через неё слать, а иначе - в эфир
						if self.force_radio or not self._inet.available:
							self.transmit(packet)
						else:
							pass
					# # запомнили на время, что мы что-то приняли или отправили
					# self._routing.new_transaction_event(packet_hash)
					# TODO! Выяснить, не повлияет ли изменение параметров пакета в case'ах (передача по ссылке?)
					#  на правильный хэш тут

					# ВЛИЯЕТ!


				print_with_date(("-->" if packet.direction == NetPacketDirection.IN else "<--") + " process: " + str(packet))

		except Exception:
			print(traceback.format_exc())


class Messenger:
	def __init__(self, process_delay=5):
		self._messenger_queue = queue.Queue()
		self._process_delay = process_delay
		self._inet = InternetConnection()
		self._device = Device(messenger_queue = self._messenger_queue, inet = self._inet)
		self._check_msg_thread = RepeatTimer(self._process_delay, self._process_messages)
		self._check_msg_thread.start()

	def _process_messages(self):
		try:
			while not self._messenger_queue.empty():
				packet: NetPacket = self._messenger_queue.get()
				#if packet.dst_addr == settings.BROADCAST:
				#	pass
				# TODO А что если сделать два подтипа пакета сообщения: который получен из Лоры и который получен из сети
				# Тогда в последнем случае можно было бы добавить дополнительную информацию (время отправки или "ответ_на")
				# Хотя это усложняет пакет, причём очень сильно
				if session_key := self._device._keys[packet.src_addr]:
					decrypted = self._device._keys.decrypt(packet.src_addr, packet.raw_data)
					flags = decrypted[3]
					m = Message.create(sender = packet.src_addr,
								   	   recipient = packet.dst_addr,
									   timestamp_sent = int.from_bytes(decrypted[:3], byteorder='big'),
									   forwarded_from = decrypted[3:7] if flags & 4 else 0)
					c = Content.create(message = m,
									   content_type = packet.content_type,
									   content = decrypted[(3 + flags & 4):]) # TODO?
					m.save()
					c.save()
				else: # если мы отправителя/получателя не знаем, то выше отправлен сразу запрос ключа, а этот пакет складываем в конец
					self._messenger_queue.put(packet)

		except Exception:
			print(traceback.format_exc())

	def message_parse(self, packet: NetPacket):
		pass

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
		//reply_to (id)
		forwarded_from (src_addr)
		*content_id
		
	| my_timestamp_sent |  flags   | forwarded_from | content |
	|      3 bytes      |  1 byte  |    4 bytes     |         |

	flags: 
	internet x x x x forwarded x x
	 2 ** 7			   2 ** 2
		
	Content:
		*id
		*ready (фрагментация)
		content_type
		content (blob)
	
	
	*- это то, что создаётся программно
"""
