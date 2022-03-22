import smartpy as sp

minter_contract = sp.io.import_script_from_url("file:contracts/TL_Minter.py")
tokens = sp.io.import_script_from_url("file:contracts/Tokens.py")

@sp.add_test(name = "TL_Minter_tests", profile = True)
def test():
    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob   = sp.test_account("Robert")
    scenario = sp.test_scenario()

    scenario.h1("Minter Tests")
    scenario.table_of_contents()

    # Let's display the accounts:
    scenario.h1("Accounts")
    scenario.show([admin, alice, bob])

    # create a FA2 contract for testing
    scenario.h1("Create test env")
    items_tokens = tokens.tz1andItems(
        metadata = sp.utils.metadata_of_url("https://example.com"),
        admin = admin.address)
    scenario += items_tokens

    places_tokens = tokens.tz1andPlaces(
        metadata = sp.utils.metadata_of_url("https://example.com"),
        admin = admin.address)
    scenario += places_tokens

    # create minter contract
    scenario.h1("Test Minter")
    minter = minter_contract.TL_Minter(admin.address, items_tokens.address, places_tokens.address,
        metadata = sp.utils.metadata_of_url("https://example.com"))
    scenario += minter

    # set items_tokens and places_tokens administrator to minter contract
    items_tokens.transfer_administrator(minter.address).run(sender = admin)
    places_tokens.transfer_administrator(minter.address).run(sender = admin)
    minter.accept_fa2_administrator([items_tokens.address, places_tokens.address]).run(sender = admin)

    # test admin stuff
    scenario.h2("transfer_administrator")
    scenario.verify(minter.data.administrator == admin.address)
    minter.transfer_administrator(alice.address).run(sender = admin)
    minter.accept_administrator().run(sender = alice)
    scenario.verify(minter.data.administrator == alice.address)
    minter.transfer_administrator(admin.address).run(sender = alice)
    minter.accept_administrator().run(sender = admin)

    # test set_paused
    scenario.h2("set_paused")
    minter.set_paused(True).run(sender = bob, valid = False)
    minter.set_paused(False).run(sender = alice, valid = False)
    minter.set_paused(True).run(sender = admin)
    scenario.verify(minter.data.paused == True)
    minter.set_paused(False).run(sender = admin)
    scenario.verify(minter.data.paused == False)

    # test Item minting
    scenario.h2("mint_Item")
    minter.mint_Item(to_ = bob.address,
        amount = 4,
        royalties = 250,
        contributors = [ sp.record(address=bob.address, relative_royalties=sp.nat(1000), role=sp.variant("minter", sp.unit)) ],
        metadata = sp.utils.bytes_of_string("test_metadata")).run(sender = bob)

    minter.mint_Item(to_ = alice.address,
        amount = 25,
        royalties = 250,
        contributors = [ sp.record(address=alice.address, relative_royalties=sp.nat(1000), role=sp.variant("minter", sp.unit)) ],
        metadata = sp.utils.bytes_of_string("test_metadata")).run(sender = alice)

    minter.set_paused(True).run(sender = admin)

    minter.mint_Item(to_ = alice.address,
        amount = 25,
        royalties = 250,
        contributors = [ sp.record(address=alice.address, relative_royalties=sp.nat(1000), role=sp.variant("minter", sp.unit)) ],
        metadata = sp.utils.bytes_of_string("test_metadata")).run(sender = alice, valid = False)

    minter.set_paused(False).run(sender = admin)

    # test Place minting
    scenario.h2("mint_Place")

    # only admin can mint
    minter.mint_Place([sp.record(
        to_ = bob.address,
        metadata = {'': sp.utils.bytes_of_string("test_metadata")}
    )]).run(sender = bob, valid = False)

    minter.mint_Place([sp.record(
        to_ = alice.address,
        metadata = {'': sp.utils.bytes_of_string("test_metadata")}
    )]).run(sender = alice, valid = False)

    minter.mint_Place([sp.record(
        to_ = admin.address,
        metadata = {'': sp.utils.bytes_of_string("test_metadata")}
    )]).run(sender = admin)

    # no minting while paused
    minter.set_paused(True).run(sender = admin)

    minter.mint_Place([sp.record(
        to_ = admin.address,
        metadata = {'': sp.utils.bytes_of_string("test_metadata")}
    )]).run(sender = admin, valid=False, exception="ONLY_UNPAUSED")

    minter.set_paused(False).run(sender = admin)

    # mint multiple
    minter.mint_Place([
        sp.record(
            to_ = admin.address,
            metadata = {'': sp.utils.bytes_of_string("test_metadata")}
        ),
        sp.record(
            to_ = alice.address,
            metadata = {'': sp.utils.bytes_of_string("test_metadata")}
        ),
        sp.record(
            to_ = bob.address,
            metadata = {'': sp.utils.bytes_of_string("test_metadata")}
        )
    ]).run(sender = admin)

    # test get_item_royalties view
    #scenario.h2("get_item_royalties")
    #scenario.p("It's a view")
    #view_res = minter.get_item_royalties(sp.nat(0))
    #scenario.verify(view_res.royalties == 250)
    #scenario.verify(view_res.creator == bob.address)

    # test pause_all_fa2
    scenario.h2("pause_all_fa2")

    # check tokens are unpaused to begin with
    scenario.verify(items_tokens.data.paused == False)
    scenario.verify(places_tokens.data.paused == False)

    minter.pause_all_fa2(True).run(sender = alice, valid = False, exception = "ONLY_ADMIN")
    minter.pause_all_fa2(True).run(sender = admin)

    # check tokens are paused
    scenario.verify(items_tokens.data.paused == True)
    scenario.verify(places_tokens.data.paused == True)

    minter.pause_all_fa2(False).run(sender = bob, valid = False, exception = "ONLY_ADMIN")
    minter.pause_all_fa2(False).run(sender = admin)

    # check tokens are unpaused
    scenario.verify(items_tokens.data.paused == False)
    scenario.verify(places_tokens.data.paused == False)

    #  test clear_adhoc_operators_all_fa2
    scenario.h2("clear_adhoc_operators_all_fa2")

    items_tokens.update_adhoc_operators(sp.variant("add_adhoc_operators", [
        sp.record(operator=minter.address, token_id=0),
        sp.record(operator=minter.address, token_id=1),
        sp.record(operator=minter.address, token_id=2),
        sp.record(operator=minter.address, token_id=3),
    ])).run(sender = alice)

    places_tokens.update_adhoc_operators(sp.variant("add_adhoc_operators", [
        sp.record(operator=minter.address, token_id=0),
        sp.record(operator=minter.address, token_id=1),
        sp.record(operator=minter.address, token_id=2),
        sp.record(operator=minter.address, token_id=3),
    ])).run(sender = alice)

    scenario.verify(sp.len(items_tokens.data.adhoc_operators) == 4)
    scenario.verify(sp.len(places_tokens.data.adhoc_operators) == 4)

    minter.clear_adhoc_operators_all_fa2().run(sender = alice, valid = False, exception = "ONLY_ADMIN")
    minter.clear_adhoc_operators_all_fa2().run(sender = bob, valid = False, exception = "ONLY_ADMIN")
    minter.clear_adhoc_operators_all_fa2().run(sender = admin)

    scenario.verify(sp.len(items_tokens.data.adhoc_operators) == 0)
    scenario.verify(sp.len(places_tokens.data.adhoc_operators) == 0)

    scenario.table_of_contents()
