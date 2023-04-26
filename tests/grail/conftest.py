import pytest
from brownie import config
from brownie import Contract
from brownie import interface, StrategyInsurance, GrailManager, GrailManagerProxy, USDCWETHGRAIL ,accounts
from tests.helper import encode_function_data

DQUICK_PRICE = 159.41
FTM_PRICE = 1.57
WETH_PRICE = 3470
WBTC_PRICE = 46000
SPOOKY_PRICE = 11.78
SPIRIT_PRICE = 5.78
ZIP_PRICE = 0.01
SUSHI_PRICE = 1.7
GRAIL = '0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8'
GRAIL_PRICE = 3000
SUSHI_FARM = '0xF4d73326C13a4Fc5FD7A064217e12780e9Bd62c3'

ORACLE = '0xb56c2F0B653B2e0b10C9b928C8580Ac5Df02C7C7'

POOL_ADDRESS_PROVIDER = '0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb'
# Tokens
USDC = '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'
USDC_WHALE = '0x489ee077994B6658eAfA855C308275EAd8097C4A'
WETH_WHALE = '0x489ee077994B6658eAfA855C308275EAd8097C4A'
SUSHI = '0xd4d42F0b6DEF4CE0383636770eF773390d85c61A'

GRAIL_ROUTER = '0xc873fEcbd354f5A56E00E710B90EF4201db2448d'

SUSHISWAP_ROUTER = '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
CONFIG = {
    'USDCWETHSUSHI': {
        'token': USDC,
        'whale': USDC_WHALE,
        'shortWhale' : WETH_WHALE,
        'deposit': 1e6,
        'harvest_token': SUSHI,
        'harvest_token_price': SUSHI_PRICE * 1e-12,
        'harvest_token_whale': '0x9873795F5DAb11e1c0342C4a58904c59827ede0c',
        'lp_token': '0x905dfCD5649217c42684f23958568e533C711Aa3',
        'lp_whale': '0xea2a2AC89281d1673E5018F60933970626905285',
        'lp_farm': SUSHI_FARM,
        'pid': 0,
        'router': SUSHISWAP_ROUTER,
    },

    'USDCWETHGRAIL': {
        'token': USDC,
        'whale': USDC_WHALE,
        'shortWhale' : WETH_WHALE,
        'deposit': 1e6,
        'harvest_token': GRAIL,
        'harvest_token_price': GRAIL_PRICE * 1e-12, #note adjust by 1e-12 due to dif in decimals between USDC & GRAIL token i.e. 6 vs 18 
        'harvest_token_whale': '0x5A5A7C0108CEf44549b7782495b1Df2Ad5294Da3',
        'lp_token': '0x84652bb2539513baf36e225c930fdd8eaa63ce27',
        'lp_whale': '0x5422AA06a38fd9875fc2501380b40659fEebD3bB',
        'lp_farm': '0x6BC938abA940fB828D39Daa23A94dfc522120C11',
        'pid': 0,
        'router': GRAIL_ROUTER,
    },

}

@pytest.fixture
def grail_manager_contract():
    yield  GrailManager

@pytest.fixture
def grail_manager_proxy_contract():
    yield GrailManagerProxy

@pytest.fixture
def strategy_contract():
    yield  USDCWETHGRAIL


@pytest.fixture
def conf(strategy_contract):
    yield CONFIG[strategy_contract._name]

@pytest.fixture
def gov(accounts):
    #yield accounts.at("0x7601630eC802952ba1ED2B6e4db16F699A0a5A87", force=True)
    yield accounts[1]

@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def token(conf):
    yield interface.IERC20Extended(conf['token'])

@pytest.fixture
def router(conf):
    yield interface.ICamelotRouter(conf['router'])


@pytest.fixture
def camelotRouter(conf):
    yield interface.ICamelotRouter(conf['router'])

@pytest.fixture
def whale(token, conf ,Contract, accounts) : 
    yield accounts.at(conf['whale'], True)

@pytest.fixture
def shortWhale(token, conf ,Contract, accounts) : 
    yield accounts.at(conf['shortWhale'], True)


@pytest.fixture
def amount(accounts, token, user, conf, whale):
    amount = 10_000 * 10 ** token.decimals()
    amount = min(amount, int(0.5*token.balanceOf(whale)))
    amount = min(amount, int(0.005*token.balanceOf(conf['lp_token'])))

    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at(whale, force=True)
    token.transfer(user, amount, {"from": reserve})
    yield amount

@pytest.fixture
def large_amount(accounts, token, user, conf, whale):
    amount = 10_000_000 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at(whale, force=True)

    amount = min(amount, int(0.5*token.balanceOf(reserve)))
    amount = min(amount, int(0.2*token.balanceOf(conf['lp_token'])))
    token.transfer(user, amount, {"from": reserve})
    yield amount


@pytest.fixture
def weth():
    token_address = "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
    yield interface.IERC20Extended(token_address)


@pytest.fixture
def weth_amout(user, weth):
    weth_amout = 10 ** weth.decimals()
    user.transfer(weth, weth_amout)
    yield weth_amout


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    assert vault.token() == token.address
    yield vault

