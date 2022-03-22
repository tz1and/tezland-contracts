import smartpy as sp

pause_mixin = sp.io.import_script_from_url("file:contracts/Pausable.py")
mod_mixin = sp.io.import_script_from_url("file:contracts/Moderation.py")
fa2_admin = sp.io.import_script_from_url("file:contracts/FA2_Administration.py")
upgradeable_mixin = sp.io.import_script_from_url("file:contracts/Upgradeable.py")
utils = sp.io.import_script_from_url("file:contracts/Utils.py")
FA2 = sp.io.import_script_from_url("file:contracts/FA2.py")


#
# Minter contract.
# NOTE: should be pausable for code updates.
class TL_Minter(
    pause_mixin.Pausable,
    mod_mixin.Moderation,
    fa2_admin.FA2_Administration,
    upgradeable_mixin.Upgradeable,
    sp.Contract):
    def __init__(self, administrator, items_contract, places_contract, metadata, exception_optimization_level="default-line"):
        self.add_flag("exceptions", exception_optimization_level)
        self.add_flag("erase-comments")
        
        self.init_storage(
            items_contract = items_contract,
            places_contract = places_contract,
            metadata = metadata,
            )
        pause_mixin.Pausable.__init__(self, administrator = administrator)
        mod_mixin.Moderation.__init__(self, administrator = administrator)
        fa2_admin.FA2_Administration.__init__(self, administrator = administrator)
        upgradeable_mixin.Upgradeable.__init__(self, administrator = administrator,
            entrypoints = ['mint_Item', 'mint_Place'])
        self.generate_contract_metadata()

    def generate_contract_metadata(self):
        """Generate a metadata json file with all the contract's offchain views
        and standard TZIP-12 and TZIP-016 key/values."""
        metadata_base = {
            "name": 'tz1and Minter',
            "description": 'tz1and Items and Places minter',
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
    # Manager-only entry points
    #
    @sp.entry_point
    def pause_all_fa2(self, new_paused):
        """The admin can pause/unpause items and places contracts."""
        sp.set_type(new_paused, sp.TBool)
        self.onlyAdministrator()

        with sp.for_("fa2", [self.data.items_contract, self.data.places_contract]) as fa2:
            # call items contract
            set_paused_handle = sp.contract(sp.TBool, fa2, 
                entry_point = "set_pause").open_some()
                
            sp.transfer(new_paused, sp.mutez(0), set_paused_handle)

    @sp.entry_point
    def clear_adhoc_operators_all_fa2(self):
        """The admin can clear adhoc ops for items and places contracts."""
        self.onlyAdministrator()
    
        with sp.for_("fa2", [self.data.items_contract, self.data.places_contract]) as fa2:
            # call items contract
            set_paused_handle = sp.contract(FA2.t_adhoc_operator_params, fa2, 
                entry_point = "update_adhoc_operators").open_some()
                
            sp.transfer(sp.variant("clear_adhoc_operators", sp.unit),
                sp.mutez(0), set_paused_handle)

    @sp.entry_point(lazify = True)
    def mint_Place(self, params):
        sp.set_type(params, FA2.t_mint_nft_batch)

        self.onlyAdministrator()
        self.onlyUnpaused()

        utils.fa2_nft_mint(
            params,
            self.data.places_contract
        )

    #
    # Public entry points
    #
    @sp.entry_point(lazify = True)
    def mint_Item(self, params):
        sp.set_type(params, sp.TRecord(
            to_ = sp.TAddress,
            amount = sp.TNat,
            royalties = sp.TNat,
            contributors = FA2.t_contributor_list,
            metadata = sp.TBytes
        ).layout(("to_", ("amount", ("royalties", ("contributors", "metadata"))))))

        self.onlyUnpaused()
        
        sp.verify((params.amount > 0) & (params.amount <= 10000) & ((params.royalties >= 0) & (params.royalties <= 250)),
            message = "PARAM_ERROR")

        utils.fa2_fungible_royalties_mint(
            [sp.record(
                to_=params.to_,
                amount=params.amount,
                token=sp.variant("new", sp.record(
                    metadata={ '' : params.metadata },
                    royalties=sp.record(
                        royalties=params.royalties,
                        contributors=params.contributors)
                    )
                )
            )],
            self.data.items_contract
        )
