#!/usr/bin/env python3

import asyncio, discord
import Muck

class DiscordUser:
	def __getstate__(self):
		d = dict(self.__dict__)
		del d['user']
		return d

	def __setstate__(self, d):
		self.user = None
		self.__dict__.update(d)

	def __init__(self, user):
		self.user = user
		self.id = user.id
		self.name = user.display_name
		self.mention = user.mention

	def message(self, content, attachments=None):
		assert attachments is None

		if self.user is not None:
			asyncio.ensure_future(client.send_message(self.user, content))

client = discord.Client()
users = {}

async def initialize_users():
	for member in client.get_all_members():
		if member.bot:
			continue
		user = users[member.id] = DiscordUser(member)
		muck.on_join(user)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

	await initialize_users()

@client.event
async def on_message(message):
	if message.author.bot or not message.channel.is_private or message.author.id == client.user.id:
		return

	muck.on_message(users[message.author.id], message.content)

@client.event
async def on_member_join(member):
	if member.bot:
		return
	user = users[member.id] = DiscordUser(member)
	muck.on_join(user)

@client.event
async def on_member_remove(member):
	if member.bot:
		return
	muck.on_quit(users[member.id])
	del users[member.id]

@client.event
async def on_member_update(before, after):
	if before.bot:
		return
	users[before.id].name = after.display_name

def main():
	global muck
	muck = Muck.load()
	client.run(open('bot.token').read())

if __name__=='__main__':
	main()
