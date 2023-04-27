from pathlib import Path

from brownie import accounts, config, network, project, web3, StrategyInsurance
from eth_utils import is_checksum_address
from tests.helper import encode_function_data
import click

API_VERSION = config["dependencies"][0].split("@")[-1]
Vault = project.load(
    Path.home() / ".brownie" / "packages" / config["dependencies"][0]
).Vault

# edit this to deploy
from brownie import USDCWETHGRAIL, GrailManager, GrailManagerProxy, CommonHealthCheck

Strategy = USDCWETHGRAIL

def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")
    #vault = Vault.at(get_address("Deployed Vault: "))
    vault = Vault.deploy({'from': dev})
    
    token = '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'
    

    vault.initialize(token, dev, dev, "Test Neutra USDC", "tnUSDC", dev, dev)

    print(
        f"""
    Strategy Parameters

       api: {vault.apiVersion()}
     token: {vault.token()}
      name: '{vault.name()}'
    symbol: '{vault.symbol()}'
    """
    )
    
    if input("Continue? y/[N]: ").lower() != "y":
        print('Thanks. Byeee')
        return

    # publish_source = click.confirm("Verify source on etherscan?")
    # if input("Deploy Strategy? y/[N]: ").lower() != "y":
    #     return
    
    # strategy = Strategy.deploy(vault, {"from": dev}, publish_source=publish_source)
    print('Deploying...')


    conf = {
        'lp_token': '0x84652bb2539513baf36e225c930fdd8eaa63ce27',
        'lp_farm': '0x6BC938abA940fB828D39Daa23A94dfc522120C11',
        'harvest_token' : '0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8',
        'router' : '0xc873fEcbd354f5A56E00E710B90EF4201db2448d'
    }

    strat = Strategy.deploy(vault,{"from": dev})
    yieldBooster = '0xD27c373950E7466C53e5Cd6eE3F70b240dC0B1B1'
    xGrail = '0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b'
    grailManager = GrailManager.deploy({'from': dev})

    grailConfig = [strat.want(), conf['lp_token'], conf['harvest_token'], xGrail, conf['lp_farm'], conf['router'], yieldBooster]
    grailManager.initialize(dev, strat, grailConfig, {'from': dev})

    encoded_initializer_function = encode_function_data(grailManager.initialize, dev, strat, grailConfig)

    grailManagerProxy = GrailManagerProxy.deploy(grailManager.address, encoded_initializer_function, {'from':dev})
    strat.setGrailManager(grailManagerProxy, {'from':dev})

    insurance = StrategyInsurance.deploy(strat, {'from':dev})
    strat.setInsurance(insurance, {'from': dev})  
    
    healthCare = CommonHealthCheck.deploy({'from':dev})
    strat.setHealthCheck(healthCare, {'from': dev})

    strat.setMinReportDelay(28740, {'from':dev})
    # strat.setMaxReportDelay(43200, {'from':dev})
    # offset = 10
    # strat.setDebtThresholds(9800 + offset, 10200 - offset, 5000, {'from':dev})
    # strat.setCollateralThresholds(4500, 5000, 5500, 8500, {'from':dev})
    
    # flatten code
    # f = open("flat.sol", "w")
    # Strategy.get_verification_info()
    # f.write(Strategy._flattener.flattened_source)
    # f.close()
    print('Successfully Deploy. See flat.sol for verification and don\'t forget to set the HEALTH CHECK!!')
    