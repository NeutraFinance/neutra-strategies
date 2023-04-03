// SPDX-License-Identifier: AGPL-3.0

pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

// Grail Router
import "@openzeppelin/contracts/proxy/Initializable.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {
    SafeMath,
    Address,
    IERC20
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "../../interfaces/camelot/ICamelotRouter.sol";
import {VaultAPI} from "@yearnvaults/contracts/BaseStrategy.sol";

struct GrailManagerConfig {
    address want;
    address lp;
    address grail;
    address xGrail;
    address pool;
    address router;
    address yieldBooster;
}

interface INFTHandler is IERC721Receiver {
    function onNFTHarvest(
        address operator,
        address to,
        uint256 tokenId,
        uint256 grailAmount,
        uint256 xGrailAmount
    ) external returns (bool);

    function onNFTAddToPosition(
        address operator,
        uint256 tokenId,
        uint256 lpAmount
    ) external returns (bool);

    function onNFTWithdraw(
        address operator,
        uint256 tokenId,
        uint256 lpAmount
    ) external returns (bool);
}

interface CoreStrategyAPI {
    function harvestTrigger(uint256 callCost) external view returns (bool);

    function harvest() external;

    function calcDebtRatio() external view returns (uint256);

    function calcCollateral() external view returns (uint256);

    function rebalanceDebt() external;

    function rebalanceCollateral() external;

    function strategist() external view returns (address);
}

interface IXGrailToken {
    function allocate(
        address usageAddress,
        uint256 amount,
        bytes calldata usageData
    ) external;

    function balanceOf(address owner) external view returns (uint256);

    function approveUsage(address usage, uint256 _amount) external;
}

interface INFTPool {
    function approve(address to, uint256 tokenId) external;

    function getStakingPosition(uint256 tokenId)
        external
        view
        returns (
            uint256 amount,
            uint256 amountWithMultiplier,
            uint256 startLockTime,
            uint256 lockDuration,
            uint256 lockMultiplier,
            uint256 rewardDebt,
            uint256 boostPoints,
            uint256 totalMultiplier
        );

    function createPosition(uint256 amount, uint256 lockDuration) external;

    function lastTokenId() external view returns (uint256);

    function addToPosition(uint256 tokenId, uint256 amountToAdd) external;

    function withdrawFromPosition(uint256 tokenId, uint256 amountToWithdraw)
        external;

    function harvestPosition(uint256 tokenId) external;

    function xGrailRewardsShare() external view returns (uint256);

    function pendingRewards(uint256 tokenId) external view returns (uint256);

    function balanceOf(address owner) external view returns (uint256);

    function exists(uint256 tokenId) external view returns (bool);
}

/**
 * @title Robovault Keeper Proxy
 * @author robovault
 * @notice
 *  KeeperProxy implements a proxy for Robovaults CoreStrategy. The proxy provide
 *  More flexibility will roles, allowing for multiple addresses to be granted
 *  keeper permissions.
 *
 */
