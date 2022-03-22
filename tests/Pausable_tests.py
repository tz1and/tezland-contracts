import smartpy as sp

pause_mixin = sp.io.import_script_from_url("file:contracts/Pausable.py")

class PausableTest(pause_mixin.Pausable, sp.Contract):
    def __init__(self, administrator):
        pause_mixin.Pausable.__init__(self, administrator = administrator)

    @sp.entry_point
    def testOnlyPaused(self):
        self.onlyPaused()

    @sp.entry_point
    def testOnlyUnpaused(self):
        self.onlyUnpaused()

    @sp.entry_point
    def testIsPaused(self, state):
        sp.set_type(state, sp.TBool)
        with sp.if_(self.isPaused() != state):
            sp.verify(False, "error")


@sp.add_test(name = "Pausable_tests", profile = True)
def test():
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Robert")
    scenario = sp.test_scenario()

    scenario.h1("Pausable contract")
    scenario.table_of_contents()

    # Let's display the accounts:
    scenario.h2("Accounts")
    scenario.show([admin, alice, bob])

    scenario.h2("Test Pausable")

    scenario.h3("Contract origination")
    pausable = PausableTest(admin.address)
    scenario += pausable

    scenario.verify(pausable.data.paused == False)

    scenario.h3("set_paused")
    pausable.set_paused(True).run(sender = bob, valid = False)
    pausable.set_paused(True).run(sender = alice, valid = False)
    pausable.set_paused(True).run(sender = admin)

    scenario.verify(pausable.data.paused == True)

    pausable.set_paused(False).run(sender = bob, valid = False)
    pausable.set_paused(False).run(sender = alice, valid = False)
    pausable.set_paused(False).run(sender = admin)

    scenario.verify(pausable.data.paused == False)

    scenario.h3("testOnlyUnpaused")
    pausable.testOnlyUnpaused().run(sender = bob)
    pausable.testOnlyUnpaused().run(sender = alice)
    pausable.testOnlyUnpaused().run(sender = admin)

    pausable.set_paused(True).run(sender = admin)

    pausable.testOnlyUnpaused().run(sender = bob, valid = False)
    pausable.testOnlyUnpaused().run(sender = alice, valid = False)
    pausable.testOnlyUnpaused().run(sender = admin, valid = False)

    scenario.h3("testOnlyPaused")
    pausable.testOnlyPaused().run(sender = bob)
    pausable.testOnlyPaused().run(sender = alice)
    pausable.testOnlyPaused().run(sender = admin)

    pausable.set_paused(False).run(sender = admin)

    pausable.testOnlyPaused().run(sender = bob, valid = False)
    pausable.testOnlyPaused().run(sender = alice, valid = False)
    pausable.testOnlyPaused().run(sender = admin, valid = False)

    scenario.h3("testIsPaused")
    pausable.testIsPaused(True).run(sender = bob, valid = False)
    pausable.testIsPaused(True).run(sender = alice, valid = False)
    pausable.testIsPaused(True).run(sender = admin, valid = False)
    pausable.testIsPaused(False).run(sender = alice)
    pausable.testIsPaused(False).run(sender = bob)
    pausable.testIsPaused(False).run(sender = admin)

    scenario.h3("is_paused view")
    scenario.verify(pausable.is_paused() == False)
    pausable.set_paused(True).run(sender = admin)
    scenario.verify(pausable.is_paused() == True)