import smartpy as sp

pause_mixin = sp.io.import_script_from_url("file:contracts/Pausable.py")
whitelist_mixin = sp.io.import_script_from_url("file:contracts/Whitelist.py")
fees_mixin = sp.io.import_script_from_url("file:contracts/Fees.py")
mod_mixin = sp.io.import_script_from_url("file:contracts/Moderation.py")
permitted_fa2 = sp.io.import_script_from_url("file:contracts/PermittedFA2.py")
upgradeable_mixin = sp.io.import_script_from_url("file:contracts/Upgradeable.py")
utils = sp.io.import_script_from_url("file:contracts/Utils.py")

# TODO: test royalties for item token

# Optional extension argument type.
# Map val can contain about anything and be
# unpacked with sp.unpack.
extensionArgType = sp.TOption(sp.TMap(sp.TString, sp.TBytes))

#
# Dutch auction contract.
# NOTE: should be pausable for code updates.
class TL_Dutch(
    pause_mixin.Pausable,
    whitelist_mixin.Whitelist,
    fees_mixin.Fees,
    mod_mixin.Moderation,
    upgradeable_mixin.Upgradeable,
    permitted_fa2.PermittedFA2,
    sp.Contract):
    """A simple dutch auction.
    
    The price keeps dropping until end_time is reached. First valid bid gets the token.
    """
    AUCTION_TYPE = sp.TRecord(
        owner=sp.TAddress,
        token_id=sp.TNat,
        start_price=sp.TMutez,
        end_price=sp.TMutez,
        start_time=sp.TTimestamp,
        end_time=sp.TTimestamp,
        fa2=sp.TAddress
    ).layout(("owner", ("token_id", ("start_price",
        ("end_price", ("start_time", ("end_time", "fa2")))))))

    def __init__(self, administrator, items_contract, places_contract, metadata, exception_optimization_level="default-line"):
        self.add_flag("exceptions", exception_optimization_level)
        self.add_flag("erase-comments")
        
        self.init_storage(
            items_contract = items_contract,
            metadata = metadata,
            secondary_enabled = sp.bool(False), # If the secondary market is enabled.
            auction_id = sp.nat(0), # the auction id counter.
            granularity = sp.nat(60), # Globally controls the granularity of price drops. in seconds.
            auctions = sp.big_map(tkey=sp.TNat, tvalue=TL_Dutch.AUCTION_TYPE)
        )
        pause_mixin.Pausable.__init__(self, administrator = administrator)
        whitelist_mixin.Whitelist.__init__(self, administrator = administrator)
        fees_mixin.Fees.__init__(self, administrator = administrator)
        mod_mixin.Moderation.__init__(self, administrator = administrator)
        upgradeable_mixin.Upgradeable.__init__(self, administrator = administrator,
            entrypoints = ['create', 'cancel', 'bid'])

        default_permitted = { places_contract : sp.record(
            swap_allowed = True,
            royalties_kind = sp.variant("none", sp.unit) )}
        permitted_fa2.PermittedFA2.__init__(self, administrator = administrator, default_permitted = default_permitted)
        self.generate_contract_metadata()

    def generate_contract_metadata(self):
        """Generate a metadata json file with all the contract's offchain views
        and standard TZIP-12 and TZIP-016 key/values."""
        metadata_base = {
            "name": 'tz1and Dutch Auctions',
            "description": 'tz1and Places and Items Dutch auctions',
            "version": "1.0.0",
            "interfaces": ["TZIP-012", "TZIP-016"],
            "authors": [
                "852Kerfunkle <https://github.com/852Kerfunkle>"
            ],
            "homepage": "https://www.tz1and.com",
            "source": {
                "tools": ["SmartPy"],
                "location": "https://github.com/tz1and",
            },
            "license": { "name": "MIT" }
        }
        offchain_views = []
        for f in dir(self):
            attr = getattr(self, f)
            if isinstance(attr, sp.OnOffchainView):
                # Include onchain views as tip 16 offchain views
                offchain_views.append(attr)
        metadata_base["views"] = offchain_views
        self.init_metadata("metadata_base", metadata_base)

    #
    # Inlineable helpers
    #
    def onlyAdminIfSecondaryDisabled(self):
        """Fails if secondary is disabled and sender is not admin"""
        with sp.if_(~ self.data.secondary_enabled):
            self.onlyAdministrator()

    #
    # Manager-only entry points
    #
    @sp.entry_point
    def set_granularity(self, granularity):
        """Set granularity in seconds."""
        sp.set_type(granularity, sp.TNat)
        self.onlyAdministrator()
        self.data.granularity = granularity


    @sp.entry_point
    def set_secondary_enabled(self, enabled):
        """Set secondary market enabled."""
        sp.set_type(enabled, sp.TBool)
        self.onlyAdministrator()
        self.data.secondary_enabled = enabled

    #
    # Public entry points
    #
    @sp.entry_point(lazify = True)
    def create(self, params):
        """Create a dutch auction.
        
        Transfers token to auction contract.
        
        end_price must be < than start_price.
        end_time must be > than start_time
        """
        sp.set_type(params, sp.TRecord(
            token_id = sp.TNat,
            start_price = sp.TMutez,
            end_price = sp.TMutez,
            start_time = sp.TTimestamp,
            end_time = sp.TTimestamp,
            fa2 = sp.TAddress,
            extension = extensionArgType
        ).layout(("token_id", ("start_price", ("end_price",
            ("start_time", ("end_time", ("fa2", "extension"))))))))

        self.onlyUnpaused()
        self.onlyAdminIfSecondaryDisabled()

        # verify inputs
        self.onlyPermittedFA2(params.fa2)
        sp.verify((params.start_time >= sp.now) &
            (params.start_time < params.end_time) &
            (abs(params.end_time - params.start_time) > self.data.granularity) &
            (params.start_price >= params.end_price), message = "INVALID_PARAM")

        # call fa2_balance or is_operator to avoid burning gas on bigmap insert.
        sp.verify(utils.fa2_get_balance(params.fa2, params.token_id, sp.sender) > 0, message = "NOT_OWNER")

        # Create auction
        self.data.auctions[self.data.auction_id] = sp.record(
            owner=sp.sender,
            token_id=params.token_id,
            start_price=params.start_price,
            end_price=params.end_price,
            start_time=params.start_time,
            end_time=params.end_time,
            fa2=params.fa2
        )

        self.data.auction_id += 1

        # Transfer token (place)
        utils.fa2_transfer(params.fa2, sp.sender, sp.self_address, params.token_id, 1)


    @sp.entry_point(lazify = True)
    def cancel(self, params):
        """Cancel an auction.

        Given it is owned.
        Token is transferred back to auction owner.
        """
        sp.set_type(params, sp.TRecord(
            auction_id = sp.TNat,
            extension = extensionArgType
        ).layout(("auction_id", "extension")))

        self.onlyUnpaused()
        # no need to call self.onlyAdminIfWhitelistEnabled() 

        the_auction = self.data.auctions[params.auction_id]

        sp.verify(the_auction.owner == sp.sender, message = "NOT_OWNER")

        # transfer token back to auction owner.
        utils.fa2_transfer(the_auction.fa2, sp.self_address, the_auction.owner, the_auction.token_id, 1)

        del self.data.auctions[params.auction_id]


    @sp.entry_point(lazify = True)
    def bid(self, params):
        """Bid on an auction.

        The first valid bid (value >= ask_price) gets the token.
        Overpay is transferred back to sender.
        """
        sp.set_type(params, sp.TRecord(
            auction_id = sp.TNat,
            extension = extensionArgType
        ).layout(("auction_id", "extension")))

        self.onlyUnpaused()

        the_auction = sp.local("the_auction", self.data.auctions[params.auction_id])

        # If auction owner is admin, sender needs to be whitelisted, if whitelist is enabled.
        with sp.if_(the_auction.value.owner == self.data.administrator):
            self.onlyWhitelisted()

        # check auction has started
        sp.verify(sp.now >= the_auction.value.start_time, message = "NOT_STARTED")

        # calculate current price and verify amount sent
        ask_price = self.getAuctionPriceInline(the_auction.value)
        #sp.trace(sp.now)
        #sp.trace(ask_price)

        # check if correct value was sent. probably best to send back overpay instead of cancel.
        sp.verify(sp.amount >= ask_price, message = "WRONG_AMOUNT")

        # Collect amounts to send in a map.
        send_map = sp.local("send_map", sp.map(tkey=sp.TAddress, tvalue=sp.TMutez))
        def addToSendMap(address, amount):
            send_map.value[address] = send_map.value.get(address, sp.mutez(0)) + amount

        # Send back overpay, if there was any.
        overpay = sp.amount - ask_price
        addToSendMap(sp.sender, overpay)

        with sp.if_(ask_price != sp.tez(0)):
            token_royalty_info = sp.compute(self.getRoyaltiesForPermittedFA2(the_auction.value.token_id, the_auction.value.fa2))

            # Calculate fees.
            fee = sp.compute(sp.utils.mutez_to_nat(ask_price) * (token_royalty_info.royalties + self.data.fees) / sp.nat(1000))
            royalties = sp.compute(token_royalty_info.royalties * fee / (token_royalty_info.royalties + self.data.fees))

            # If there are any royalties to be paid.
            with sp.if_(royalties > sp.nat(0)):
                # Pay each contributor his relative share.
                with sp.for_("contributor", token_royalty_info.contributors) as contributor:
                    # Calculate amount to be paid from relative share.
                    absolute_amount = sp.compute(sp.utils.nat_to_mutez(royalties * contributor.relative_royalties / 1000))
                    addToSendMap(contributor.address, absolute_amount)

            # TODO: don't localise nat_to_mutez, is probably a cast and free.
            # Send management fees.
            send_mgr_fees = sp.compute(sp.utils.nat_to_mutez(abs(fee - royalties)))
            addToSendMap(self.data.fees_to, send_mgr_fees)

            # Send rest of the value to seller.
            send_seller = sp.compute(ask_price - sp.utils.nat_to_mutez(fee))
            addToSendMap(the_auction.value.owner, send_seller)

        # Transfer.
        with sp.for_("send", send_map.value.items()) as send:
            utils.send_if_value(send.key, send.value)

        # Transfer item to buyer.
        utils.fa2_transfer(the_auction.value.fa2, sp.self_address, sp.sender, the_auction.value.token_id, 1)

        # If it was a whitelist required auction, remove from whitelist.
        with sp.if_(the_auction.value.owner == self.data.administrator):
            self.removeFromWhitelist(sp.sender)

        del self.data.auctions[params.auction_id]


    def getAuctionPriceInline(self, the_auction):
        """Inlined into bid and get_auction_price view"""
        the_auction = sp.set_type_expr(the_auction, TL_Dutch.AUCTION_TYPE)
        
        # Local var for the result.
        result = sp.local("result", sp.tez(0))
        # return start price if it hasn't started
        with sp.if_(sp.now <= the_auction.start_time):
            result.value = the_auction.start_price
        with sp.else_():
            # return end price if it's over
            with sp.if_(sp.now >= the_auction.end_time):
                result.value = the_auction.end_price
            with sp.else_():
                # alright, this works well enough. make 100% sure the math checks out (overflow, abs, etc)
                # probably by validating the input in create. to make sure intervals can't be negative.
                duration = abs(the_auction.end_time - the_auction.start_time) // self.data.granularity
                time_since_start = abs(sp.now - the_auction.start_time) // self.data.granularity
                # NOTE: this can lead to a division by 0. auction duration must be > granularity.
                mutez_per_interval = sp.utils.mutez_to_nat(the_auction.start_price - the_auction.end_price) // duration
                time_deduction = mutez_per_interval * time_since_start

                current_price = the_auction.start_price - sp.utils.nat_to_mutez(time_deduction)

                result.value = current_price
        return result.value


    #
    # Views
    #

    # NOTE: does it make sense to even have get_auction?
    # without being able to get the indices...
    @sp.onchain_view(pure=True)
    def get_auction(self, auction_id):
        """Returns information about an auction."""
        sp.set_type(auction_id, sp.TNat)
        sp.result(self.data.auctions[auction_id])

    @sp.onchain_view(pure=True)
    def get_auction_price(self, auction_id):
        """Returns the current price of an auction."""
        sp.set_type(auction_id, sp.TNat)
        the_auction = sp.local("the_auction", self.data.auctions[auction_id])
        sp.result(self.getAuctionPriceInline(the_auction.value))

    @sp.onchain_view(pure=True)
    def is_secondary_enabled(self):
        """Returns true if secondary is enabled."""
        sp.result(self.data.secondary_enabled)