@pytest.fixture
def vault_mock_oracle(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    assert vault.token() == token.address
    yield vault

@pytest.fixture
def strategy_before_set(strategist, keeper, vault, strategy_contract, gov, conf):
    # strategy = strategy_contract.deploy(vault, {'from': strategist,'gas_limit': 20000000})
    strategy = strategist.deploy(strategy_contract, vault)
    insurance = strategist.deploy(StrategyInsurance, strategy)
    strategy.setKeeper(keeper)
    strategy.setInsurance(insurance, {'from': gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy

@pytest.fixture
def grailManager(grail_manager_proxy_contract, strategy_before_set, grail_manager_contract, gov, conf) : 
    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    
    grailManager = gov.deploy(grail_manager_contract)

    # grailManager.initialize(gov, strategy, grailConfig, {'from': gov})
    grailConfig = [strategy_before_set.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]

    encoded_initializer_function = encode_function_data(grailManager.initialize, gov, strategy_before_set, grailConfig)
    
    grailManagerProxy = gov.deploy(grail_manager_proxy_contract, grailManager.address, encoded_initializer_function)
    yield grailManagerProxy

@pytest.fixture
def strategy(strategy_before_set, grailManager, gov):
    strategy_before_set.setGrailManager(grailManager, {'from': gov})
    yield strategy_before_set

@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-4

@pytest.fixture
def lp_token(conf):
    yield interface.ERC20(conf['lp_token'])

@pytest.fixture
def lp_whale(accounts, conf):
    yield accounts.at(conf['lp_whale'], True)

@pytest.fixture
def harvest_token(conf):
    yield interface.ERC20(conf['harvest_token'])

@pytest.fixture
def harvest_token_whale(conf, accounts):
    yield accounts.at(conf['harvest_token_whale'], True)

@pytest.fixture
def pid(conf):
    yield conf['pid']

@pytest.fixture
def lp_price(token, lp_token):
    yield (token.balanceOf(lp_token) * 2) / lp_token.totalSupply()  

@pytest.fixture
def deployed_vault(chain, accounts, gov, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    print("Amount: ", amount)
    print("User: ", user)
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount
    
    # harvest
    chain.sleep(1)
    
    print("Vault: ",token.balanceOf(vault.address))
    print("Strategy: ",token.balanceOf(strategy.address))
    strategy.harvest()
    strat = strategy
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
    yield vault 

@pytest.fixture
def deployed_vault_large_deposit(chain, accounts, gov, token, vault, strategy, user, strategist, large_amount, RELATIVE_APPROX):
    # Deposit to the vault
    token.approve(vault.address, large_amount, {"from": user})
    vault.deposit(large_amount, {"from": user})
    assert token.balanceOf(vault.address) == large_amount
    
    # harvest
    chain.sleep(1)
    #strategy.approveContracts({'from':gov})
    strategy.harvest()
    strat = strategy
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == large_amount
    yield vault  


@pytest.fixture
def strategy_mock_initialized_vault(chain, accounts, gov, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, amount, RELATIVE_APPROX):
    # Deposit to the vault
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    print("Amount: ", amount)
    print("User: ", user)
    vault_mock_oracle.deposit(amount, {"from": user})
    assert token.balanceOf(vault_mock_oracle.address) == amount
    
    # harvest
    chain.sleep(1)
    
    print("Vault: ",token.balanceOf(vault_mock_oracle.address))
    print("Strategy: ",token.balanceOf(strategy_mock_oracle.address))
    strategy_mock_oracle.harvest()
    strat = strategy_mock_oracle
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
    yield vault_mock_oracle 

@pytest.fixture
def strategy_mock_oracle_before_set(token, amount, user, strategist, keeper, vault_mock_oracle, strategy_contract, gov ,MockAaveOracle, conf):
    pool_address_provider = interface.IPoolAddressesProvider(POOL_ADDRESS_PROVIDER)
    old_oracle = pool_address_provider.getPriceOracle()
    # Set the mock price oracle
    oracle = MockAaveOracle.deploy(old_oracle, {'from': accounts[0]})

    admin = accounts.at(pool_address_provider.owner(), True)
    pool_address_provider.setPriceOracle(oracle, {'from': admin})

    strategy_mock_oracle = strategist.deploy(strategy_contract, vault_mock_oracle)
    insurance = strategist.deploy(StrategyInsurance, strategy_mock_oracle)
    strategy_mock_oracle.setKeeper(keeper)
    strategy_mock_oracle.setInsurance(insurance, {'from': gov})

    vault_mock_oracle.addStrategy(strategy_mock_oracle, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy_mock_oracle

@pytest.fixture
def grailManager_mock_oracle(grail_manager_proxy_contract, grail_manager_contract, gov, strategy_mock_oracle_before_set, conf) : 
    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    
    grailManager = gov.deploy(grail_manager_contract)

    # grailManager.initialize(gov, strategy, grailConfig, {'from': gov})
    grailConfig = [strategy_mock_oracle_before_set.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]

    encoded_initializer_function = encode_function_data(grailManager.initialize, gov, strategy_mock_oracle_before_set, grailConfig)
    
    grailManagerProxy = gov.deploy(grail_manager_proxy_contract, grailManager.address, encoded_initializer_function)

    yield grailManagerProxy

@pytest.fixture
def strategy_mock_oracle(strategy_mock_oracle_before_set, grailManager_mock_oracle, gov):
    strategy_mock_oracle_before_set.setGrailManager(grailManager_mock_oracle, {'from': gov})
    yield strategy_mock_oracle_before_set


# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
#@pytest.fixture(scope="function", autouse=True)
#def shared_setup(strategy, strategy_mock_oracle, grailManager, grailManager_mock_oracle):
#    pass
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
