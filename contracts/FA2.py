"""
FA2 standard: https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/tzip-12.md. <br/>
Documentation: [FA2 lib](/docs/guides/FA/FA2_lib).

Multiple mixins and several standard [policies](https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/permissions-policy.md#operator-permission-behavior) are supported.
"""

import smartpy as sp
import types


#########
# Types #
#########


t_operator_permission = sp.TRecord(
    owner=sp.TAddress, operator=sp.TAddress, token_id=sp.TNat
).layout(("owner", ("operator", "token_id")))

t_update_operators_params = sp.TList(
    sp.TVariant(
        add_operator=t_operator_permission, remove_operator=t_operator_permission
    )
)

t_transfer_tx = sp.TRecord(
    to_=sp.TAddress,
    token_id=sp.TNat,
    amount=sp.TNat,
).layout(("to_", ("token_id", "amount")))

t_transfer_batch = sp.TRecord(
    from_=sp.TAddress,
    txs=sp.TList(t_transfer_tx),
).layout(("from_", "txs"))

t_transfer_params = sp.TList(t_transfer_batch)

t_balance_of_request = sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
    ("owner", "token_id")
)

t_balance_of_response = sp.TRecord(
    request=t_balance_of_request, balance=sp.TNat
).layout(("request", "balance"))

t_balance_of_params = sp.TRecord(
    callback=sp.TContract(sp.TList(t_balance_of_response)),
    requests=sp.TList(t_balance_of_request),
).layout(("requests", "callback"))

# mint types

t_mint_nft_batch = sp.TList(sp.TRecord(
    to_=sp.TAddress,
    metadata=sp.TMap(sp.TString, sp.TBytes)
).layout(("to_", "metadata")))

t_mint_fungible_batch = sp.TList(sp.TRecord(
    to_=sp.TAddress,
    amount=sp.TNat,
    token=sp.TVariant(
        new=sp.TRecord(
            metadata=sp.TMap(sp.TString, sp.TBytes)
        ),
        existing=sp.TNat
    ).layout(("new", "existing"))
).layout(("to_", ("amount", "token"))))

# burn types

t_burn_batch = sp.TList(sp.TRecord(
    from_=sp.TAddress,
    amount=sp.TNat,
    token_id=sp.TNat
).layout(("from_", ("amount", "token_id"))))

# distribute types

t_distribute_batch = sp.TList(sp.TRecord(
    to_=sp.TAddress, amount=sp.TNat
).layout(("to_", "amount")))

# adhoc operator types

t_adhoc_operator_permission = sp.TRecord(
    operator=sp.TAddress, token_id=sp.TNat
).layout(("operator", "token_id"))

t_adhoc_operator_params = sp.TVariant(
    add_adhoc_operators = sp.TList(t_adhoc_operator_permission),
    clear_adhoc_operators = sp.TUnit
).layout(("add_adhoc_operators", "clear_adhoc_operators"))

# royalties

t_contributor_list = sp.TList(
    # The relative royalties, per contributor, in permille.
    # must add up to 1000. And the role.
    sp.TRecord(
        address=sp.TAddress,
        relative_royalties=sp.TNat,
        role=sp.TVariant(
            minter=sp.TUnit,
            creator=sp.TUnit,
            donation=sp.TUnit,
            custom=sp.TString
        ).layout(("minter", ("creator", ("donation", "custom"))))
    ).layout(("address", ("relative_royalties", "role"))))

t_royalties = sp.TRecord(
    # The absolute royalties in permille.
    royalties=sp.TNat,
    # The minter address
    contributors=t_contributor_list
).layout(("royalties", "contributors"))

# mint with royalties

t_mint_nft_royalties_batch = sp.TList(sp.TRecord(
    to_=sp.TAddress,
    metadata=sp.TMap(sp.TString, sp.TBytes),
    royalties=t_royalties
).layout(("to_", ("metadata", "royalties"))))

t_mint_fungible_royalties_batch = sp.TList(sp.TRecord(
    to_=sp.TAddress,
    amount=sp.TNat,
    token=sp.TVariant(
        new=sp.TRecord(
            metadata=sp.TMap(sp.TString, sp.TBytes),
            royalties=t_royalties
        ).layout(("metadata", "royalties")),
        existing=sp.TNat
    ).layout(("new", "existing"))
).layout(("to_", ("amount", "token"))))

# token_extra

t_token_extra_royalties_supply = sp.TRecord(
    supply=sp.TNat,
    royalty_info=t_royalties
).layout(("supply", "royalty_info"))

t_token_extra_royalties = sp.TRecord(
    royalty_info=t_royalties
)

t_token_extra_supply = sp.TRecord(
    supply=sp.TNat
)


############
# Policies #
############


class NoTransfer:
    """(Transfer Policy) No transfer allowed."""

    def init_policy(self, contract):
        self.name = "no-transfer"
        self.supports_transfer = False
        self.supports_operator = False

    def check_tx_transfer_permissions(self, contract, from_, to_, token_id):
        pass

    def check_operator_update_permissions(self, contract, operator_permission):
        pass

    def is_operator(self, contract, operator_permission):
        return False


class OwnerTransfer:
    """(Transfer Policy) Only owner can transfer tokens, no operator
    allowed."""

    def init_policy(self, contract):
        self.name = "owner-transfer"
        self.supports_transfer = True
        self.supports_operator = False

    def check_tx_transfer_permissions(self, contract, from_, to_, token_id):
        sp.verify(sp.sender == from_, "FA2_NOT_OWNER")

    def check_operator_update_permissions(self, contract, operator_permission):
        pass

    def is_operator(self, contract, operator_permission):
        return False


