import brownie
from brownie import interface, Contract, accounts, MockAaveOracle
import pytest
import time 
from tests.helper import encode_function_data


POOL = '0x794a61358D6845594F94dc1DB02A252b5b4814aD' 
want = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174' # USDC
ORACLE = '0xb023e699F5a33916Ea823A16485e259257cA8Bd1'

POOL_ADDRESS_PROVIDER = '0xa97684ead0e402dc232d5a977953df7ecbab3cdb'




def steal(stealPercent, strategy_mock_oracle, token, chain, gov, user):
    steal = round(strategy_mock_oracle.estimatedTotalAssets() * stealPercent)
    strategy_mock_oracle.liquidatePositionAuth(steal, {'from': gov})
    token.transfer(user, strategy_mock_oracle.balanceOfWant(), {"from": accounts.at(strategy_mock_oracle, True)})
    chain.sleep(1)
    chain.mine(1)


def offSetDebtRatioLow(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, shortWhale):
    # use other AMM's LP to force some swaps 

    WHALEHAGOOOO = '0xaa30D6bba6285d0585722e2440Ff89E23EF68864'

    short = Contract(strategy_mock_oracle.short())
    swapAmtMax = short.balanceOf(lp_token)*swapPct
    swapAmt = min(swapAmtMax, short.balanceOf(shortWhale))
    print("Force Large Swap - to offset debt ratios")
    short.approve(router, 2**256-1, {"from": shortWhale})
    if router.address == '0xc873fEcbd354f5A56E00E710B90EF4201db2448d' :
        camelotRouter = interface.ICamelotRouter(router.address)
        camelotRouter.swapExactTokensForTokensSupportingFeeOnTransferTokens(swapAmt, 0, [short, token], shortWhale, '0x0000000000000000000000000000000000000000' , 2**256-1, {"from": shortWhale})

    else : 
        router.swapExactTokensForTokens(swapAmt, 0, [short, token], shortWhale, 2**256-1, {"from": shortWhale})
    

    

def offSetDebtRatioHigh(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, whale):
    short = Contract(strategy_mock_oracle.short())
    swapAmtMax = token.balanceOf(lp_token)*swapPct
    swapAmt = min(swapAmtMax, token.balanceOf(whale))
    print("Force Large Swap - to offset debt ratios")
    token.approve(router, 2**256-1, {"from": whale})
    if router.address == '0xc873fEcbd354f5A56E00E710B90EF4201db2448d' :
        camelotRouter = interface.ICamelotRouter(router.address)
        camelotRouter.swapExactTokensForTokensSupportingFeeOnTransferTokens(swapAmt, 0, [token, short], whale, '0x0000000000000000000000000000000000000000' , 2**256-1, {"from": whale})
    else :
        router.swapExactTokensForTokens(swapAmt, 0, [token, short], whale, 2**256-1, {"from": whale})

def offSetDebtRatioLowAmtIn(strategy_mock_oracle, lp_token, token, Contract, swapAmtMax, router, shortWhale):
    # use other AMM's LP to force some swaps 

    WHALEHAGOOOO = '0xaa30D6bba6285d0585722e2440Ff89E23EF68864'

    short = Contract(strategy_mock_oracle.short())
    swapAmt = min(swapAmtMax, short.balanceOf(shortWhale))
    print("Force Large Swap - to offset debt ratios")
    short.approve(router, 2**256-1, {"from": shortWhale})
    if router.address == '0xc873fEcbd354f5A56E00E710B90EF4201db2448d' :
        camelotRouter = interface.ICamelotRouter(router.address)
        camelotRouter.swapExactTokensForTokensSupportingFeeOnTransferTokens(swapAmt, 0, [short, token], shortWhale, '0x0000000000000000000000000000000000000000' , 2**256-1, {"from": shortWhale})

    else : 
        router.swapExactTokensForTokens(swapAmt, 0, [short, token], shortWhale, 2**256-1, {"from": shortWhale})
    

    

