import json, os, pickle

class Player:
	def __init__(self, user):
		self.user = user
		self.mention = self.user.mention
		self.playing = False

		self.room = muck.rooms['Docking Bay 3A']

	@property
	def wizard(self):
		return self.user.id in muck.wizards

	@property
	def name(self):
		return self.user.name

	def message(self, message, attachments=None):
		if self.playing:
			self.user.message(message, attachments)

class Room:
	__props__ = ('name', 'description', 'short_description', 'muted')

	def __init__(self,
			name, # Internal name for the room
			description='You are in a room.', # Used when the player is in the room
			short_description='a room', # Used when the player is outside
			muted=False # Whether or not players can speak here
		):
		self.name = name
		self.description = description
		self.short_description = short_description
		self.muted = muted
		self.connections = {}
		self.objects = []

		muck.rooms[self.name] = self

	def connect(self, direction, room):
		if isinstance(room, str):
			room = muck.rooms[room]
		self.connections[direction] = room

	@property
	def players(self):
		for player in muck.players.values():
			if player.room is self:
				yield player

def command(*options, wizard=False, help=None):
	if help:
		helps.append((options, help, wizard))
	def sub(func):
		fargs = func.__code__.co_varnames[:func.__code__.co_argcount][2:]
		optional = len(func.__defaults__) if func.__defaults__ is not None else 0
		req = len(fargs) - optional
		wantsMessage = fargs == ('message', )
		def nsub(self, player, command, message):
			if wizard and not player.wizard:
				player.message('This command is beyond your power.')
				return
			args = message.split(' ')
			if len(args) == 1 and args[0] == '':
				args = []
			if wantsMessage:
				return func(self, player, message)
			elif req <= len(args) <= (req + optional):
				return func(self, player, *args)
			else:
				helpmsg = ''
				for options, help, _ in helps:
					if command in options:
						helpmsg = help
						break
				player.message('Wrong number of parameters to command. ' + helpmsg)

		for option in options:
			commands[option] = nsub
		return func
	return sub

def ifind(d, key, default=None):
	key = key.lower()
	for k, v in d.items():
		if k.lower() == key:
			return v
	return default

commands = {}
helps = []

def load():
	global muck
	try:
		with open('world.state', 'rb') as fp:
			muck = pickle.load(fp)
			return muck
	except IOError:
		print('Could not open world state. Baking a new one.')
		muck = Muck()
		Room(
			'Docking Bay 3A', 
			description='''You are in a docking bay on Freeside.''', 
			muted=True
		)
		muck.save()
		return muck