contract GrailManager is Initializable, INFTHandler {
    using Address for address;
    using SafeMath for uint256;

    uint256 private constant _TOTAL_REWARDS_SHARES = 10000;

    // camelot contracts
    INFTPool public pool;
    IXGrailToken public xGrail;
    IERC20 public grail;
    ICamelotRouter public router;
    address public yieldBooster;

    CoreStrategyAPI public strategy;
    IERC20 public lp;
    address public strategist;
    address public manager;
    uint256 public tokenId;
    IERC20 public want;

    mapping(uint256 => address) tokenIdOwner; // save tokenId previous owner

    bytes4 private constant _ERC721_RECEIVED = 0x150b7a02;

    constructor(address _manager) public {
        manager = _manager;
    }

    function _onlyManager() internal {
        require(msg.sender == address(manager));
    }

    function _onlyStrategist() internal {
        require(
            msg.sender == address(strategist) ||
                msg.sender == address(strategist)
        );
    }

    function _onlyStrategy() internal {
        require(msg.sender == address(strategy));
    }

    function initialize(
        address _manager,
        address _strategy,
        GrailManagerConfig memory _config
    ) external initializer {
        setManagerInternal(_manager);
        setStrategyInternal(_strategy);

        want = IERC20(_config.want);
        lp = IERC20(_config.lp);
        grail = IERC20(_config.grail);
        xGrail = IXGrailToken(_config.xGrail);

        pool = INFTPool(_config.pool);
        router = ICamelotRouter(_config.router);
        yieldBooster = _config.yieldBooster;

        lp.approve(address(pool), uint256(-1));
        grail.approve(address(router), uint256(-1));
        xGrail.approveUsage(yieldBooster, uint256(-1));
    }

    function setStrategy(address _strategy) external {
        _onlyStrategist();
        setStrategyInternal(_strategy);
    }

    function balance() external view returns (uint256 _amount) {
        if (pool.balanceOf(address(this)) > 0) {
            (_amount, , , , , , , ) = pool.getStakingPosition(tokenId);
        } else {
            _amount = 0;
        }
    }

    function deposit(uint256 _amount) external {
        _onlyStrategy();
        lp.transferFrom(address(strategy), address(this), _amount);
        if (pool.balanceOf(address(this)) > 0) {
            pool.addToPosition(tokenId, _amount);
        } else {
            pool.createPosition(_amount, 0);

            uint256 balanceXGrail = balanceOfXGrail();
            if (balanceXGrail > 0) {
                _stakeXGrail(balanceXGrail);
            }
        }
    }

    function withdraw(uint256 _amount) external {
        _onlyStrategy();
        if (pool.balanceOf(address(this)) > 0) {
            pool.withdrawFromPosition(tokenId, _amount);

            _swapGrailToWant(balanceOfGrail());
        }

        if (tokenId != uint256(0)) {
            _stakeXGrail(balanceOfXGrail());
        }

        lp.transfer(address(strategy), _amount);
    }

    function harvest() external {
        _onlyStrategy();
        // harvest grail rewards
        if (pool.balanceOf(address(this)) > 0) {
            pool.harvestPosition(tokenId);
            _swapGrailToWant(balanceOfGrail());
            _stakeXGrail(balanceOfXGrail());
        }
    }

    function stakeXGrail(uint256 _amount) external {
        _onlyStrategy();
        _stakeXGrail(_amount);
    }

    function _stakeXGrail(uint256 _amount) internal {
        bytes memory usageData = abi.encode(address(pool), tokenId);
        uint256 _minAmount = 1000;
        if (_amount > _minAmount) {
            xGrail.allocate(yieldBooster, _amount, usageData);
        }
    }

    function _swapGrailToWant(uint256 _amountGrail) internal {
        address[] memory _path = new address[](2);

        _path[0] = address(grail);
        _path[1] = address(want);

        uint256 minGrailSwapAmount = 10000000000;

        if (_amountGrail > minGrailSwapAmount){
            router.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                _amountGrail,
                0,
                _path,
                address(strategy),
                address(strategy),
                now
            );
        }

    }

    // need to get the pending Grail rewards
    // xGrail cannot be liquidated
    function getPendingRewards() public view returns (uint256, uint256) {
        uint256 pending = pool.pendingRewards(tokenId);

        uint256 xGrailRewards =
            pending.mul(pool.xGrailRewardsShare()).div(_TOTAL_REWARDS_SHARES);
        uint256 grailRewards = pending.sub(xGrailRewards);

        return (xGrailRewards, grailRewards);
    }

    function balanceOfWant() public view returns (uint256) {
        return (want.balanceOf(address(this)));
    }

    function balanceOfGrail() public view returns (uint256) {
        return (grail.balanceOf(address(this)));
    }

    function balanceOfXGrail() public view returns (uint256) {
        return (xGrail.balanceOf(address(this)));
    }

    function setStrategyInternal(address _strategy) internal {
        strategy = CoreStrategyAPI(_strategy);
        strategist = strategy.strategist();
    }

    function setManagerInternal(address _manager) internal {
        manager = _manager;
    }

    function approveUsage(address _usage) external {
        _onlyManager();
        xGrail.approveUsage(_usage, uint256(-1));
    }

    function setYieldBooster(address _yieldBooster) external {
        _onlyManager();
        yieldBooster = _yieldBooster;
    }

    function onERC721Received(
        address, /*operator*/
        address _from,
        uint256 _tokenId,
        bytes calldata /*data*/
    ) external override returns (bytes4) {
        require(msg.sender == address(pool), "NFTHandler: unexpected nft");
        // save tokenId previous owner
        tokenId = _tokenId;
        pool.approve(_from, _tokenId);
        return _ERC721_RECEIVED;
    }

    function onNFTHarvest(
        address _operator,
        address _to,
        uint256, /*tokenId*/
        uint256, /*grailAmount*/
        uint256 /*xGrailAmount*/
    ) external override returns (bool) {
        require(
            _operator == address(this),
            "NFTHandler: caller is not the nft previous owner"
        );
        // if(_to == address(this)){
        //     return false; // user must call xGrailToken.harvestPositionTo as xGrail is not transferable
        // }
        return true;
    }

    function onNFTAddToPosition(
        address _operator,
        uint256, /*tokenId*/
        uint256 /*lpAmount*/
    ) external override returns (bool) {
        require(
            _operator == address(this),
            "NFTHandler: caller is not the nft previous owner"
        );
        return true;
    }

    function onNFTWithdraw(
        address _operator,
        uint256 _tokenId,
        uint256 /*lpAmount*/
    ) external override returns (bool) {
        require(
            _operator == address(this),
            "NFTHandler: caller is not the nft previous owner"
        );
        if (!pool.exists(_tokenId)) {
            tokenId = uint256(0);
        }
        return true;
    }
}
