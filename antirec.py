#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (c) 2010, Natenom / Natenom@googlemail.com
# Copyright (c) 2011, DunkleAura dunkleaura at gmail dot com
# Version: 0.0.3-da1
# 2010-09-07, 2011-06-17

# SETTINGS #

# Name of the groups that are allowed to give others permission to record :)
# This groups and its members must be defined in the root channel.
canallowrecording = ('admin', 'moderator')

# Port and secret
iceport = 6502
icesecret = "must be changed"

# Entries in the context menu:
msg_context_allow = "Aufnahmeerlaubnis erteilen"
msg_context_disallow = "Aufnahmeerlaubnis zurückziehen"

PUNISHMENT = "DEAF"       # Punishment for users that try to record :P" Can be "DEAF" or "KICK".
ADMINALLOWSELF = False    # Don't allow members of the group canallowrecording to permit themselfs to record.

JOININFO = False  # Shows a small piece of Information on Join
DEBUG = False  # More verbose output, True or False

################################################################################
# DO NOT CHANGE BELOW THIS LINE #
################################################################################
import Ice
#Ice.loadSlice("--all -I/usr/share/slice /usr/share/slice/Murmur.ice")
Ice.loadSlice('', ['-I' + Ice.getSliceDir(), "/usr/share/slice/Murmur.ice"])
import Murmur
import sys
import os
import logging
import signal

myname = os.path.basename(__file__)

FORMAT = "%(levelname)s:%(name)s - %(message)s"
if (DEBUG):
	logging.basicConfig(stream=sys.stdout, format=FORMAT, level=logging.DEBUG)
else:
	logging.basicConfig(stream=sys.stdout, format=FORMAT, level=logging.INFO)

AllowedToRec = {}               # Temporary list of users allowed to record.
canAllowRec = {}                # Temporary list of users which can permit to record
isRecording = {}                # Temporary list of users they are recording
pidfile = "/tmp/antirec.pid"    # a pidfile

class MetaCallbackI(Murmur.MetaCallback):
	logger = logging.getLogger('MetaCallback')
	def started(self, s, current=None):
		logger.debug("started")
		serverR=Murmur.ServerCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerCallbackI(server, current.adapter)))
		s.addCallback(serverR)

	def stopped(self, s, current=None):
		logger.debug("stopped")

class ServerCallbackI(Murmur.ServerCallback):
	def __init__(self, server, adapter):
	  self.server = server
	  self.contextR = Murmur.ServerContextCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerContextCallbackI(server)))

	def userStateChanged(self, p, current=None):
		"""Wer aufnimmt, wird stumm-taub gestellt."""
		global AllowedToRec, PUNISHMENT
		UserState = self.server.getState(p.session)

		logger = logging.getLogger('userStateChanged')
		logger.debug('userStateChanged')
		#Check if user is allowed to record.

		if (UserState.recording == True) and (UserState.deaf == False) and not (p.session in AllowedToRec): #and not (p.channel == AllowedToRec[p.session]):
			if (PUNISHMENT == "DEAF"):
				UserState.deaf = True
				self.server.setState(UserState)
				logger.info('User: %s was deafened, because: recording' % (UserState.name))
				msg="<font style='color:red;background:yellow;'>User \"%s\" has been deafened because he started recording.</font>" % (UserState.name)
				self.server.sendMessageChannel(UserState.channel, 0, msg)
			elif (PUNISHMENT == "KICK"):
				logger.info('User: %s was kicked, because: recording' % (UserState.name))
				self.server.kickUser(UserState.session, "Recording on this server is not allowed. Please respect privacy!")

			#Callback is not implemented... if a user switches a channel :(
			#if (p.channel == AllowedToRec[p.session]):
				#print "Erlaubnis gilt nur für KanalID %s, deshalb wurde sie entzogen" % AllowedToRec[p.session]
				##Deaf him and beat him...
		elif (UserState.recording == True) and (p.session in AllowedToRec):
				logger.info('User: %s is recording' % (UserState.name))
				isRecording[p.session] = p.name
		elif (UserState.recording == False) and (p.session in isRecording) and (p.session in AllowedToRec):
			logger.info('User: %s stopped recording' % (UserState.name))
			if (p.session in isRecording):
				del isRecording[p.session]

	def userConnected(self, p, current=None):
		logger = logging.getLogger('userConnected')
		global msg_context_allow, msg_context_disallow, canAllowRec, isRecording
		ACL = self.server.getACL(0) #Check if user is in group canallowrecording defined in the root channel.
		#ACL[0] = ACL
		#ACL[1] = Groups
		#ACL[2] = inherit
		for gruppe in ACL[1]:
			if (gruppe.name in canallowrecording):
				if (p.userid in gruppe.members):
					canAllowRec[p.session] = p.name
					self.server.addContextCallback(p.session, "recallow", msg_context_allow, self.contextR, Murmur.ContextUser)
					self.server.addContextCallback(p.session, "recdisallow", msg_context_disallow, self.contextR, Murmur.ContextUser)
					break
		if (p.session in canAllowRec):
			logger.debug('User: %s can permit to record in group: %s' % (p.name, gruppe.name))
		else:
			logger.debug('User: %s' % (p.name))
		# Informations on Connect
		if JOININFO:
			msg = '<ul>Folgende User können Dir die berechtigung zum Aufzeichnen erteilen:'
			for n in sorted(canAllowRec.itervalues()):
				msg += '<li>%s</li>' % n
			msg += '</ul>'
			if (len(isRecording) > 0):
				msg += '<p style="color:red;font-weight:bold;">Zur Zeit wird aufgezeichnet von: %s</p>' % (", ".join(sorted(isRecording.values())))
			self.server.sendMessage(p.session, msg)

	def userDisconnected(self, p, current=None):
		logger = logging.getLogger('userDisconnected')
		try:
			out = ""
			if (p.session in canAllowRec):
				out = out + ", was able to permin recording"
				del canAllowRec[p.session]
			if (p.session in AllowedToRec):
				out = out + ", had the permission to record"
				del AllowedToRec[p.session]
			logger.debug('User: %s%s' % (p.name, out))
		except:
			logger.debug('User: %s' % (p.name))

	def channelCreated(self, c, current=None):
		logger = logging.getLogger('channelCreated')
		logger.debug("Channel: %s" % (c.name))

	def channelRemoved(self, c, current=None):
		logger = logging.getLogger('channelRemoved')
		logger.debug("Channel: %s" % (c.name))

	def channelStateChanged(self, c, current=None):
		logger = logging.getLogger('channelStateChanged')
		logger.debug("Channel: %s" % (c.name))