def offSetDebtRatioHighAmtIn(strategy_mock_oracle, lp_token, token, Contract, swapAmtMax, router, whale):
    short = Contract(strategy_mock_oracle.short())
    swapAmt = min(swapAmtMax, token.balanceOf(whale))
    print("Force Large Swap - to offset debt ratios")
    token.approve(router, 2**256-1, {"from": whale})
    if router.address == '0xc873fEcbd354f5A56E00E710B90EF4201db2448d' :
        camelotRouter = interface.ICamelotRouter(router.address)
        camelotRouter.swapExactTokensForTokensSupportingFeeOnTransferTokens(swapAmt, 0, [token, short], whale, '0x0000000000000000000000000000000000000000' , 2**256-1, {"from": whale})
    else :
        router.swapExactTokensForTokens(swapAmt, 0, [token, short], whale, 2**256-1, {"from": whale})

def setOracleShortPriceToLpPrice(strategy_mock_oracle):
    short = Contract(strategy_mock_oracle.short())
    # Oracle should reflect the "new" price
    pool_address_provider = interface.IPoolAddressesProvider(POOL_ADDRESS_PROVIDER)
    oracle = MockAaveOracle.at(pool_address_provider.getPriceOracle())
    new_price = strategy_mock_oracle.getLpPrice()
    print("Oracle price before", oracle.getAssetPrice(short))
    oracle.setAssetPrice(short, new_price * 100)
    print("Strategy Lp price", new_price)
    print("Oracle price", oracle.getAssetPrice(short))
    print("Strategy oracle price", strategy_mock_oracle.getOraclePrice())

def strategySharePrice(strategy_mock_oracle, vault):
    return strategy_mock_oracle.estimatedTotalAssets() / vault.strategies(strategy_mock_oracle)['totalDebt']

def test_lossy_withdrawal_partial(
    chain, gov, accounts, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, amount, RELATIVE_APPROX, conf
):
    #strategy.approveContracts({'from':gov})
    # Deposit to the vault and harvest
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})

    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 100_00, {"from": gov})
    chain.sleep(1)
    strategy_mock_oracle.harvest()
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
    # Steal from the strategy
    stealPercent = 0.005
    steal(stealPercent, strategy_mock_oracle, token, chain, gov, user)
    balBefore = token.balanceOf(user)

    #give RPC a little break to stop it spzzing out 
    time.sleep(5)

    half = int(amount / 2)
    vault_mock_oracle.withdraw(half, user, 100, {'from' : user}) 
    balAfter = token.balanceOf(user)

    assert pytest.approx(balAfter - balBefore, rel = 2e-3) == (half * (1-stealPercent)) 


def test_partialWithdrawal_unbalancedDebtLow(
    chain, gov, accounts, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, lp_token ,amount, RELATIVE_APPROX, conf, router, shortWhale, Contract
):
    #strategy.approveContracts({'from':gov})
    # Deposit to the vault and harvest
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})

    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 100_00, {"from": gov})
    chain.sleep(1)
    strategy_mock_oracle.harvest()
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    swapPct = 0.01
    # use other AMM's LP to force some swaps 
    offSetDebtRatioLow(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, shortWhale)
    setOracleShortPriceToLpPrice(strategy_mock_oracle)
    preWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))

    strategyLoss = amount - strategy_mock_oracle.estimatedTotalAssets()
    lossPercent = strategyLoss / amount

    chain.sleep(1)
    chain.mine(1)
    balBefore = token.balanceOf(user)
    ssp_before = strategySharePrice(strategy_mock_oracle, vault_mock_oracle)

    #give RPC a little break to stop it spzzing out 
    time.sleep(5)
    percentWithdrawn = 0.7

    withdrawAmt = int(amount * percentWithdrawn)
    vault_mock_oracle.withdraw(withdrawAmt, user, 100, {'from' : user}) 
    balAfter = token.balanceOf(user)
    print("Withdraw Amount : ")
    print(balAfter - balBefore)

    assert (balAfter - balBefore) < int(percentWithdrawn * amount * (1 - lossPercent))

    # confirm the debt ratio wasn't impacted
    postWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Post Withdraw debt Ratio :  {0}'.format(postWithdrawDebtRatio))
    assert pytest.approx(preWithdrawDebtRatio, rel = 2e-3) == postWithdrawDebtRatio

    # confirm the loss was not felt disproportionately by the strategy - Strategy Share Price
    ssp_after = strategySharePrice(strategy_mock_oracle, vault_mock_oracle)
    assert ssp_after >= ssp_before * (1 - 1 / 100000)

