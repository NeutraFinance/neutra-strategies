
import pytest
from brownie import Contract, accounts
import time 


def farmWithdraw(grailManager, grail_manager_contract, strategy, amount):
    grailManager_box = Contract.from_abi("GrailManager", grailManager.address, grail_manager_contract.abi)
    auth = accounts.at(strategy, True)
    grailManager_box.withdraw(amount, {'from': auth})

def test_report_profit(
    chain,
    token,
    deployed_vault,
    strategy,
    interface,
    harvest_token,
    harvest_token_whale,
    whale,
    conf
):
    # harvest to load deploy the funnds
    chain.sleep(1)
    chain.mine(1)

    strategy.harvest()
    chain.sleep(1)
    
    # send some funds to force the profit
    #harvest_token = interface.ERC20(conf['harvest_token'])

    # need a small amount to actually call insurance
    profit = int(strategy.estimatedTotalAssets() * 0.01)
    token.transfer(strategy, profit, {'from' : whale})
    strategy.harvest()
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    # insurance payment should be 10% of profit
    assert pytest.approx(0.1, rel=1e-1) == token.balanceOf(strategy.insurance()) / profit 



def test_full_payout(
    chain,
    token,
    deployed_vault,
    whale,
    strategy,
    interface,
    harvest_token,
    harvest_token_whale,
    conf,
    lp_price,
    lp_token,
    user,
    pid,
    StrategyInsurance,
    grailManager,
    grail_manager_contract
):
    vault = deployed_vault
    insurance = StrategyInsurance.at(strategy.insurance())

    chain.sleep(1)
    chain.mine(1)

    # harvest to load deploy the funnds
    strategy.harvest()
    chain.sleep(1)
    initial_debt = vault.strategies(strategy)[6]

    # send some funds to insurance for the payment
    insurance_budget = int(vault.totalAssets() * 0.02)
    token.transfer(strategy.insurance(), insurance_budget, {'from': whale})

    # steal 0.05% from from the strat to force a loss
    stolen = strategy.estimatedTotalAssets() * 0.0005
    sendAmount = int(stolen / lp_price)
    auth = accounts.at(strategy, True)
    farmWithdraw(grailManager, grail_manager_contract, strategy, sendAmount)
    lp_token.transfer(user, sendAmount, {'from': auth})

    # *** 1 *** Test the insurance payout

    # The max debt payout is insurace.maximumCompenstionRate() bps of the total debt of the strategy
    max_payout = int(vault.strategies(strategy)[6] * insurance.maximumCompenstionRate() / 10000)
    target_payout = min(max_payout, stolen)
    bal_before = token.balanceOf(insurance)

    # harvesting will trigger the payout
    tx = strategy.harvest()
    payout = bal_before - token.balanceOf(insurance)
    print('target: {}'.format(target_payout))
    print('payout: {}'.format(payout))

    dust = (stolen / 1000)
    assert pytest.approx(target_payout, rel=1e-1) == payout 
    assert tx.events['StrategyReported']['loss'] < dust
    chain.sleep(1)

    # *** 2 *** Now harvest and check no additional payout is made
    token.transfer(strategy, stolen, {'from': whale})

    bal_before = token.balanceOf(insurance)
    strategy.harvest()
    payout = bal_before - token.balanceOf(insurance)

    assert payout == 0
    assert insurance.lossSum() == 0


# def test_multiple_insurance_payouts(
#     chain,
#     token,
#     deployed_vault,
#     whale,
#     strategy,
#     interface,
#     harvest_token,
#     harvest_token_whale,
#     conf,
#     lp_price,
#     lp_token,
#     lp_farm,
#     user,
#     pid,
#     StrategyInsurance,
#     gov,
#     grailManager
# ):
#     vault = deployed_vault
#     insurance = StrategyInsurance.at(strategy.insurance())

#     chain.sleep(1)
#     chain.mine(1)

#     # harvest to load deploy the funnds
#     strategy.harvest()
#     chain.sleep(1)

#     # send some funds to insurance for the payment
#     insurance_budget = int(vault.totalAssets() * 0.02)
#     token.transfer(strategy.insurance(), insurance_budget, {"from": whale})

#     # steal 0.2% from from the strat to force a loss
#     stolen = strategy.estimatedTotalAssets() * 0.002
#     sendAmount = round(stolen / lp_price)
#     auth = accounts.at(strategy, True)
#     farmWithdraw(grailManager, pid, strategy, sendAmount)
#     lp_token.transfer(user, sendAmount, {"from": auth})
#     vault.setPerformanceFee(0, {'from':gov})
#     vault.updateStrategyPerformanceFee(strategy, 0, {'from':gov})

#     chain.mine(10)
#     chain.sleep(10)

#     # loop through payouts until the debt is erased
#     loss = stolen
#     print(loss)
#     loops = 0
#     payout = 0
#     while True:
#         loops = loops + 1
#         assert loops < 10
#         print("***** {} *****".format(loops))
#         # The max debt payout is insurace.maximumCompenstionRate() bps of the total debt of the strategy
#         max_payout = int(
#             vault.strategies(strategy)['totalDebt'] * insurance.maximumCompenstionRate() / 10000
#         )
#         target_payout = int(max(min(max_payout, loss - payout), 0))
#         bal_before = token.balanceOf(insurance)

#         chain.mine(10)
#         chain.sleep(10)
#         time.sleep(1)

#         # harvesting will trigger the payout
#         print("Pre Balance:  {}".format(strategy.estimatedTotalAssets()))
#         print("Pre Debt:     {}".format(int(vault.strategies(strategy)[6])))
#         print("Pre Loss Sum: {}".format(insurance.lossSum()))
#         tx = strategy.harvest()
#         payout = int(bal_before - token.balanceOf(insurance))
#         print("Target:   {}".format(target_payout))
#         print("Payout:   {}".format(payout))
#         print("Loss Sum: {}".format(insurance.lossSum()))
#         print("Loss:     {}".format(loss))
#         loss = int(loss - payout)


#         # assert False
#         if insurance.lossSum() == 0:
#             break

#         if (loss <= 0) : 
#             break

#         chain.sleep(1)

#     # there should now be no pending loss
#     assert loops > 0
#     assert insurance.lossSum() == 0
#     assert insurance_budget - token.balanceOf(insurance) == pytest.approx(
#         stolen, rel=1e-3
#     )