class OwnerOrOperatorTransfer:
    """(Transfer Policy) Only owner and operators can transfer tokens.

    Operators allowed.
    """

    def init_policy(self, contract):
        self.name = "owner-or-operator-transfer"
        self.supports_transfer = True
        self.supports_operator = True
        contract.update_initial_storage(
            operators=sp.big_map(tkey=t_operator_permission, tvalue=sp.TUnit)
        )

    def check_tx_transfer_permissions(self, contract, from_, to_, token_id):
        sp.verify(
            (sp.sender == from_)
            | contract.data.operators.contains(
                sp.record(owner=from_, operator=sp.sender, token_id=token_id)
            ),
            message="FA2_NOT_OPERATOR",
        )

    def check_operator_update_permissions(self, contract, operator_permission):
        sp.verify(operator_permission.owner == sp.sender, "FA2_NOT_OWNER")

    def is_operator(self, contract, operator_permission):
        return contract.data.operators.contains(operator_permission)


class OwnerOrOperatorAdhocTransfer:
    """(Transfer Policy) Only owner and operators can transfer tokens.

    Adds a `update_adhoc_operators` entrypoint. Checks both operators
    and adhoc operators.

    Provides adhoc, temporary operators. Cheap and storage efficient.
    They are supposed to apply only to the current operation group.
    They are only valid in the current block level.

    For long-lasting operators, use standard operators.

    You've seen it here first :)
    """

    def init_policy(self, contract):
        self.name = "owner-or-operator-transfer"
        self.supports_transfer = True
        self.supports_operator = True
        contract.update_initial_storage(
            operators=sp.big_map(tkey=t_operator_permission, tvalue=sp.TUnit),
            adhoc_operators = sp.set(t = sp.TBytes)
        )

        # Add make_adhoc_operator_key to contract.
        def make_adhoc_operator_key(self, owner, operator, token_id):
            t_adhoc_operator_record = sp.TRecord(
                owner=sp.TAddress,
                operator=sp.TAddress,
                token_id=sp.TNat,
                level=sp.TNat
            ).layout(("owner", ("operator", ("token_id", "level"))))

            return sp.sha3(sp.pack(sp.set_type_expr(sp.record(
                owner=owner,
                operator=operator,
                token_id=token_id,
                level=sp.level
            ), t_adhoc_operator_record)))

        contract.make_adhoc_operator_key = types.MethodType(make_adhoc_operator_key, contract)

        # Add update_adhoc_operators entrypoint to contract.
        def update_adhoc_operators(self, params):
            # Supports add_adhoc_operators, and clear_adhoc_operators.
            sp.set_type(params, t_adhoc_operator_params)

            with params.match_cases() as arg:
                with arg.match("add_adhoc_operators") as updates:
                    # Check adhoc operator limit. To prevent potential gaslock.
                    sp.verify(sp.len(updates) <= 100, "ADHOC_OPERATOR_LIMIT")

                    # Add new adhoc operators to temp set.
                    additions = sp.local("additions", sp.set(t=sp.TBytes))
                    with sp.for_("upd", updates) as upd:
                        additions.value.add(self.make_adhoc_operator_key(
                            sp.sender, # Sender must be the owner
                            upd.operator,
                            upd.token_id))

                    # Remove as many adhoc operators as we added.
                    # We do this to make sure the storage diffs aren't lost
                    # on minting tokens. And to make sure the set doesn't grow larger
                    # than the adhoc operator limit.
                    num_additions = sp.compute(sp.len(additions.value))
                    counter = sp.local("counter", sp.nat(0))
                    with sp.for_("op", self.data.adhoc_operators.elements()) as op:
                        with sp.if_(counter.value < num_additions):
                            self.data.adhoc_operators.remove(op)
                            counter.value += 1

                    # Add adhoc ops from temp set.
                    with sp.for_("add", additions.value.elements()) as add:
                        self.data.adhoc_operators.add(add)

                with arg.match("clear_adhoc_operators"):
                    # Only admin is allowed to do this.
                    # Otherwise someone could sneakily get storage diffs at
                    # the cost of everyone else.
                    sp.verify(self.isAdministrator(sp.sender), "FA2_NOT_ADMIN")
                    # Clear adhoc operators.
                    self.data.adhoc_operators = sp.set(t = sp.TBytes)

        contract.update_adhoc_operators = sp.entry_point(update_adhoc_operators)

    def check_tx_transfer_permissions(self, contract, from_, to_, token_id):
        sp.verify(
            (sp.sender == from_)
            | contract.data.adhoc_operators.contains(
                contract.make_adhoc_operator_key(from_, sp.sender, token_id)
            )
            | contract.data.operators.contains(
                sp.record(owner=from_, operator=sp.sender, token_id=token_id)
            ),
            message="FA2_NOT_OPERATOR",
        )

    def check_operator_update_permissions(self, contract, operator_permission):
        sp.verify(operator_permission.owner == sp.sender, "FA2_NOT_OWNER")

    def is_operator(self, contract, operator_permission):
        adhoc_key = contract.make_adhoc_operator_key(operator_permission.owner, operator_permission.operator, operator_permission.token_id)
        return contract.data.adhoc_operators.contains(adhoc_key) | contract.data.operators.contains(operator_permission)


