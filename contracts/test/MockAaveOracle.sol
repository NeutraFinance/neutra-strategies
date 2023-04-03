// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.6.0 <0.7.0;
pragma experimental ABIEncoderV2;

import "../interfaces/aave/IAaveOracle.sol";

contract MockAaveOracle {
    bool public constant isPriceOracle = true;
    mapping(address => uint256) public prices;
    IAaveOracle oldOracle;

    constructor(address _oldOracle) public {
        oldOracle = IAaveOracle(_oldOracle);
    }

    function getAssetPrice(address token) external view returns (uint256) {
        if (prices[token] == 0) {
            return oldOracle.getAssetPrice(token);
        }
        return prices[token];
    }

    function setAssetPrice(address token, uint256 price) external {
        prices[token] = price;
    }
}
