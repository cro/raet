# -*- coding: utf-8 -*-
'''
Tests for the join transaction

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import time
import tempfile
import shutil

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing
from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import estating, keeping, stacking

if 'TEMP' in os.environ:
    TEMPDIR = os.environ['TEMP']
elif 'TMP' in os.environ:
    TEMPDIR = os.environ['TMP']
else:
    if sys.platform == 'win32':
        TEMPDIR = 'c:\temp'
        try:
            os.mkdir(TEMPDIR)
        except Exception:
            pass
    else:
        TEMPDIR = '/tmp'


def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self,
                       base,
                       name='',
                       ha=None,
                       main=None,
                       auto=raeting.autoModes.never):
        '''
        name is local estate name (which is stack name property)
        base is the base directory for the keep files
        auto is the auto accept status mode ()
        Creates odict and populates with data to setup road stack

        '''
        data = odict()
        data['name'] = name
        data['ha'] = ha
        data['main'] =  main
        data['auto'] = auto
        data['dirpath'] = os.path.join(base, 'road', 'keep', name)
        signer = nacling.Signer()
        data['sighex'] = signer.keyhex
        data['verhex'] = signer.verhex
        privateer = nacling.Privateer()
        data['prihex'] = privateer.keyhex
        data['pubhex'] = privateer.pubhex

        return data

    def createRoadStack(self,
                        data,
                        uid=None,
                        ha=None,
                        main=None,
                        auto=None,):
        '''
        Creates stack and local estate from data with
        and overrides with parameters

        returns stack

        '''
        stack = stacking.RoadStack(store=self.store,
                                   name=data['name'],
                                   uid=uid,
                                   ha=ha or data['ha'],
                                   sigkey=data['sighex'],
                                   prikey=data['prihex'],
                                   auto=auto or data['auto'],
                                   main=main or data['main'],
                                   dirpath=data['dirpath'],)

        return stack

    def join(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        if not initiator.remotes:
            remote =  initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=correspondent.local.ha))
            deid = remote.uid

        initiator.join(uid=deid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def allow(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        initiator.allow(uid=deid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def alive(self, initiator, correspondent, duid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do alive. Call from test method.
        '''
        console.terse("\nAlive Transaction **************\n")
        initiator.alive(uid=duid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def flushReceives(self, stack):
        '''
        Flush any queued up udp packets in receive buffer
        '''
        stack.serviceReceives()
        while stack.rxes:
            stack.rxes.popleft()

    def serviceStacks(self, stacks, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAll()
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.05)
            time.sleep(0.05)


    def testJoinBasic(self):
        '''
        Test join
        '''
        console.terse("{0}\n".format(self.testJoinBasic.__doc__))

        alphaData = self.createRoadData(base=self.base,
                                       name='alpha',
                                       ha=("", raeting.RAET_PORT),
                                       main=True,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                        name='beta',
                                        ha=("", raeting.RAET_TEST_PORT),
                                        main=None,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin from Beta to Alpha *********\n")
        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(beta.remotes), 0)
        self.join(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        console.terse("\nAllow Beta to Alpha *********\n")
        self.allow(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    '''
    Unittest runner
    '''
    tests =  []
    names = ['testJoinBasic',
              ]

    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    '''
    Unittest runner
    '''
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    #runAll() #run all unittests

    runSome()#only run some

    #runOne('testJoinFromMain')
