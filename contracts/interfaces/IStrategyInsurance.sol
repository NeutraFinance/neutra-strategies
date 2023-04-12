// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.8.15;

interface IStrategyInsurance {
    function reportProfit(uint256 _totalDebt, uint256 _profit)
        external
        returns (uint256 _payment, uint256 _compensation);

    function reportLoss(uint256 _totalDebt, uint256 _loss)
        external
        returns (uint256 _compensation);

    function migrateInsurance(address newInsurance) external;
}
