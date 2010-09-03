#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (c) 2010, Natenom / Natenom@googlemail.com
# Version: 0.0.2
# 2010-09-02

import Ice, sys
Ice.loadSlice("--all -I/usr/share/slice /usr/share/slice/Murmur.ice")
import Murmur

AllowedToRec=[] #Liste der Benutzer die aufnehmen duerfen.

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
      self.contextR=Murmur.ServerContextCallbackPrx.uncheckedCast(adapter.addWithUUID(ServerContextCallbackI(server)))

    def userStateChanged(self, p, current=None):
        """Wer aufnimmt, wird stumm-taub gestellt."""
        global AllowedToRec
        UserState=self.server.getState(p.session)
        
        if (UserState.recording==True) and (UserState.deaf==False) and not (p.session in AllowedToRec):
	    UserState.deaf=True
	    self.server.setState(UserState)
	    
	    msg="<font style='color:red;background:yellow;'>User \"%s\" has been deafened because he started recording.</font>" % ( UserState.name )
	    self.server.sendMessageChannel(UserState.channel, 0, msg)
	
    def userConnected(self, p, current=None):
	if (self.server.hasPermission(p.session, 0, Murmur.PermissionWrite)):
	    print "Is a global admin"
	    self.server.addContextCallback(p.session, "recallow", "Aufnahmeerlaubnis erteilen", self.contextR, Murmur.ContextUser)
	    self.server.addContextCallback(p.session, "recdisallow", "Aufnahmeerlaubnis zurückziehen", self.contextR, Murmur.ContextUser)

    def userDisconnected(self, p, current=None):
	    print "User disconnected"
	    
    def channelCreated(self, c, current=None):
      print "created"

    def channelRemoved(self, c, current=None):
      print "removed"

    def channelStateChanged(self, c, current=None):
      print "stateChanged"


class ServerContextCallbackI(Murmur.ServerContextCallback):
    def __init__(self, server):
      self.server = server

    def contextAction(self, action, p, session, chanid, current=None):
      global AllowedToRec
      
      if (action == "recdisallow"):
	  UserState=self.server.getState(session) #Remove the user from AllowedToRec.
	  try:
	      AllowedToRec.remove(session)
	      self.server.sendMessageChannel(UserState.channel,0, "<font style='color:red;font-weight:none;'>Die Aufnahmeerlaubnis des Benutzers \"%s\" wurde durch \"%s\" entzogen.</font>" % (UserState.name, p.name))
	      
	      if (UserState.recording == True): #If User is still recording deaf him.
		  UserState.deaf=True
		  self.server.setState(UserState)
	  except:
	      print "Could not delete %s, not in List." % (session)

      if (action == "recallow"):
	  UserState=self.server.getState(session)

	  AllowedToRec.append(session) #Add to List of recorders.
	  self.server.sendMessageChannel(UserState.channel,0, "<font style='color:green;font-weight:none;'>Der Benutzer \"%s\" hat von \"%s\" die Erlaubnis bekommen aufzunehmen.</font>" % (UserState.name, p.name))
        


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