class PauseTransfer:
    """(Transfer Policy) Decorate any policy to add a pause mechanism.

    Adds a `set_pause` entrypoint. Checks that contract.data.paused is
    `False` before accepting transfers and operator updates.

    Needs the `Administrable` mixin in order to work.
    """

    def __init__(self, policy=None):
        if policy is None:
            self.policy = OwnerOrOperatorTransfer()
        else:
            self.policy = policy

    def init_policy(self, contract):
        self.policy.init_policy(contract)
        self.name = "pauseable-" + self.policy.name
        self.supports_transfer = self.policy.supports_transfer
        self.supports_operator = self.policy.supports_operator
        contract.update_initial_storage(paused=False)

        # Add a set_pause entrypoint
        def set_pause(self, params):
            sp.set_type(params, sp.TBool)
            sp.verify(self.isAdministrator(sp.sender), "FA2_NOT_ADMIN")
            self.data.paused = params

        contract.set_pause = sp.entry_point(set_pause)

    def check_tx_transfer_permissions(self, contract, from_, to_, token_id):
        sp.verify(~contract.data.paused, message=sp.pair("FA2_TX_DENIED", "FA2_PAUSED"))
        self.policy.check_tx_transfer_permissions(contract, from_, to_, token_id)

    def check_operator_update_permissions(self, contract, operator_param):
        sp.verify(
            ~contract.data.paused,
            message=sp.pair("FA2_OPERATORS_UNSUPPORTED", "FA2_PAUSED"),
        )
        self.policy.check_operator_update_permissions(contract, operator_param)

    def is_operator(self, contract, operator_param):
        return self.policy.is_operator(contract, operator_param)


##################
# Onchain views #
##################


class OnchainViewsNft:
    """(Mixin) All standard offchain views for NFTs except the optional
    `token_metadata`."""

    @sp.onchain_view(pure=True)
    def all_tokens(self):
        """Return the list of all the token IDs known to the contract."""
        sp.result(sp.range(0, self.data.last_token_id))

    @sp.onchain_view(pure=True)
    def get_balance(self, params):
        """Return the balance of an address for the specified `token_id`."""
        sp.set_type(
            params,
            sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")
            ),
        )
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        sp.result(
            sp.eif(
                self.data.ledger[params.token_id] == params.owner, sp.nat(1), sp.nat(0)
            )
        )

    @sp.onchain_view(pure=True)
    def total_supply(self, params):
        """Return the total number of tokens for the given `token_id`."""
        sp.set_type(params, sp.TRecord(token_id=sp.TNat))
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        sp.result(sp.nat(1))

    @sp.onchain_view(pure=True)
    def is_operator(self, params):
        """Return whether `operator` is allowed to transfer `token_id` tokens
        owned by `owner`."""
        sp.set_type(params, t_operator_permission)
        sp.result(self.policy.is_operator(self, params))


class OnchainViewsFungible:
    """(Mixin) All standard offchain views for Fungible except the optional
    `token_metadata`."""

    @sp.onchain_view(pure=True)
    def all_tokens(self):
        """Return the list of all the token IDs known to the contract."""
        sp.result(sp.range(0, self.data.last_token_id))

    @sp.onchain_view(pure=True)
    def get_balance(self, params):
        """Return the balance of an address for the specified `token_id`."""
        sp.set_type(
            params,
            sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")
            ),
        )
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        sp.result(self.data.ledger.get((params.owner, params.token_id), sp.nat(0)))

    @sp.onchain_view(pure=True)
    def total_supply(self, params):
        """Return the total number of tokens for the given `token_id`."""
        sp.set_type(params, sp.TRecord(token_id=sp.TNat))
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        with sp.if_(self.data.token_extra.contains(params.token_id)):
            sp.result(self.data.token_extra[params.token_id].supply)
        with sp.else_():
            sp.result(sp.nat(0))

    @sp.onchain_view(pure=True)
    def is_operator(self, params):
        """Return whether `operator` is allowed to transfer `token_id` tokens
        owned by `owner`."""
        sp.set_type(params, t_operator_permission)
        sp.result(self.policy.is_operator(self, params))


class OnchainViewsSingleAsset:
    """(Mixin) All standard offchain views for single asset except the optional
    `token_metadata`."""

    @sp.onchain_view(pure=True)
    def all_tokens(self):
        """Return the list of all the token IDs known to the contract."""
        sp.result([sp.nat(0)])

    @sp.onchain_view(pure=True)
    def get_balance(self, params):
        """Return the balance of an address for the specified `token_id`."""
        sp.set_type(
            params,
            sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")
            ),
        )
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        sp.result(self.data.ledger.get(params.owner, sp.nat(0)))

    @sp.onchain_view(pure=True)
    def total_supply(self, params):
        """Return the total number of tokens for the given `token_id`."""
        sp.set_type(params, sp.TRecord(token_id=sp.TNat))
        sp.verify(self.is_defined(params.token_id), "FA2_TOKEN_UNDEFINED")
        sp.result(self.data.supply)

    @sp.onchain_view(pure=True)
    def is_operator(self, params):
        """Return whether `operator` is allowed to transfer `token_id` tokens
        owned by `owner`."""
        sp.set_type(params, t_operator_permission)
        sp.result(self.policy.is_operator(self, params))


##########
# Common #
##########


