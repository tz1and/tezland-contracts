import smartpy as sp

fees_mixin = sp.io.import_script_from_url("file:contracts/Fees.py")

class FeesTest(fees_mixin.Fees, sp.Contract):
    def __init__(self, administrator):
        fees_mixin.Fees.__init__(self, administrator = administrator)


@sp.add_test(name = "Fees_tests", profile = True)
def test():
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Robert")
    scenario = sp.test_scenario()

    scenario.h1("Fees contract")
    scenario.table_of_contents()

    # Let's display the accounts:
    scenario.h2("Accounts")
    scenario.show([admin, alice, bob])

    scenario.h2("Test Fees")

    scenario.h3("Contract origination")
    fees = FeesTest(admin.address)
    scenario += fees

    #
    # update_fees
    #
    scenario.h3("update_fees")

    fees.update_fees(35).run(sender = bob, valid = False)
    fees.update_fees(250).run(sender = admin, valid = False)
    scenario.verify(fees.data.fees == sp.nat(25))
    fees.update_fees(45).run(sender = admin)
    scenario.verify(fees.data.fees == sp.nat(45))

    scenario.h3("update_fees_to")

    fees.update_fees_to(bob.address).run(sender = bob, valid = False)
    scenario.verify(fees.data.fees_to == admin.address)
    fees.update_fees_to(bob.address).run(sender = admin)
    scenario.verify(fees.data.fees_to == bob.address)