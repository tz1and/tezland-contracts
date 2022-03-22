import smartpy as sp

admin_mixin = sp.io.import_script_from_url("file:contracts/Administrable.py")


class Pausable(admin_mixin.Administrable):
    def __init__(self, administrator):
        self.update_initial_storage(
            paused = False
        )
        admin_mixin.Administrable.__init__(self, administrator = administrator)

    def isPaused(self):
        return self.data.paused

    def onlyUnpaused(self):
        sp.verify(self.isPaused() == False, 'ONLY_UNPAUSED')

    def onlyPaused(self):
        sp.verify(self.isPaused() == True, 'ONLY_PAUSED')

    @sp.entry_point
    def set_paused(self, new_paused):
        self.onlyAdministrator()
        self.data.paused = new_paused

    @sp.onchain_view(pure=True)
    def is_paused(self):
        sp.result(self.isPaused())