class Common(sp.Contract):
    """Common logic between Fa2Nft, Fa2Fungible and Fa2SingleAsset."""

    def __init__(self, name, description, policy=None, metadata_base=None, token_metadata={}):
        self.add_flag("exceptions", "default-line")
        self.add_flag("erase-comments")

        if policy is None:
            self.policy = OwnerOrOperatorTransfer()
        else:
            self.policy = policy
        self.update_initial_storage(
            token_metadata=sp.big_map(
                token_metadata,
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    token_id=sp.TNat, token_info=sp.TMap(sp.TString, sp.TBytes)
                ).layout(("token_id", "token_info")),
            )
        )
        self.policy.init_policy(self)
        self.generate_contract_metadata(name, description, "metadata_base", metadata_base)

    def is_defined(self, token_id):
        return self.data.token_metadata.contains(token_id)

    def generate_contract_metadata(self, name, description, filename, metadata_base=None):
        """Generate a metadata json file with all the contract's offchain views
        and standard TZIP-126 and TZIP-016 key/values."""
        if metadata_base is None:
            metadata_base = {
                "name": name,
                "version": "1.0.0",
                "description": (
                    description + "\n\nBased on the SmartPy FA2 implementation."
                ),
                "interfaces": ["TZIP-012", "TZIP-016"],
                "authors": [
                    "852Kerfunkle <https://github.com/852Kerfunkle>",
                    "SmartPy <https://smartpy.io/#contact>"
                ],
                "homepage": "https://www.tz1and.com",
                "source": {
                    "tools": ["SmartPy"],
                    "location": "https://github.com/tz1and",
                },
                "license": { "name": "MIT" },
                "permissions": {"receiver": "owner-no-hook", "sender": "owner-no-hook"},
            }
        offchain_views = []
        for f in dir(self):
            attr = getattr(self, f)
            if isinstance(attr, sp.OnOffchainView):
                # Change: include onchain views as tip 16 offchain views
                offchain_views.append(attr)
        metadata_base["views"] = offchain_views
        metadata_base["permissions"]["operator"] = self.policy.name
        self.init_metadata(filename, metadata_base)

    @sp.entry_point
    def update_operators(self, batch):
        """Accept a list of variants to add or remove operators who can perform
        transfers on behalf of the owner."""
        sp.set_type(batch, t_update_operators_params)
        if self.policy.supports_operator:
            with sp.for_("action", batch) as action:
                with action.match_cases() as arg:
                    with arg.match("add_operator") as operator:
                        self.policy.check_operator_update_permissions(self, operator)
                        self.data.operators[operator] = sp.unit
                    with arg.match("remove_operator") as operator:
                        self.policy.check_operator_update_permissions(self, operator)
                        del self.data.operators[operator]
        else:
            sp.failwith("FA2_OPERATORS_UNSUPPORTED")


################
# Base classes #
################


class Fa2Nft(OnchainViewsNft, Common):
    """Base class for a FA2 NFT contract.

    Respects the FA2 standard.
    """

    def __init__(
        self, metadata, name="FA2", description="A NFT FA2 implementation.",
        token_metadata=[], ledger={}, policy=None, metadata_base=None, has_royalties=False
    ):
        metadata = sp.set_type_expr(metadata, sp.TBigMap(sp.TString, sp.TBytes))
        self.ledger_type = "NFT"
        self.has_royalties = has_royalties
        ledger, token_extra, token_metadata = self.initial_mint(token_metadata, ledger, has_royalties)
        self.init(
            ledger=sp.big_map(ledger, tkey=sp.TNat, tvalue=sp.TAddress),
            metadata=metadata,
            last_token_id=sp.nat(len(token_metadata))
        )
        if has_royalties:
            self.update_initial_storage(
                token_extra=sp.big_map(token_extra, tkey=sp.TNat, tvalue=t_token_extra_royalties)
            )
        Common.__init__(
            self,
            name,
            description,
            policy=policy,
            metadata_base=metadata_base,
            token_metadata=token_metadata,
        )

    def initial_mint(self, token_metadata=[], ledger={}, has_royalties=False):
        """Perform a mint before the origination.

        Returns `ledger`, `token_extra` and `token_metadata`.
        """
        token_metadata_dict = {}
        token_extra_dict = {}
        for token_id, metadata in enumerate(token_metadata):
            token_metadata_dict[token_id] = sp.record(
                token_id=token_id, token_info=metadata
            )
            token_extra_dict[token_id] = sp.record(
                royalty_info=sp.record(
                    royalties=0, contributors=[]
                )
            )
        for token_id, address in ledger.items():
            if token_id not in token_metadata_dict:
                raise Exception(
                    "Ledger contains token_id with no corresponding metadata"
                )
        return (ledger, token_extra_dict, token_metadata_dict)

    def balance_of_(self, requests):
        """Logic of the balance_of entrypoint."""
        sp.set_type(requests, sp.TList(t_balance_of_request))

        def f_process_request(req):
            sp.verify(self.is_defined(req.token_id), "FA2_TOKEN_UNDEFINED")
            sp.result(
                sp.record(
                    request=sp.record(owner=req.owner, token_id=req.token_id),
                    balance=sp.eif(self.data.ledger[req.token_id] == req.owner, 1, 0),
                )
            )

        return requests.map(f_process_request)

    @sp.entry_point
    def balance_of(self, params):
        """Send the balance of multiple account / token pairs to a callback
        address."""
        sp.set_type(params, t_balance_of_params)
        sp.transfer(self.balance_of_(params.requests), sp.mutez(0), params.callback)

    @sp.entry_point
    def transfer(self, batch):
        """Accept a list of transfer operations between a source and multiple
        destinations."""
        sp.set_type(batch, t_transfer_params)
        if self.policy.supports_transfer:
            with sp.for_("transfer", batch) as transfer:
                with sp.for_("tx", transfer.txs) as tx:
                    # The ordering of sp.verify is important: 1) token_undefined, 2) transfer permission 3) balance
                    sp.verify(self.is_defined(tx.token_id), "FA2_TOKEN_UNDEFINED")
                    self.policy.check_tx_transfer_permissions(
                        self, transfer.from_, tx.to_, tx.token_id
                    )
                    with sp.if_(tx.amount > 0):
                        sp.verify(
                            (tx.amount == 1)
                            & (self.data.ledger[tx.token_id] == transfer.from_),
                            message="FA2_INSUFFICIENT_BALANCE",
                        )
                        # Do the transfer
                        self.data.ledger[tx.token_id] = tx.to_
        else:
            sp.failwith("FA2_TX_DENIED")


