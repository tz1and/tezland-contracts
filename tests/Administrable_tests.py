import smartpy as sp

admin_mixin = sp.io.import_script_from_url("file:contracts/Administrable.py")

class AdministrableTest(admin_mixin.Administrable, sp.Contract):
    def __init__(self, administrator):
        admin_mixin.Administrable.__init__(self, administrator = administrator)

    @sp.entry_point
    def testOnlyAdmin(self):
        self.onlyAdministrator()

    @sp.entry_point
    def testIsAdmin(self, address):
        sp.set_type(address, sp.TAddress)
        with sp.if_(~self.isAdministrator(address)):
            sp.verify(False, "error")


@sp.add_test(name = "Administrable_tests", profile = True)
def test():
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Robert")
    scenario = sp.test_scenario()

    scenario.h1("Administrable contract")
    scenario.table_of_contents()

    # Let's display the accounts:
    scenario.h2("Accounts")
    scenario.show([admin, alice, bob])

    scenario.h2("Test Administrable")

    scenario.h3("Contract origination")
    administrable = AdministrableTest(admin.address)
    scenario += administrable

    scenario.verify(administrable.data.administrator == admin.address)

    scenario.h3("onlyAdministrator")
    administrable.testOnlyAdmin().run(sender = bob, valid = False)
    administrable.testOnlyAdmin().run(sender = alice, valid = False)
    administrable.testOnlyAdmin().run(sender = admin)

    scenario.h3("isAdministrator")
    administrable.testIsAdmin(bob.address).run(sender = bob, valid = False)
    administrable.testIsAdmin(bob.address).run(sender = alice, valid = False)
    administrable.testIsAdmin(bob.address).run(sender = admin, valid = False)
    administrable.testIsAdmin(admin.address).run(sender = alice)
    administrable.testIsAdmin(admin.address).run(sender = bob)
    administrable.testIsAdmin(admin.address).run(sender = admin)

    scenario.h3("transfer_administrator")
    administrable.transfer_administrator(bob.address).run(sender = bob, valid = False, exception = "ONLY_ADMIN")
    administrable.transfer_administrator(bob.address).run(sender = alice, valid = False, exception = "ONLY_ADMIN")
    administrable.transfer_administrator(bob.address).run(sender = admin)

    scenario.verify(administrable.data.proposed_administrator == sp.some(bob.address))

    administrable.accept_administrator().run(sender = admin, valid = False, exception = "NOT_PROPOSED_ADMIN")
    administrable.accept_administrator().run(sender = alice, valid = False, exception = "NOT_PROPOSED_ADMIN")
    administrable.accept_administrator().run(sender = bob)

    scenario.verify(administrable.data.proposed_administrator == sp.none)
    scenario.verify(administrable.data.administrator == bob.address)

    administrable.transfer_administrator(admin.address).run(sender = admin, valid = False, exception = "ONLY_ADMIN")

    administrable.accept_administrator().run(sender = admin, valid = False, exception = "NO_ADMIN_TRANSFER")
    administrable.accept_administrator().run(sender = alice, valid = False, exception = "NO_ADMIN_TRANSFER")
    administrable.accept_administrator().run(sender = bob, valid = False, exception = "NO_ADMIN_TRANSFER")

    scenario.h3("get_administrator view")

    scenario.verify(administrable.get_administrator() != admin.address)
    scenario.verify(administrable.get_administrator() == bob.address)