import smartpy as sp

tokens = sp.io.import_script_from_url("file:contracts/Tokens.py")
permitted_fa2 = sp.io.import_script_from_url("file:contracts/PermittedFA2.py")

class PermittedFA2Test(permitted_fa2.PermittedFA2, sp.Contract):
    def __init__(self, administrator):
        permitted_fa2.PermittedFA2.__init__(self, administrator = administrator)

    # test helpers
    @sp.entry_point
    def testOnlyPermittedFA2(self, fa2):
        self.onlyPermittedFA2(fa2)

    @sp.entry_point
    def testGetPermittedFA2Props(self, fa2):
        self.getPermittedFA2Props(fa2)


@sp.add_test(name = "PermittedFA2_tests", profile = True)
def test():
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Robert")
    carol   = sp.test_account("Carol")
    scenario = sp.test_scenario()

    scenario.h1("PermittedFA2 contract")
    scenario.table_of_contents()

    # Let's display the accounts:
    scenario.h2("Accounts")
    scenario.show([admin, alice, bob])

    scenario.h2("Test PermittedFA2")

    scenario.h3("Contract origination")

    permitted = PermittedFA2Test(admin.address)
    scenario += permitted

    scenario.h4("some other FA2 token")
    other_token = tokens.tz1andItems(
        metadata = sp.utils.metadata_of_url("https://example.com"),
        admin = admin.address)
    scenario += other_token

    # test set permitted
    scenario.h3("set_fa2_permitted")
    add_permitted = sp.list([sp.variant("add_permitted",
        sp.record(
            fa2 = other_token.address,
            props = sp.record(
                swap_allowed = True,
                royalties_kind = sp.variant("tz1and", sp.unit))))])

    remove_permitted = sp.list([sp.variant("remove_permitted", other_token.address)])

    # no permission
    permitted.set_fa2_permitted(add_permitted).run(sender = bob, valid = False, exception = "ONLY_ADMIN")
    scenario.verify(permitted.data.permitted_fa2.contains(other_token.address) == False)

    # add
    permitted.set_fa2_permitted(add_permitted).run(sender = admin)
    scenario.verify(permitted.data.permitted_fa2.contains(other_token.address) == True)
    scenario.verify(permitted.data.permitted_fa2[other_token.address].swap_allowed == True)

    # remove
    permitted.set_fa2_permitted(remove_permitted).run(sender = admin)
    scenario.verify(permitted.data.permitted_fa2.contains(other_token.address) == False)
    scenario.verify(sp.is_failing(permitted.data.permitted_fa2[other_token.address]))

    # test get
    scenario.h3("get_fa2_permitted view")
    scenario.verify(sp.is_failing(permitted.get_fa2_permitted(other_token.address)))
    permitted.set_fa2_permitted(add_permitted).run(sender = admin)
    scenario.verify(permitted.get_fa2_permitted(other_token.address) == sp.record(swap_allowed = True, royalties_kind = sp.variant("tz1and", sp.unit)))

    scenario.h3("is_fa2_permitted view")
    scenario.verify(permitted.is_fa2_permitted(other_token.address) == True)
    permitted.set_fa2_permitted(remove_permitted).run(sender = admin)
    scenario.verify(permitted.is_fa2_permitted(other_token.address) == False)

    scenario.h3("testOnlyPermittedFA2")
    permitted.testOnlyPermittedFA2(other_token.address).run(sender = admin, valid = False, exception = "TOKEN_NOT_PERMITTED")
    permitted.set_fa2_permitted(add_permitted).run(sender = admin)
    permitted.testOnlyPermittedFA2(other_token.address).run(sender = admin)

    scenario.h3("testGetPermittedFA2Props")
    permitted.testOnlyPermittedFA2(other_token.address).run(sender = admin)
    permitted.set_fa2_permitted(remove_permitted).run(sender = admin)
    permitted.testOnlyPermittedFA2(other_token.address).run(sender = admin, valid = False, exception = "TOKEN_NOT_PERMITTED")
