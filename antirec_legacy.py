#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (c) 2010, Natenom / Natenom@googlemail.com
# Version: 0.0.1
# 2010-08-31

# This scripts just sets state of a recording user to deaf and sends a notice to the channel.

import Ice, sys
Ice.loadSlice("--all -I/usr/share/slice /usr/share/slice/Murmur.ice")
import Murmur

#Temporary list of allowed users.
AllowedToRec=[]

class MetaCallbackI(Murmur.MetaCallback):
    def started(self, s, current=None):
        print "started"
        serverR=Murmur.ServerCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerCallbackI(server, current.adapter)))
        s.addCallback(serverR)

    def stopped(self, s, current=None):
        print "stopped"

class ServerCallbackI(Murmur.ServerCallback):
    def __init__(self, server, adapter):
      self.server = server

    def userStateChanged(self, p, current=None):
	"""Deafen recording users."""
        UserState=self.server.getState(p.session)
        if (UserState.recording==True) and (UserState.deaf==False):
	    UserState.deaf=True
	    self.server.setState(UserState)
	    
	    msg="<font style='color:red;background:yellow;'>User \"%s\" has been deafened because he started recording.</font>" % ( UserState.name )
	    self.server.sendMessageChannel(UserState.channel, 0, msg)
	
    def userConnected(self, p, current=None):
        print "User connected"

    def userDisconnected(self, p, current=None):
	    print "User disconnected"
	    
    def channelCreated(self, c, current=None):
      print "created"

    def channelRemoved(self, c, current=None):
      print "removed"

    def channelStateChanged(self, c, current=None):
      print "stateChanged"


if __name__ == "__main__":
    global contextR

    prop = Ice.createProperties(sys.argv)
    prop.setProperty("Ice.ImplicitContext", "Shared")

    idd = Ice.InitializationData()
    idd.properties = prop

    ice = Ice.initialize(idd)

    print "Creating callbacks...",

    # If icesecret is set, we need to set it here as well.
    ice.getImplicitContext().put("secret", "heidebubu")

    meta = Murmur.MetaPrx.checkedCast(ice.stringToProxy('Meta:tcp -h 127.0.0.1 -p 60000'))
    adapter = ice.createObjectAdapterWithEndpoints("Callback.Client", "tcp -h 127.0.0.1")
    
    metaR=Murmur.MetaCallbackPrx.uncheckedCast(adapter.addWithUUID(MetaCallbackI()))
    adapter.activate()
    
    meta.addCallback(metaR)

    for server in meta.getBootedServers():
      serverR=Murmur.ServerCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerCallbackI(server, adapter)))
      server.addCallback(serverR)

    print "Done"
    print 'Script running (press CTRL-C to abort)';
    try:
        ice.waitForShutdown()
    except KeyboardInterrupt:
        print 'CTRL-C caught, aborting'

    meta.removeCallback(metaR)
    ice.shutdown()
    print "Goodbye"
