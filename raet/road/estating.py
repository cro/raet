# -*- coding: utf-8 -*-
'''
estating.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611

import socket
import uuid
from collections import deque

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding
from ioflo.base import storing

from .. import raeting
from .. import nacling
from .. import lotting

from ioflo.base.consoling import getConsole
console = getConsole()

class Estate(lotting.Lot):
    '''
    RAET protocol endpoint estate object ie Road Lot
    '''

    def __init__(self,
                 stack,
                 name="",
                 prefix='road',
                 ha=None,
                 uid=None,
                 tid=0,
                 host="",
                 port=raeting.RAET_PORT,
                 role=None,
                 **kwa):
        '''
        Setup instance

        stack is required parameter
        '''
        name = name or "{0}_{1}".format(prefix, uuid.uuid1().hex)
        uid = uid if uid is not None else stack.nextUid()
        super(Estate, self).__init__(stack=stack, name=name, ha=ha, uid=uid, **kwa)

        self.tid = tid # current transaction ID

        if ha:  # takes precedence
            host, port = ha
        self.host = socket.gethostbyname(host)
        self.port = port
        if self.host == '0.0.0.0':
            host = '127.0.0.1'
        else:
            host = self.host
        self.fqdn = socket.getfqdn(host)
        self.role = role if role is not None else self.name
        self.transactions = odict() # estate transactions keyed by transaction index

    @property
    def ha(self):
        '''
        property that returns ip address (host, port) tuple
        '''
        return (self.host, self.port)

    @ha.setter
    def ha(self, value):
        '''
        Expects value is tuple of (host, port)
        '''
        self.host, self.port = value

    def nextTid(self):
        '''
        Generates next transaction id number.
        '''
        self.tid += 1
        if self.tid > 0xffffffffL:
            self.tid = 1  # rollover to 1
        return self.tid

    def addTransaction(self, index, transaction):
        '''
        Safely add transaction at index, If not already there

        index of the form
        (rf, le, re, si, ti, bf)

        Where
        rf = Remotely Initiated Flag, RmtFlag
        le = leid, local estate id LEID
        re = reid, remote estate id REID
        si = sid, Session ID, SID
        ti = tid, Transaction ID, TID
        bf = Broadcast Flag, BcstFlag
        '''
        self.transactions[index] = transaction
        transaction.remote = self
        console.verbose( "Added transaction to {0} at '{1}'\n".format(self.name, index))

    def removeTransaction(self, index, transaction=None):
        '''
        Safely remove transaction at index, If transaction identity same
        If transaction is None then remove without comparing identity
        '''
        if index in self.transactions:
            if transaction:
                if transaction is self.transactions[index]:
                    del  self.transactions[index]
            else:
                del self.transactions[index]

    def removeStaleTransactions(self):
        '''
        Remove stale transactions associated with estate
        '''
        pass

    def process(self):
        '''
        Call .process or all transactions to allow timer based processing
        '''
        for transaction in self.transactions.values():
            transaction.process()

class LocalEstate(Estate):
    '''
    RAET protocol endpoint local estate object ie Local Road Lot
    Maintains signer for signing and privateer for encrypt/decrypt
    '''
    def __init__(self,
                 sigkey=None,
                 prikey=None,
                 **kwa):
        '''
        Setup instance

        stack is required argument

        sigkey is either nacl SigningKey or hex encoded key
        prikey is either nacl PrivateKey or hex encoded key
        '''
        super(LocalEstate, self).__init__( **kwa)
        self.signer = nacling.Signer(sigkey)
        self.priver = nacling.Privateer(prikey) # Long term key

class RemoteEstate(Estate):
    '''
    RAET protocol endpoint remote estate object ie Remote Road Lot
    Maintains verifier for verifying signatures and publican for encrypt/decrypt

    .alived attribute is the dead or alive status of the remote

    .alived = True, alive, recently have received valid signed packets from remote
    .alive = False, dead, recently have not received valid signed packets from remote

    .fuid is the far uid of the remote as owned by the farside stack
    '''

    def __init__(self,
                 stack,
                 prefix='estate',
                 uid=None,
                 fuid=0,
                 verkey=None,
                 pubkey=None,
                 acceptance=None,
                 joined=None,
                 rsid=0,
                 **kwa):
        '''
        Setup instance

        stack is required parameter

        verkey is either nacl VerifyKey or raw or hex encoded key
        pubkey is either nacl PublicKey or raw or hex encoded key

        acceptance is accepted state of remote on Road

        rsid is last received session id used by remotely initiated transaction


        '''
        if uid is None:
            uid = stack.nextUid()
            while uid in stack.remotes or uid == stack.local.uid:
                uid = stack.nextUid()

        if 'host' not in kwa and 'ha' not in kwa:
            kwa['ha'] = ('127.0.0.1', raeting.RAET_TEST_PORT)
        super(RemoteEstate, self).__init__(stack, prefix=prefix, uid=uid, **kwa)
        self.fuid = fuid
        self.joined = joined
        self.allowed = None
        self.alived = None
        self.reaped = None
        self.acceptance = acceptance
        self.privee = nacling.Privateer() # short term key manager
        self.publee = nacling.Publican() # correspondent short term key  manager
        self.verfer = nacling.Verifier(verkey) # correspondent verify key manager
        self.pubber = nacling.Publican(pubkey) # correspondent long term key manager

        self.rsid = rsid # last sid received from remote when RmtFlag is True

        # persistence keep alive heartbeat timer. Initial duration has offset so
        # not synced with other side persistence heatbeet
        # by default do not use offset on main
        if self.stack.main:
            duration = self.stack.period
        else:
            duration = self.stack.period + self.stack.offset
        self.timer = aiding.StoreTimer(store=self.stack.store,
                                       duration=duration)

        self.reapTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.stack.interim)
        self.messages = deque() # deque of saved stale message body data to remote.uid

    #@property
    #def nuid(self):
        #'''
        #property that returns near uid of remote as owned by nearside stack
        #alias for uid
        #'''
        #return self.uid

    #@name.setter
    #def nuid(self, value):
        #'''
        #setter for nuid property
        #'''
        #self.uid = value

    #@property
    #def puid(self):
        #'''
        #property that returns duple of (nuid, fuid)
        #'''
        #return (self.nuid, self.fuid)

    #@puid.setter
    #def puid(self, value):
        #'''
        #setter for puid property, value is duple of (nuid, fuid)
        #'''
        #self.nuid, self.fuid = value

    def rekey(self):
        '''
        Regenerate short term keys
        '''
        self.allowed = None
        self.privee = nacling.Privateer() # short term key
        self.publee = nacling.Publican() # correspondent short term key  manager

    def validRsid(self, rsid):
        '''
        Compare new rsid to old .rsid and return True
        If new is >= old modulo N where N is 2^32 = 0x100000000
        And >= means the difference is less than N//2 = 0x80000000
        (((new - old) % 0x100000000) < (0x100000000 // 2))
        '''
        return self.validateSid(new=rsid, old=self.rsid)

    def refresh(self, alived=True):
        '''
        Restart presence heartbeat timer and conditionally reapTimer
        If alived is None then do not change .alived  but update timer
        If alived is True then set .alived to True and handle implications
        If alived is False the set .alived to False and handle implications
        '''
        self.timer.restart(duration=self.stack.period)
        if alived is None:
            return

        if self.alived or alived: # alive before or after
            self.reapTimer.restart()
            if self.reaped:
                self.unreap()
        #otherwise let timer run both before and after are still dead
        self.alived = alived

    def manage(self, cascade=False, immediate=False):
        '''
        Perform time based processing of keep alive heatbeat
        '''
        if not self.reaped: # only manage alives if not already reaped
            if immediate or self.timer.expired:
                # alive transaction restarts self.timer
                self.stack.alive(duid=self.uid, cascade=cascade)
            if self.stack.interim >  0.0 and self.reapTimer.expired:
                self.reap()

    def reap(self):
        '''
        Remote is dead, reap it if main estate.
        '''
        if self.stack.main: # only main can reap
            console.concise("Stack {0}: Reaping dead remote {1} at {2}\n".format(
                    self.stack.name, self.name, self.stack.store.stamp))
            self.stack.incStat("remote_reap")
            self.reaped = True
            #self.stack.removeRemote(self, clear=False) #remove from memory but not disk

    def unreap(self):
        '''
        Remote packet received from remote so not dead anymore.
        '''
        if self.stack.main: # only only main can reap or unreap
            console.concise("Stack {0}: Unreaping dead remote {1} at {2}\n".format(
                    self.stack.name, self.name, self.stack.store.stamp))
            self.stack.incStat("remote_unreap")
            self.reaped = False

    def removeStaleCorrespondents(self, renew=False):
        '''
        Remove stale correspondent transactions associated with remote

        If renew then remove all correspondents from this remote with nonzero sid

        Stale means the sid in the transaction is older than the current .rsid
        or if renew (rejoining with .rsid == zero)

        When sid in index is older than remote.rsid
        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        for index, transaction in self.transactions.items():
            sid = index[3]
            rf = index[0]
            if rf and  ((renew and sid != 0) or (not renew and not self.validRsid(sid))):
                transaction.nack()
                self.removeTransaction(index)
                emsg = ("Stack {0}: Stale correspondent {1} from remote {1} at {2}"
                            "\n".format(self.stack.name,
                                        index,
                                        self.name,
                                        self.stack.store.stamp))
                console.terse(emsg)
                self.stack.incStat('stale_correspondent')

    def replaceStaleInitiators(self, renew=False):
        '''
        Save and remove any messages from messenger transactions initiated locally
        with remote

        Remove non message stale initiator transactions associated with remote

        If renew Then remove all initiators from this remote with nonzero sid

        Stale means the sid in the transaction is older than the current .sid
        or if renew (rejoining with .sid == zero)

        When sid in index is older than remote.sid

        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        for index, transaction in self.transactions.items():
            sid = index[3]
            rf = index[0]
            if not rf and ((renew and sid != 0) or (not renew and not self.validSid(sid))):
                if transaction.kind in [raeting.trnsKinds.message]:
                    self.saveMessage(transaction)
                transaction.nack()
                self.removeTransaction(index)
                emsg = ("Stack {0}: Stale initiator {1} to remote {2} at {3}"
                        "\n".format(self.stack.name,
                                    index,
                                    self.name,
                                    self.stack.store.stamp))
                console.terse(emsg)
                self.stack.incStat('stale_initiator')

    def saveMessage(self, messenger):
        '''
        Message is Messenger compatible transaction
        Save copy of body data from stale initiated message on .messages deque
        for retransmitting later after new session is established
        '''
        self.messages.append(odict(messenger.tray.body))
        emsg = ("Stack {0}: Saved stale message with remote {1} at {2}"
                                                "\n".format(self.stack.name, index, self.name))
        console.concise(emsg)

    def sendSavedMessages(self):
        '''
        Message is Messenger compatible transaction
        Save stale initiated message for retransmitting later after new session is established
        '''
        while self.messages:
            body = self.messages.popleft()
            self.stack.message(body=body, duid=self.uid)
            emsg = ("Stack {0}: Resent saved message with remote {1} at {2}"
                                        "\n".format(self.stack.name, index, self.name))
            console.concise(emsg)

    def allowInProcess(self):
        '''
        Returns list of transactions for all allow transactions with this remote
        that are already in process
        '''
        return ([t for t in self.transactions.values()
                     if t.kind == raeting.trnsKinds.allow])

    def joinInProcess(self):
        '''
        Returns  list of transactions for all join transaction with this remote
        that are already in process
        '''
        return ([t for t in self.transactions.values()
                     if t.kind == raeting.trnsKinds.join])

    def yokeInProcess(self):
        '''
        Returns  list of transactions for all yoke transaction with this remote
        that are already in process
        '''
        return ([t for t in self.transactions.values()
                     if t.kind == raeting.trnsKinds.yoke])