class ServerContextCallbackI(Murmur.ServerContextCallback):
	def __init__(self, server):
		self.server = server

	def contextAction(self, action, p, session, chanid, current=None):
		global AllowedToRec, ADMINALLOWSELF, canAllowRec

		logger = logging.getLogger('contextAction')

		if (action == "recdisallow"):
			UserState=self.server.getState(session) #Remove the user from AllowedToRec.
			try:
				del AllowedToRec[session]
				logger.info("User: %s revoked recording rights from: %s" % (p.name, UserState.name))
				self.server.sendMessageChannel(UserState.channel, 0, "<font style='color:red;font-weight:none;'>Die Aufnahmeerlaubnis des Benutzers \"%s\" wurde durch \"%s\" entzogen.</font>" % (UserState.name, p.name))

				if (UserState.recording == True): #If User is still recording deaf him.
					UserState.deaf = True
					self.server.setState(UserState)
			except:
				logger.debug("Could not revoke recording rights from: %s, not in List" % (session))

		#Do not allow Admins to permit themselfs to record.
		if (action == "recallow"):
			if ((p.session <> session) and (p.session in canAllowRec)):
				#Allow recording.
				UserState = self.server.getState(session)

				AllowedToRec[session] = p.channel #Add entry of sessionid and channelid to our dictionary.
				logger.info("User: %s granted recording rights to: %s" % (p.name, UserState.name))
				self.server.sendMessageChannel(UserState.channel, 0, "<font style='color:green;font-weight:none;'>Der Benutzer \"%s\" hat von \"%s\" die Erlaubnis bekommen aufzunehmen.</font>" % (UserState.name, p.name))

			else: #Admin wants to give himself permission to record.
				if (ADMINALLOWSELF == True):
					UserState=self.server.getState(session)

					AllowedToRec[session] = p.channel #Add entry of sessionid and channelid to our dictionary.
					logger.info("User: %s granted himself recording rights" % (UserState.name))
					self.server.sendMessageChannel(UserState.channel, 0, "<font style='color:green;font-weight:none;'>Der Benutzer \"%s\" hat sich selbst die Erlaubnis gegeben aufzunehmen.</font>" % (UserState.name))
				else:
					#Do not allow recording.
					UserState = self.server.getState(session)
					logger.debug("User: %s can't give himself recording rights" % (UserState.name))
					self.server.sendMessage(UserState.session, "<font style='color:red;font-weight:none;'>Nur ein anderer Administrator kann dir eine Aufnahmeerlaubnis erteilen :)</font>") 


if __name__ == "__main__":
	def on_exit(sig, func=None):
		logger = logging.getLogger('exit')
		logger.info("%s is terminating" % (myname))
		meta.removeCallback(metaR)
		ice.shutdown()
		os.unlink(pidfile)
		logger.info('Goodbye')
		logging.shutdown()
		sys.exit(0)
	signal.signal(signal.SIGTERM, on_exit)

	global contextR

	logger = logging.getLogger('main')
	logger.info("%s is starting" % myname)

	if os.path.isfile(pidfile):
		f = open(pidfile, "r")
		f.seek(0)
		old_pid = f.readline()
		f.close()
		if os.path.exists("/proc/%s" % old_pid):
			logger.info("%s is already running with pid: %s" % (myname, old_pid))
			sys.exit(1)
		else:
			logger.info("%s unclean shutdown, removing pidfile" % (myname))
			os.remove(pidfile)

	f = open(pidfile, 'w')
	f.write("%s" % os.getpid())
	f.close()
	logger.debug("created pidfile")


	prop = Ice.createProperties(sys.argv)
	prop.setProperty("Ice.ImplicitContext", "Shared")

	idd = Ice.InitializationData()
	idd.properties = prop

	ice = Ice.initialize(idd)

	logger.debug("creating callbacks")

	# If icesecret is set, we need to set it here as well.
	ice.getImplicitContext().put("secret", icesecret)

	meta = Murmur.MetaPrx.checkedCast(ice.stringToProxy('Meta:tcp -h 127.0.0.1 -p %s' % iceport))
	adapter = ice.createObjectAdapterWithEndpoints("Callback.Client", "tcp -h 127.0.0.1")

	metaR = Murmur.MetaCallbackPrx.uncheckedCast(adapter.addWithUUID(MetaCallbackI()))
	adapter.activate()

	meta.addCallback(metaR)

	for server in meta.getBootedServers():
		serverR = Murmur.ServerCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerCallbackI(server, adapter)))
		server.addCallback(serverR)

	logger.info('%s is running with pid: %d (press CTRL-C to quit)' % (myname, os.getpid()));
	try:
		ice.waitForShutdown()
	except KeyboardInterrupt:
		logger.info('CTRL-C caught, quitting')
		on_exit(signal.SIGINT)