def test_partialWithdrawal_unbalancedDebtHigh(
    chain, gov, accounts, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, lp_token ,amount, RELATIVE_APPROX, conf, router, whale
):
    #strategy.approveContracts({'from':gov})
    # Deposit to the vault and harvest
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})

    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 100_00, {"from": gov})
    chain.sleep(1)
    strategy_mock_oracle.harvest()
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    swapPct = 0.015
    offSetDebtRatioHigh(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, whale)
    setOracleShortPriceToLpPrice(strategy_mock_oracle)

    strategyLoss = amount - strategy_mock_oracle.estimatedTotalAssets()
    lossPercent = strategyLoss / amount

    preWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))

    chain.sleep(1)
    chain.mine(1)
    balBefore = token.balanceOf(user)
    ssp_before = strategySharePrice(strategy_mock_oracle, vault_mock_oracle)

    #give RPC a little break to stop it spzzing out 
    time.sleep(5)
    percentWithdrawn = 0.7

    withdrawAmt = int(amount * percentWithdrawn)
    vault_mock_oracle.withdraw(withdrawAmt, user, 100, {'from' : user})
    balAfter = token.balanceOf(user)
    print("Withdraw Amount : ")
    print(balAfter - balBefore)
    assert (balAfter - balBefore) < int(percentWithdrawn * amount * (1 - lossPercent))
    
    # confirm the debt ratio wasn't impacted
    postWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Post Withdraw debt Ratio :  {0}'.format(postWithdrawDebtRatio))
    assert pytest.approx(preWithdrawDebtRatio, rel = 2e-3) == postWithdrawDebtRatio

    # confirm the loss was not felt disproportionately by the strategy - Strategy Share Price
    ssp_after = strategySharePrice(strategy_mock_oracle, vault_mock_oracle)
    assert ssp_after >= ssp_before * (1 - 1 / 100000)


# Load up the vault with 2 strategies, deploy them with harvests and then withdraw 75% from the vault to test  withdrawing 100% from one of the strats is okay. 
def test_withdraw_all_from_multiple_strategies(
    gov, vault_mock_oracle, strategy_mock_oracle, token, user, amount, conf, chain, strategy_contract, strategist, StrategyInsurance, keeper, grail_manager_contract, grail_manager_proxy_contract
):
    # Deposit to the vault and harvest
    user_balance_before = token.balanceOf(user)
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})
    chain.sleep(1)
    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 50_00, {"from": gov})

    new_strategy = strategist.deploy(strategy_contract, vault_mock_oracle)

    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    grailManager = gov.deploy(grail_manager_contract)

    # grailManager.initialize(gov, strategy, grailConfig, {'from': gov})
    grailConfig = [new_strategy.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]

    encoded_initializer_function = encode_function_data(grailManager.initialize, gov, new_strategy, grailConfig)
    
    grailManagerProxy = gov.deploy(grail_manager_proxy_contract, grailManager.address, encoded_initializer_function)

    new_strategy.setGrailManager(grailManagerProxy.address, {'from': gov})

    newInsurance = strategist.deploy(StrategyInsurance, new_strategy)
    new_strategy.setKeeper(keeper)
    new_strategy.setInsurance(newInsurance, {'from': gov})
    vault_mock_oracle.addStrategy(new_strategy, 50_00, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    strategy_mock_oracle.harvest()
    chain.sleep(1)
    new_strategy.harvest()

    half = int(amount/2)

    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=2e-3) == half
    assert pytest.approx(new_strategy.estimatedTotalAssets(), rel=2e-3) == half

    # Withdrawal
    vault_mock_oracle.withdraw(amount, {"from": user})
    assert (
        pytest.approx(token.balanceOf(user), rel=1e-5) == user_balance_before
    )


