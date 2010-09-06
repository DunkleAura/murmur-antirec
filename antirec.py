#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (c) 2010, Natenom / Natenom@googlemail.com
# Version: 0.0.3
# 2010-09-07

import Ice, sys
Ice.loadSlice("--all -I/usr/share/slice /usr/share/slice/Murmur.ice")
import Murmur

AllowedToRec={} #Temporary list of users allowed to record.
canallowrecording="canallowrecording" #Name of the group that is allowed to give others permission to record :)
                                      #This group and the members must be defined in the root channel.
iceport=6502

#Entries in the context menu:
msg_context_allow="Aufnahmeerlaubnis erteilen"
msg_context_disallow="Aufnahmeerlaubnis zurückziehen"

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
        
        #Check if user is allowed to record.
        if (UserState.recording==True) and (UserState.deaf==False) and not (p.session in AllowedToRec): #and not (p.channel == AllowedToRec[p.session]):
	    UserState.deaf=True
	    self.server.setState(UserState)

	    msg="<font style='color:red;background:yellow;'>User \"%s\" has been deafened because he started recording.</font>" % (UserState.name)
	    self.server.sendMessageChannel(UserState.channel, 0, msg)

	    #Callback is not implemented... if a user switches a channel :(
	    #if (p.channel == AllowedToRec[p.session]):
		#print "Erlaubnis gilt nur für KanalID %s, deshalb wurde sie entzogen" % AllowedToRec[p.session]
		##Deaf him and beat him...
	    #else:
	
    def userConnected(self, p, current=None):
	if (self.server.hasPermission(p.session, 0, Murmur.PermissionWrite)):
	      #Check if user is in group canallowrecording defined in the root channel.
	      ACL=self.server.getACL(0)
	      #ACL[0] = ACL
	      #ACL[1] = Groups
	      #ACL[2] = inherit
	      for gruppe in ACL[1]:
		  if (gruppe.name == canallowrecording):
		      if (p.userid in gruppe.members):
			  self.server.addContextCallback(p.session, "recallow", msg_context_allow, self.contextR, Murmur.ContextUser)
			  self.server.addContextCallback(p.session, "recdisallow", msg_context_disallow, self.contextR, Murmur.ContextUser)
		  	  break

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
	      #AllowedToRec.remove(session)
	      #AllowedToRec[session] = p.channel #Add entry of sessionid and channelid to our dictionary.
	      del AllowedToRec[session]
	      self.server.sendMessageChannel(UserState.channel,0, "<font style='color:red;font-weight:none;'>Die Aufnahmeerlaubnis des Benutzers \"%s\" wurde durch \"%s\" entzogen.</font>" % (UserState.name, p.name))
	      
	      if (UserState.recording == True): #If User is still recording deaf him.
		  UserState.deaf=True
		  self.server.setState(UserState)
	  except:
	      print "Could not delete %s, not in List." % (session)
      
      #Do not allow Admins to permit themselfs to record.
      if (action == "recallow") and not (p.session == session):
	  UserState=self.server.getState(session)
	      
	  AllowedToRec[session] = p.channel #Add entry of sessionid and channelid to our dictionary.
	  self.server.sendMessageChannel(UserState.channel,0, "<font style='color:green;font-weight:none;'>Der Benutzer \"%s\" hat von \"%s\" die Erlaubnis bekommen aufzunehmen.</font>" % (UserState.name, p.name))
      else:
	  UserState=self.server.getState(session)
	  self.server.sendMessage(UserState.session, "<font style='color:red;font-weight:none;'>Nur ein anderer Administrator kann dir eine Aufnahmeerlaubnis erteilen :)</font>") 


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

    meta = Murmur.MetaPrx.checkedCast(ice.stringToProxy('Meta:tcp -h 127.0.0.1 -p %s' % iceport))
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