# TODO: test allow_mint_existing=False
class Fa2Fungible(OnchainViewsFungible, Common):
    """Base class for a FA2 fungible contract.

    Respects the FA2 standard.
    """

    def __init__(
        self, metadata, name="FA2", description="A Fungible FA2 implementation.",
        token_metadata=[], ledger={}, policy=None, metadata_base=None, has_royalties=False, allow_mint_existing=True
    ):
        metadata = sp.set_type_expr(metadata, sp.TBigMap(sp.TString, sp.TBytes))
        self.ledger_type = "Fungible"
        self.has_royalties = has_royalties
        self.allow_mint_existing = allow_mint_existing
        ledger, token_extra, token_metadata = self.initial_mint(token_metadata, ledger, has_royalties)
        self.init(
            ledger=sp.big_map(
                ledger, tkey=sp.TPair(sp.TAddress, sp.TNat), tvalue=sp.TNat
            ),
            metadata=metadata,
            last_token_id=sp.nat(len(token_metadata))
        )
        if has_royalties:
            self.update_initial_storage(
                token_extra=sp.big_map(token_extra, tkey=sp.TNat, tvalue=t_token_extra_royalties_supply)
            )
        else:
            self.update_initial_storage(
                token_extra=sp.big_map(token_extra, tkey=sp.TNat, tvalue=t_token_extra_supply)
            )
        Common.__init__(
            self,
            name,
            description,
            policy=policy,
            metadata_base=metadata_base,
            token_metadata=token_metadata,
        )

    def initial_mint(self, token_metadata=[], ledger={}, has_royalties=False):
        """Perform a mint before the origination.

        Returns `ledger`, `token_extra` and `token_metadata`.
        """
        token_metadata_dict = {}
        token_extra_dict = {}
        for token_id, metadata in enumerate(token_metadata):
            metadata = sp.record(token_id=token_id, token_info=metadata)
            token_metadata_dict[token_id] = metadata
            # Token that are in token_metadata and not in ledger exist with supply = 0
            if has_royalties:
                token_extra_dict[token_id] = sp.record(
                    supply=sp.nat(0),
                    royalty_info=sp.record(
                        royalties=0, contributors=[]
                    )
                )
            else:
                token_extra_dict[token_id] = sp.record(supply=sp.nat(0))
        for (address, token_id), amount in ledger.items():
            if token_id not in token_metadata_dict:
                raise Exception("Ledger contains a token_id with no metadata")
            token_extra_dict[token_id].supply += amount
        return (ledger, token_extra_dict, token_metadata_dict)

    def balance_of_(self, requests):
        """Logic of the balance_of entrypoint."""
        sp.set_type(requests, sp.TList(t_balance_of_request))

        def f_process_request(req):
            sp.verify(self.is_defined(req.token_id), "FA2_TOKEN_UNDEFINED")
            sp.result(
                sp.record(
                    request=sp.record(owner=req.owner, token_id=req.token_id),
                    balance=self.data.ledger.get((req.owner, req.token_id), 0),
                )
            )

        return requests.map(f_process_request)

    @sp.entry_point
    def balance_of(self, params):
        """Send the balance of multiple account / token pairs to a callback
        address."""
        sp.set_type(params, t_balance_of_params)
        sp.transfer(self.balance_of_(params.requests), sp.mutez(0), params.callback)

    @sp.entry_point
    def transfer(self, batch):
        """Accept a list of transfer operations between a source and multiple
        destinations."""
        sp.set_type(batch, t_transfer_params)
        if self.policy.supports_transfer:
            with sp.for_("transfer", batch) as transfer:
                with sp.for_("tx", transfer.txs) as tx:
                    # The ordering of sp.verify is important: 1) token_undefined, 2) transfer permission 3) balance
                    sp.verify(self.is_defined(tx.token_id), "FA2_TOKEN_UNDEFINED")
                    self.policy.check_tx_transfer_permissions(
                        self, transfer.from_, tx.to_, tx.token_id
                    )
                    from_ = (transfer.from_, tx.token_id)
                    # Transfer from.
                    from_balance = sp.compute(sp.as_nat(
                        self.data.ledger.get(from_, 0) - tx.amount,
                        message="FA2_INSUFFICIENT_BALANCE",
                    ))
                    with sp.if_(from_balance == 0):
                        del self.data.ledger[from_]
                    with sp.else_():
                        self.data.ledger[from_] = from_balance

                    # Do the transfer
                    to_ = (tx.to_, tx.token_id)
                    self.data.ledger[to_] = self.data.ledger.get(to_, 0) + tx.amount
        else:
            sp.failwith("FA2_TX_DENIED")

