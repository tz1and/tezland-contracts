import smartpy as sp

admin_mixin = sp.io.import_script_from_url("file:contracts/Administrable.py")


class Moderation(admin_mixin.Administrable):
    """Mixin to add moderation_contract address to a contract's storage.
    
    Can then later be used through add moderation functions through upgrades."""
    def __init__(self, administrator):
        self.update_initial_storage(
            moderation_contract = administrator # points to administrator by default
        )
        admin_mixin.Administrable.__init__(self, administrator = administrator)

    @sp.entry_point
    def set_moderation_contract(self, moderation_contract):
        """Set moderation contract.
        """
        sp.set_type(moderation_contract, sp.TAddress)
        self.onlyAdministrator()
        self.data.moderation_contract = moderation_contract
