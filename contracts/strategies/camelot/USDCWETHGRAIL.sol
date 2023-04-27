// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.15;

import {
    SafeERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "./CoreStrategyAaveGrail.sol";
import "../../interfaces/aave/IAaveOracle.sol";

interface IGrailManager {
    function deposit(uint256 _amount) external;
    function withdraw(uint256 _amount) external;
    function harvest() external;
    function balance() external view returns (uint256 _amount);
    function getPendingRewards() external view returns (uint256, uint256);
}


contract USDCWETHGRAIL is CoreStrategyAaveGrail {
    using SafeERC20 for IERC20;
    uint256 constant farmPid = 0;

    event SetGrailManager(address grailManager);
    event SetAave(address oracle, address pool);

    constructor(address _vault)
        CoreStrategyAaveGrail(
            _vault,
            CoreStrategyAaveConfig(
                0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8, // want -> USDC
                0x82aF49447D8a07e3bd95BD0d56f35241523fBab1, // short -> WETH
                0x84652bb2539513BAf36e225c930Fdd8eaa63CE27, // wantShortLP -> USDC/WETH
                0x625E7708f30cA75bfd92586e17077590C60eb4cD, // aToken
                0x0c84331e39d6658Cd6e6b9ba04736cC4c4734351, // variableDebtTOken
                0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb, // PoolAddressesProvider
                0xc873fEcbd354f5A56E00E710B90EF4201db2448d, // router
                1e4 //mindeploy
            )
        )
    {}

    function _setup() internal override {
        weth = router.WETH();
    }

    function balancePendingHarvest() public view override returns (uint256) {
        (,uint256 grailRewards) = IGrailManager(grailManager).getPendingRewards();
        return grailRewards;
    }

    function _depositLp() internal override {
        uint256 lpBalance = wantShortLP.balanceOf(address(this));
        IGrailManager(grailManager).deposit(lpBalance);
    }

    function _withdrawFarm(uint256 _amount) internal override {
        if (_amount > 0)
            IGrailManager(grailManager).withdraw(_amount);
    }

    function claimHarvest() internal override {
        IGrailManager(grailManager).harvest();
    }

    function countLpPooled() internal view override returns (uint256) {
        return IGrailManager(grailManager).balance();
    }

    function setGrailManager(address _grailManager) external onlyAuthorized {
        grailManager = _grailManager;
        IERC20(address(wantShortLP)).safeApprove(_grailManager, type(uint256).max);
        emit SetGrailManager(_grailManager);
    }

    function setAave(address _oracle, address _pool) external onlyAuthorized {
        require(_oracle != address(0) && _pool != address(0), "invalid address");
        oracle = IAaveOracle(_oracle);
        pool = IPool(_pool);
        want.safeApprove(address(pool), type(uint256).max);
        short.safeApprove(address(pool), type(uint256).max);
        emit SetAave(_oracle, _pool);
    }
}