class Fa2SingleAsset(OnchainViewsSingleAsset, Common):
    """Base class for a FA2 single asset contract.

    Respects the FA2 standard.
    """

    def __init__(
        self, metadata, name="FA2", description="A Single Asset FA2 implementation.",
        token_metadata=[], ledger={}, policy=None, metadata_base=None
    ):
        metadata = sp.set_type_expr(metadata, sp.TBigMap(sp.TString, sp.TBytes))
        self.ledger_type = "SingleAsset"
        ledger, supply, token_metadata = self.initial_mint(token_metadata, ledger)
        self.init(
            ledger=sp.big_map(
                ledger, tkey=sp.TAddress, tvalue=sp.TNat
            ),
            metadata=metadata,
            last_token_id=sp.nat(len(token_metadata)),
            supply=supply,
        )
        Common.__init__(
            self,
            name,
            description,
            policy=policy,
            metadata_base=metadata_base,
            token_metadata=token_metadata,
        )

    def initial_mint(self, token_metadata=[], ledger={}):
        """Perform a mint before the origination.

        Returns `ledger`, `supply` and `token_metadata`.
        """
        if len(token_metadata) > 1:
            raise Exception("Single asset can only contain one token")
        token_metadata_dict = {}
        supply = sp.nat(0)
        for token_id, metadata in enumerate(token_metadata):
            metadata = sp.record(token_id=token_id, token_info=metadata)
            token_metadata_dict[token_id] = metadata
        for address, amount in ledger.items():
            if token_id not in token_metadata_dict:
                raise Exception("Ledger contains a token_id with no metadata")
            supply += amount
        return (ledger, supply, token_metadata_dict)

    def balance_of_(self, requests):
        """Logic of the balance_of entrypoint."""
        sp.set_type(requests, sp.TList(t_balance_of_request))

        def f_process_request(req):
            sp.verify(self.is_defined(req.token_id), "FA2_TOKEN_UNDEFINED")
            sp.result(
                sp.record(
                    request=sp.record(owner=req.owner, token_id=req.token_id),
                    balance=self.data.ledger.get(req.owner, 0),
                )
            )

        return requests.map(f_process_request)

    @sp.entry_point
    def balance_of(self, params):
        """Send the balance of multiple account / token pairs to a callback
        address."""
        sp.set_type(params, t_balance_of_params)
        sp.transfer(self.balance_of_(params.requests), sp.mutez(0), params.callback)

    # Overload is_defined to make sure token_id is always 0
    def is_defined(self, token_id):
        return token_id == 0

    @sp.entry_point
    def transfer(self, batch):
        """Accept a list of transfer operations between a source and multiple
        destinations."""
        sp.set_type(batch, t_transfer_params)
        if self.policy.supports_transfer:
            with sp.for_("transfer", batch) as transfer:
                with sp.for_("tx", transfer.txs) as tx:
                    # The ordering of sp.verify is important: 1) token_undefined, 2) transfer permission 3) balance
                    sp.verify(self.is_defined(tx.token_id), "FA2_TOKEN_UNDEFINED")
                    self.policy.check_tx_transfer_permissions(
                        self, transfer.from_, tx.to_, tx.token_id
                    )
                    from_ = transfer.from_
                    # Transfer from.
                    from_balance = sp.compute(sp.as_nat(
                        self.data.ledger.get(from_, 0) - tx.amount,
                        message="FA2_INSUFFICIENT_BALANCE",
                    ))
                    with sp.if_(from_balance == 0):
                        del self.data.ledger[from_]
                    with sp.else_():
                        self.data.ledger[from_] = from_balance

                    # Do the transfer
                    to_ = tx.to_
                    self.data.ledger[to_] = self.data.ledger.get(to_, 0) + tx.amount
        else:
            sp.failwith("FA2_TX_DENIED")


##########
# Mixins #
##########


class ChangeMetadata:
    """(Mixin) Provide an entrypoint to change contract metadata.

    Requires the `Administrable` mixin.
    """

    @sp.entry_point
    def set_metadata(self, metadata):
        """(Admin only) Set the contract metadata."""
        sp.set_type(metadata, sp.TBigMap(sp.TString, sp.TBytes))
        sp.verify(self.isAdministrator(sp.sender), message="FA2_NOT_ADMIN")
        self.data.metadata = metadata


class WithdrawMutez:
    """(Mixin) Provide an entrypoint to withdraw mutez that are in the
    contract's balance.

    Requires the `Administrable` mixin.
    """

    @sp.entry_point
    def withdraw_mutez(self, destination, amount):
        """(Admin only) Transfer `amount` mutez to `destination`."""
        sp.set_type(destination, sp.TAddress)
        sp.set_type(amount, sp.TMutez)
        sp.verify(self.isAdministrator(sp.sender), message="FA2_NOT_ADMIN")
        sp.send(destination, amount)


class OnchainviewTokenMetadata:
    """(Mixin) If present indexers use it to retrieve the token's metadata.

    Warning: If someone can change the contract's metadata he can change how
    indexers see every token metadata.
    """

    @sp.onchain_view()
    def token_metadata(self, token_id):
        """Returns the token-metadata URI for the given token."""
        sp.set_type(token_id, sp.TNat)
        sp.result(self.data.token_metadata[token_id])


class OnchainviewBalanceOf:
    """(Mixin) Non-standard onchain view equivalent to `balance_of`.

    Before onchain views were introduced in Michelson, the standard way
    of getting value from a contract was through a callback. Now that
    views are here we can create a view for the old style one.
    """

    @sp.onchain_view()
    def get_balance_of(self, requests):
        """Onchain view equivalent to the `balance_of` entrypoint."""
        sp.set_type(requests, sp.TList(t_balance_of_request))
        sp.result(
            sp.set_type_expr(
                self.balance_of_(requests), sp.TList(t_balance_of_response)
            )
        )


