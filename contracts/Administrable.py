import smartpy as sp

class Administrable:
    def __init__(self, administrator):
        # TODO: figure out how to init the type in subclasses
        #self.init_type(sp.TRecord(
        #    administrator = sp.TAddress,
        #    proposed_administrator = sp.TOption(sp.TAddress)
        #))
        self.update_initial_storage(
            administrator = administrator,
            proposed_administrator = sp.none
        )

    def isAdministrator(self, address):
        address = sp.set_type_expr(address, sp.TAddress)
        return self.data.administrator == address

    def onlyAdministrator(self):
        sp.verify(self.isAdministrator(sp.sender), 'ONLY_ADMIN')

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.
        """
        sp.set_type(proposed_administrator, sp.TAddress)
        self.onlyAdministrator()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsabilities.
        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(), message="NO_ADMIN_TRANSFER")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(), message="NOT_PROPOSED_ADMIN")

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.onchain_view(pure=True)
    def get_administrator(self):
        """Returns the administrator.
        """
        sp.result(self.data.administrator)
