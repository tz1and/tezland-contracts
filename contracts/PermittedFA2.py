import smartpy as sp

admin_mixin = sp.io.import_script_from_url("file:contracts/Administrable.py")
utils = sp.io.import_script_from_url("file:contracts/Utils.py")
FA2 = sp.io.import_script_from_url("file:contracts/FA2.py")

# TODO: is_fa2_permitted/get_fa2_permitted is probably not needed? maybe for interop...
# TODO: test getRoyaltiesForPermittedFA2

royaltiesKindVariantType = sp.TVariant(
    none = sp.TUnit,
    tz1and = sp.TUnit, # tz1and style royalties, similar to versum. This may be used in Dutch auctions.
    combined = sp.TUnit, # versum style royalties, but combined into one view.
    versum = sp.TUnit, # versum style, 3 separate views.
    other1 = sp.TUnit, # reserved for other marketplaces to be extensible
    other2 = sp.TUnit, # reserved
    other3 = sp.TUnit, # reserved
    other4 = sp.TUnit, # reserved
    other5 = sp.TUnit, # reserved
    other6 = sp.TUnit  # reserved
)

permittedFA2MapValueType = sp.TRecord(
    swap_allowed = sp.TBool, # If the token is allowed to be swapped. This is a little extra.
    royalties_kind = royaltiesKindVariantType, # If the token has royalties and what kind they are.
).layout(("swap_allowed", "royalties_kind"))

#
# Lazy map of permitted FA2 tokens for 'other' type.
class Permitted_fa2_map:
    def make(self, default_permitted):
        return sp.big_map(l = default_permitted, tkey = sp.TAddress, tvalue = permittedFA2MapValueType)
    def add(self, map, fa2, allow_swap):
        map[fa2] = allow_swap
    def remove(self, map, fa2):
        del map[fa2]
    def is_permitted(self, map, fa2):
        return map.contains(fa2)
    def get_props(self, map, fa2):
        return map.get(fa2, message = "TOKEN_NOT_PERMITTED")

class Permitted_fa2_param:
    def get_add_type(self):
        return sp.TRecord(
            fa2 = sp.TAddress,
            props = permittedFA2MapValueType
        ).layout(("fa2", "props"))
    def make_add(self, fa2, props):
        r = sp.record(fa2 = fa2,
            props = props)
        return sp.set_type_expr(r, self.get_add_type())
    def get_remove_type(self):
        return sp.TAddress
    def make_remove(self, fa2):
        return sp.set_type_expr(fa2, self.get_remove_type())


# NOTE:
# When a permitted FA2 is removed, that will break swaps, auctions, etc.
# I think this is desired. But make sure to give a good error message.


class PermittedFA2(admin_mixin.Administrable):
    def __init__(self, administrator, default_permitted = {}):
        self.permitted_fa2_map = Permitted_fa2_map()
        self.permitted_fa2_param = Permitted_fa2_param()
        self.update_initial_storage(
            permitted_fa2 = self.permitted_fa2_map.make(default_permitted),
        )
        admin_mixin.Administrable.__init__(self, administrator = administrator)


    def onlyPermittedFA2(self, fa2):
        """Fails if not permitted"""
        fa2 = sp.set_type_expr(fa2, sp.TAddress)
        sp.verify(self.permitted_fa2_map.is_permitted(self.data.permitted_fa2, fa2),
            message = "TOKEN_NOT_PERMITTED")


    def getPermittedFA2Props(self, fa2):
        """Returns permitted props or fails if not permitted"""
        fa2 = sp.set_type_expr(fa2, sp.TAddress)
        return sp.compute(self.permitted_fa2_map.get_props(self.data.permitted_fa2, fa2))


    def getRoyaltiesForPermittedFA2(self, token_id, auction_fa2):
        """Returns roaylties info for a token of a specified contract."""
        token_id = sp.set_type_expr(token_id, sp.TNat)
        auction_fa2 = sp.set_type_expr(auction_fa2, sp.TAddress)

        # Get permitted FA2 props.
        fa2_props = self.getPermittedFA2Props(auction_fa2)

        # Make sure swapping is allowed.
        # In the dutch auction contract, this should never happen.
        sp.verify(fa2_props.swap_allowed == True, message="SWAP_NOT_ALLOWED")

        token_royalty_info = sp.local("token_royalty_info",
            sp.record(royalties=0, contributors=[]),
            t=FA2.t_royalties)

        with fa2_props.royalties_kind.match_cases() as arg:
            #with arg.match("none"): # none is implied to return default royalty info
            with arg.match("tz1and"):
                token_royalty_info.value = utils.tz1and_items_get_royalties(auction_fa2, token_id)
            with arg.match("combined"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("versum"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other1"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other2"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other3"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other4"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other5"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
            with arg.match("other6"):
                sp.failwith("ROYALTIES_NOT_IMPLEMENTED")
        
        return token_royalty_info.value


    @sp.entry_point
    def set_fa2_permitted(self, params):
        """Call to add/remove fa2 contract from
        token contracts permitted for 'other' type items."""
        sp.set_type(params, sp.TList(sp.TVariant(
            add_permitted = self.permitted_fa2_param.get_add_type(),
            remove_permitted = self.permitted_fa2_param.get_remove_type()
        ).layout(("add_permitted", "remove_permitted"))))

        self.onlyAdministrator()
        
        with sp.for_("update", params) as update:
            with update.match_cases() as arg:
                with arg.match("add_permitted") as upd:
                    self.permitted_fa2_map.add(self.data.permitted_fa2, upd.fa2, upd.props)
                with arg.match("remove_permitted") as upd:
                    self.permitted_fa2_map.remove(self.data.permitted_fa2, upd)


    @sp.onchain_view(pure=True)
    def is_fa2_permitted(self, fa2):
        """Returns True if an fa2 is permitted."""
        sp.set_type(fa2, sp.TAddress)
        sp.result(self.permitted_fa2_map.is_permitted(self.data.permitted_fa2, fa2))


    @sp.onchain_view(pure=True)
    def get_fa2_permitted(self, fa2):
        """Returns permitted fa2 props."""
        sp.set_type(fa2, sp.TAddress)
        sp.result(self.permitted_fa2_map.get_props(self.data.permitted_fa2, fa2))

