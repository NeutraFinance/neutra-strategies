import brownie
from brownie import interface, Contract, accounts
import pytest
import time 

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


def test_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    strategy_contract,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
    grail_manager_contract,
    conf,
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    newGrailManager = gov.deploy(grail_manager_contract, gov)

    new_strategy = strategist.deploy(strategy_contract, vault,  newGrailManager.address)

    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    grailConfig = [new_strategy.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]
    newGrailManager.initialize(gov, new_strategy, grailConfig, {'from': gov})

    # migrate to a new strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )



def test_migration_with_low_calcdebtratio(
    chain,
    token,
    vault,
    strategy,
    amount,
    lp_token,
    Contract,
    strategy_contract,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
    router,
    shortWhale,
    grail_manager_contract,
    conf,
):

    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # use other AMM's LP to force some swaps 

    print("Force Large Swap - to offset debt ratios")

    swapPct = 0.015

    offSetDebtRatioLow(strategy, lp_token, token, Contract, swapPct, router, shortWhale)
    preWithdrawDebtRatio = strategy.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))

    newGrailManager = gov.deploy(grail_manager_contract, gov)

    new_strategy = strategist.deploy(strategy_contract, vault,  newGrailManager.address)

    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    grailConfig = [new_strategy.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]
    newGrailManager.initialize(gov, new_strategy, grailConfig, {'from': gov})


    # migrate to a new strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    # will be some loss so use rel = 2e-3 (due to forcing debt ratio away from 100%)
    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=2e-3)
        == amount
    )


def test_migration_with_high_calcdebtratio(
    chain,
    token,
    vault,
    strategy,
    amount,
    lp_token,
    Contract,
    strategy_contract,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
    router,
    whale,
    grail_manager_contract,
    conf,
):

    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # use other AMM's LP to force some swaps
    short = Contract(strategy.short())


    print("Force Large Swap - to offset debt ratios")
    swapPct = 0.015
    offSetDebtRatioHigh(strategy, lp_token, token, Contract, swapPct, router, whale)

    preWithdrawDebtRatio = strategy.calcDebtRatio()
    print('Pre Withdraw debt Ratio :  {0}'.format(preWithdrawDebtRatio))

    # migrate to a new strategy
    newGrailManager = gov.deploy(grail_manager_contract, gov)

    new_strategy = strategist.deploy(strategy_contract, vault,  newGrailManager.address)

    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    grailConfig = [new_strategy.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]
    newGrailManager.initialize(gov, new_strategy, grailConfig, {'from': gov})
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    # will be some loss so use rel = 2e-3 (due to forcing debt ratio away from 100%)
    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=2e-3)
        == amount
    )