#################
# Mixins - Mint #
#################


class MintNft:
    """(Mixin) Non-standard `mint` entrypoint for FA2Nft with incrementing id.

    Requires the `Administrable` mixin.
    """

    @sp.entry_point
    def mint(self, batch):
        """Admin can mint new or existing tokens."""
        if self.has_royalties:
            sp.set_type(batch, t_mint_nft_royalties_batch)
        else:
            sp.set_type(batch, t_mint_nft_batch)
        sp.verify(self.isAdministrator(sp.sender), "FA2_NOT_ADMIN")
        with sp.for_("action", batch) as action:
            if self.has_royalties:
                self.validateRoyalties(action.royalties)
            token_id = sp.compute(self.data.last_token_id)
            metadata = sp.record(token_id=token_id, token_info=action.metadata)
            self.data.token_metadata[token_id] = metadata
            self.data.ledger[token_id] = action.to_
            if self.has_royalties:
                self.data.token_extra[token_id] = sp.record(royalty_info=action.royalties)
            self.data.last_token_id += 1


class MintFungible:
    """(Mixin) Non-standard `mint` entrypoint for FA2Fungible with incrementing
    id.

    Requires the `Administrable` mixin.
    """

    @sp.entry_point
    def mint(self, batch):
        """Admin can mint tokens."""
        if self.has_royalties:
            sp.set_type(batch, t_mint_fungible_royalties_batch)
        else:
            sp.set_type(batch, t_mint_fungible_batch)
        sp.verify(self.isAdministrator(sp.sender), "FA2_NOT_ADMIN")
        with sp.for_("action", batch) as action:
            with action.token.match_cases() as arg:
                with arg.match("new") as new:
                    if self.has_royalties:
                        self.validateRoyalties(new.royalties)
                    token_id = sp.compute(self.data.last_token_id)
                    self.data.token_metadata[token_id] = sp.record(
                        token_id=token_id, token_info=new.metadata
                    )
                    if self.has_royalties:
                        self.data.token_extra[token_id] = sp.record(
                            supply=action.amount,
                            royalty_info=new.royalties
                        )
                    else:
                        self.data.token_extra[token_id] = sp.record(
                            supply=action.amount
                        )
                    self.data.ledger[(action.to_, token_id)] = action.amount
                    self.data.last_token_id += 1
                with arg.match("existing") as token_id:
                    if self.allow_mint_existing:
                        sp.verify(self.is_defined(token_id), "FA2_TOKEN_UNDEFINED")
                        self.data.token_extra[token_id].supply += action.amount
                        from_ = (action.to_, token_id)
                        self.data.ledger[from_] = (
                            self.data.ledger.get(from_, 0) + action.amount
                        )
                    else:
                        sp.failwith("FA2_TX_DENIED")


class MintSingleAsset:
    """(Mixin) Non-standard `mint` entrypoint for FA2SingleAsset assuring only
    one token can be minted.

    Requires the `Administrable` mixin.
    """

    @sp.entry_point
    def mint(self, batch):
        """Admin can mint tokens."""
        sp.set_type(batch, t_mint_fungible_batch)
        sp.verify(self.isAdministrator(sp.sender), "FA2_NOT_ADMIN")
        with sp.for_("action", batch) as action:
            with action.token.match_cases() as arg:
                with arg.match("new") as new:
                    token_id = sp.nat(0)
                    sp.verify(~ self.data.token_metadata.contains(token_id), "FA2_TOKEN_DEFINED") # TODO: change this message?
                    self.data.token_metadata[token_id] = sp.record(
                        token_id=token_id, token_info=new.metadata
                    )
                    self.data.supply = action.amount
                    self.data.ledger[action.to_] = action.amount
                    self.data.last_token_id += 1
                with arg.match("existing") as token_id:
                    sp.verify(self.is_defined(token_id), "FA2_TOKEN_UNDEFINED")
                    self.data.supply += action.amount
                    from_ = action.to_
                    self.data.ledger[from_] = (
                        self.data.ledger.get(from_, 0) + action.amount
                    )


#################
# Mixins - Burn #
#################


class BurnNft:
    """(Mixin) Non-standard `burn` entrypoint for FA2Nft that uses the transfer
    policy permission."""

    @sp.entry_point
    def burn(self, batch):
        """Users can burn tokens if they have the transfer policy permission.

        Burning an nft destroys its metadata.
        """
        sp.set_type(batch, t_burn_batch)
        sp.verify(self.policy.supports_transfer, "FA2_TX_DENIED")
        with sp.for_("action", batch) as action:
            sp.verify(self.is_defined(action.token_id), "FA2_TOKEN_UNDEFINED")
            self.policy.check_tx_transfer_permissions(
                self, action.from_, action.from_, action.token_id
            )
            with sp.if_(action.amount > 0):
                sp.verify(
                    (action.amount == sp.nat(1))
                    & (self.data.ledger[action.token_id] == action.from_),
                    message="FA2_INSUFFICIENT_BALANCE",
                )
                # Burn the token
                del self.data.ledger[action.token_id]
                del self.data.token_metadata[action.token_id]
                if self.has_royalties:
                    del self.data.token_extra[action.token_id]


