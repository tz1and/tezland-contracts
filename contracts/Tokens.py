import smartpy as sp

FA2 = sp.io.import_script_from_url("file:contracts/FA2.py")
admin_mixin = sp.io.import_script_from_url("file:contracts/Administrable.py")

class tz1andPlaces(
    admin_mixin.Administrable,
    FA2.ChangeMetadata,
    FA2.MintNft,
    FA2.OnchainviewCountTokens,
    FA2.Fa2Nft,
):
    """tz1and Places"""

    def __init__(self, metadata, admin):
        FA2.Fa2Nft.__init__(
            self, metadata=metadata,
            name="tz1and Places", description="tz1and Place FA2 Tokens.",
            policy=FA2.PauseTransfer(FA2.OwnerOrOperatorAdhocTransfer())
        )
        admin_mixin.Administrable.__init__(self, admin)

class tz1andItems(
    admin_mixin.Administrable,
    FA2.ChangeMetadata,
    FA2.MintFungible,
    FA2.BurnFungible,
    FA2.Royalties,
    FA2.Fa2Fungible,
):
    """tz1and Items"""

    def __init__(self, metadata, admin):
        FA2.Fa2Fungible.__init__(
            self, metadata=metadata,
            name="tz1and Items", description="tz1and Item FA2 Tokens.",
            policy=FA2.PauseTransfer(FA2.OwnerOrOperatorAdhocTransfer()), has_royalties=True,
            allow_mint_existing=False
        )
        FA2.Royalties.__init__(self)
        admin_mixin.Administrable.__init__(self, admin)

class tz1andDAO(
    admin_mixin.Administrable,
    FA2.ChangeMetadata,
    FA2.MintSingleAsset,
    FA2.Fa2SingleAsset,
):
    """tz1and DAO"""

    def __init__(self, metadata, admin):
        FA2.Fa2SingleAsset.__init__(
            self, metadata=metadata,
            name="tz1and DAO", description="tz1and DAO FA2 Tokens."
        )
        admin_mixin.Administrable.__init__(self, admin)