def test_Sandwhich_High(
    chain, gov, accounts, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, lp_token ,amount, RELATIVE_APPROX, conf, router, whale

):
    #strategy.approveContracts({'from':gov})
    # Deposit to the vault and harvest
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})

    balBefore = token.balanceOf(user)

    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 100_00, {"from": gov})
    chain.sleep(1)
    strategy_mock_oracle.harvest()
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # do a big swap to offset debt ratio's massively 
    swapPct = 0.7
    short = Contract(strategy_mock_oracle.short())

    balBeforeWhale = short.balanceOf(whale)

    offSetDebtRatioHigh(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, whale)

    offsetEstimatedAssets  = strategy_mock_oracle.estimatedTotalAssets()
    strategyLoss = amount - strategy_mock_oracle.estimatedTotalAssets()
    lossPercent = strategyLoss / amount

    preWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))


    print("Try to rebalance - this should fail due to _testPriceSource()")
    with brownie.reverts():
        strategy_mock_oracle.rebalanceDebt()
    assert preWithdrawDebtRatio == strategy_mock_oracle.calcDebtRatio()

    chain.sleep(1)
    chain.mine(1)
    balBefore = token.balanceOf(user)

    balAftereWhale = short.balanceOf(whale)


    #give RPC a little break to stop it spzzing out 
    time.sleep(5)
    percentWithdrawn = 0.7

    withdrawAmt = int(amount * percentWithdrawn)

    with brownie.reverts():     
        vault_mock_oracle.withdraw({'from' : user}) 

    # swap all tokens back 
    swapPct = 1 

    balanceDelta = balAftereWhale - balBeforeWhale

    offSetDebtRatioLowAmtIn(strategy_mock_oracle, lp_token, token, Contract, balanceDelta, router, whale)


def test_Sandwhich_Low(
    chain, gov, accounts, token, vault_mock_oracle, strategy_mock_oracle, user, strategist, lp_token ,amount, RELATIVE_APPROX, conf, router, shortWhale
):
    #strategy.approveContracts({'from':gov})
    # Deposit to the vault and harvest
    token.approve(vault_mock_oracle.address, amount, {"from": user})
    vault_mock_oracle.deposit(amount, {"from": user})

    balBefore = token.balanceOf(user)

    vault_mock_oracle.updateStrategyDebtRatio(strategy_mock_oracle.address, 100_00, {"from": gov})
    chain.sleep(1)
    strategy_mock_oracle.harvest()
    assert pytest.approx(strategy_mock_oracle.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # do a big swap to offset debt ratio's massively 
    swapPct = 0.7
    offSetDebtRatioLow(strategy_mock_oracle, lp_token, token, Contract, swapPct, router, shortWhale)

    print("Try to rebalance - this should fail due to _testPriceSource()")
    # for some reason brownie.reverts doesn't fail.... here although transaction reverts... 
    with brownie.reverts():     
        strategy_mock_oracle.rebalanceDebt()

    offsetEstimatedAssets  = strategy_mock_oracle.estimatedTotalAssets()
    strategyLoss = amount - strategy_mock_oracle.estimatedTotalAssets()
    lossPercent = strategyLoss / amount

    preWithdrawDebtRatio = strategy_mock_oracle.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))

    chain.sleep(1)
    chain.mine(1)
    balBefore = token.balanceOf(user)

    #give RPC a little break to stop it spzzing out 
    time.sleep(5)
    percentWithdrawn = 0.7

    withdrawAmt = int(amount * percentWithdrawn)

    with brownie.reverts():     
        vault_mock_oracle.withdraw({'from' : user}) 