# TODO: test ledger, metadata, extra removal.
class BurnFungible:
    """(Mixin) Non-standard `burn` entrypoint for FA2Fungible that uses the
    transfer policy permission."""

    @sp.entry_point
    def burn(self, batch):
        """Users can burn tokens if they have the transfer policy
        permission."""
        sp.set_type(batch, t_burn_batch)
        sp.verify(self.policy.supports_transfer, "FA2_TX_DENIED")
        with sp.for_("action", batch) as action:
            sp.verify(self.is_defined(action.token_id), "FA2_TOKEN_UNDEFINED")
            self.policy.check_tx_transfer_permissions(
                self, action.from_, action.from_, action.token_id
            )
            from_ = (action.from_, action.token_id)
            # Burn from.
            from_balance = sp.compute(sp.as_nat(
                self.data.ledger.get(from_, 0) - action.amount,
                message="FA2_INSUFFICIENT_BALANCE",
            ))
            with sp.if_(from_balance == 0):
                del self.data.ledger[from_]
            with sp.else_():
                self.data.ledger[from_] = from_balance

            # Decrease supply or delete of it becomes 0.
            supply = sp.compute(
                sp.is_nat(self.data.token_extra[action.token_id].supply - action.amount)
            )
            with supply.match_cases() as arg:
                with arg.match("Some") as nat_supply:
                    # NOTE: if existing tokens can't be minted again, delete on 0.
                    if self.allow_mint_existing:
                        self.data.token_extra[action.token_id].supply = nat_supply
                    else:
                        with sp.if_(nat_supply == 0):
                            del self.data.token_extra[action.token_id]
                            del self.data.token_metadata[action.token_id]
                        with sp.else_():
                            self.data.token_extra[action.token_id].supply = nat_supply
                with arg.match("None"):
                    # NOTE: this is a failure case, but we give up instead
                    # of allowing a catstrophic failiure.
                    self.data.token_extra[action.token_id].supply = 0


class BurnSingleAsset:
    """(Mixin) Non-standard `burn` entrypoint for FA2SingleAsset that uses the
    transfer policy permission."""

    @sp.entry_point
    def burn(self, batch):
        """Users can burn tokens if they have the transfer policy
        permission."""
        sp.set_type(batch, t_burn_batch)
        sp.verify(self.policy.supports_transfer, "FA2_TX_DENIED")
        with sp.for_("action", batch) as action:
            sp.verify(self.is_defined(action.token_id), "FA2_TOKEN_UNDEFINED")
            self.policy.check_tx_transfer_permissions(
                self, action.from_, action.from_, action.token_id
            )
            from_ = action.from_
            # Burn from.
            from_balance = sp.compute(sp.as_nat(
                self.data.ledger.get(from_, 0) - action.amount,
                message="FA2_INSUFFICIENT_BALANCE",
            ))
            with sp.if_(from_balance == 0):
                del self.data.ledger[from_]
            with sp.else_():
                self.data.ledger[from_] = from_balance

            # Decrease supply.
            supply = sp.compute(
                sp.is_nat(self.data.supply - action.amount)
            )
            with supply.match_cases() as arg:
                with arg.match("Some") as nat_supply:
                    self.data.supply = nat_supply
                with arg.match("None"):
                    # NOTE: this is a failure case, but we give up instead
                    # of allowing a catstrophic failiure.
                    self.data.supply = 0


# TODO: implement versum views?
class Royalties:
    """(Mixin) Non-standard royalties for nft and fungible.
    Requires has_royalties=True on base.
    
    I admit, not very elegant, but I want to save that bigmap."""

    MIN_ROYALTIES = sp.nat(0)
    MAX_ROYALTIES = sp.nat(250)
    MAX_CONTRIBUTORS = sp.nat(3)

    def __init__(self):
        if self.ledger_type == "SingleAsset":
            raise Exception("Royalties not supported on SingleAsset")
        if self.has_royalties != True:
            raise Exception("Royalties not enabled on base")

    def validateRoyalties(self, royalties):
        """Inline function to validate royalties."""
        royalties = sp.set_type_expr(royalties, t_royalties)
        # Make sure absolute royalties and splits are in valid range.
        sp.verify((royalties.royalties >= Royalties.MIN_ROYALTIES) &
            (royalties.royalties <= Royalties.MAX_ROYALTIES), message="FA2_ROYALTIES_INVALID")
        sp.verify(sp.len(royalties.contributors) <= Royalties.MAX_CONTRIBUTORS, message="FA2_ROYALTIES_INVALID")
        
        # If royalties > 0, validate individual splits and that they add up to 1000
        with sp.if_(royalties.royalties > 0):
            total_relative = sp.local("total_relative", sp.nat(0))
            with sp.for_("contribution", royalties.contributors) as contribution:
                total_relative.value += contribution.relative_royalties
            sp.verify(total_relative.value == 1000, message="FA2_ROYALTIES_INVALID")
        # If royalties == 0, make sure contributors are empty
        with sp.else_():
            sp.verify(sp.len(royalties.contributors) == 0, message="FA2_ROYALTIES_INVALID")

    @sp.onchain_view(pure=True)
    def get_token_royalties(self, token_id):
        """Returns the token royalties information"""
        sp.set_type(token_id, sp.TNat)

        with sp.if_(self.data.token_extra.contains(token_id)):
            sp.result(self.data.token_extra[token_id].royalty_info)
        with sp.else_():
            sp.result(sp.record(royalties=sp.nat(0), contributors=[]))


class OnchainviewCountTokens:
    """(Mixin) Adds count_tokens onchain view."""
    
    @sp.onchain_view(pure=True)
    def count_tokens(self):
        """Returns the number of tokens in the FA2 contract."""
        sp.result(self.data.last_token_id)