class Muck:
	def __init__(self):
		self.players = {}
		self.rooms = {}
		self.wizards = ['172586206788452353']

	def save(self):
		try:
			os.rename('world.state', 'backup.state')
		except FileNotFoundError:
			pass
		with open('world.state', 'wb') as fp:
			pickle.dump(self, fp)

	def __getitem__(self, user):
		if user.id not in self.players:
			self.players[user.id] = Player(user)
		self.players[user.id].user = user
		return self.players[user.id]

	def on_join(self, user):
		player = self[user]

	def on_message(self, user, message):
		player = self[user]
		print('%s: %s' % (player.name, message))
		room = player.room

		first = False
		if not player.playing:
			player.playing = True
			player.message('Welcome to Freeside.')
			self.look(player)
			first = True

		if ' ' in message:
			command, message = message.split(' ', 1)
		else:
			command = message
			message = ''
		command = command.lower()
		if command in commands:
			if first and command == 'look':
				return
			commands[command](self, player, command, message)
			self.save()
			return

		if first:
			player.message('For help, all you have to do is ask.')
		else:
			player.message('Unknown command.')

	@command('help')
	def help(self, player):
		helpmsg = ''
		for options, help, wizard in helps:
			if not wizard or player.wizard:
				helpmsg += '- %s: %s\n' % (', '.join('**%s**' % x for x in options), help)
		player.message(helpmsg)

	@command('look', 'where', help='*look* -- Look at the room you\'re in')
	def look(self, player):
		room = player.room
		player.message(room.description)
		adjoining = []
		for direction, other in room.connections.items():
			adjoining.append('To your %s is %s.' % (direction, other.short_description))
		if adjoining:
			player.message(' '.join(adjoining))
		others = ['**%s**' % other.name for other in room.players if other is not player and other.playing]
		if len(others) <= 2:
			others = ' and '.join(others)
		elif len(others) > 2:
			others[-1] = 'and ' + others[-1]
			others = ', '.join(others)
		if others:
			player.message('In here with you: %s\n' % others)

	@command('go', help='*go __direction__* -- Go to an adjacent room')
	def go(self, player, direction):
		nroom = ifind(player.room.connections, direction)
		if nroom is None:
			player.message('You can\'t go that way.')
		else:
			player.room = nroom
			self.look(player)

	@command('teleport', wizard=True, help='*teleport __room__* -- Teleport to a given room')
	def teleport(self, player, name):
		nroom = ifind(self.rooms, name)
		if nroom is None:
			player.message('Unknown room.  Known rooms: ' + ', '.join(room.keys()))
		else:
			player.room = nroom
			self.look(player)

	@command('say', '"', help='*say __message__* -- Say something in the room')
	def say(self, player, message):
		if player.room.muted:
			player.message('You cannot speak here.')
			return
		for other in player.room.players:
			if other is not player:
				other.message('%s said "%s".' % (player.name, message))
		player.message('You said "%s".' % message)

	@command('create-room', wizard=True, help='*create-room __name__* -- Create a new room')
	def createRoom(self, player, name):
		Room(name)
		player.message('Room created.')

	@command('delete-room', wizard=True, help='*delete-room __name__* -- Delete a room')
	def deleteRoom(self, player, name):
		room = ifind(self.rooms, name)
		if room is None:
			player.message('Unknown room.')
			return
		elif room is self.rooms['Docking Bay 3A']:
			player.message('Cannot delete default room.')
			return

		for other in self.rooms.values():
			todel = []
			for k, v in other.connections.items():
				if v is room:
					todel.append(k)
			for k in todel:
				del other.connections[k]
		for other in room.players:
			other.room = self.rooms['Docking Bay 3A']
			other.message('The room you were in has been deleted.  Moving you to the default room.')
			self.look(other)
		del self.rooms[room.name]
		player.message('Room deleted.')

	@command('connect-room', wizard=True, help='*connect-room __direction__ __name__* -- Connect this room to another')
	def connectRoom(self, player, direction, name):
		first = player.room
		second = ifind(self.rooms, name)
		if second is None:
			player.message('Unknown room.')
			return
		first.connections[direction.lower()] = second
		player.message('Connected.')

	@command('set-room', wizard=True, help='*set-room __property__ __value__* -- Set a property on the current room')
	def setRoom(self, player, message):
		if ' ' in message:
			property, value = message.split(' ', 1)
		else:
			property, value = message, ''

		room = player.room

		if not hasattr(room, property):
			player.message('Unknown property.')

		try:
			value = json.loads(value)
		except:
			import traceback
			player.message(traceback.format_exc())
			return

		setattr(room, property, value)

		player.message('Set property.')

	@command('get-room', wizard=True, help='*get-room [__property__]* -- Get one or all properties on the current room')
	def getRoom(self, player, property=None):
		room = player.room
		if property is None:
			for x in room.__props__:
				player.message('Room property `%s`: `%r`' % (x, getattr(room, x)))
		elif hasattr(room, property):
			player.message('Room property: `%r`' % (getattr(room, property), ))
		else:
			player.message('Unknown property.')

	@command('quit', help='*quit* -- Stop playing and receiving messages')
	def quit(self, player):
		player.message('Good bye for now.')
		player.playing = False

	def on_quit(self, user):
		if user.id in self.players:
			del self.players[user.id]
