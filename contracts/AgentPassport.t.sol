// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AgentPassport} from "./AgentPassport.sol";

interface Vm {
    function etch(address target, bytes calldata code) external;
    function warp(uint256 timestamp) external;
    function prank(address sender) external;
    function expectRevert(bytes4 selector) external;
}

contract MockAgentID {
    mapping(address => uint256) public balanceOf;

    function setBalance(address account, uint256 amount) external {
        balanceOf[account] = amount;
    }
}

contract AgentPassportTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address private constant HOLDER = address(0xA11CE);
    address private constant NON_HOLDER = address(0xB0B);
    uint256 private constant DAY = 20_000;
    AgentPassport private passport;

    function setUp() public {
        passport = new AgentPassport(address(this));
        MockAgentID mock = new MockAgentID();
        address gate = address(passport.AGENT_ID());
        vm.etch(gate, address(mock).code);
        MockAgentID(gate).setBalance(HOLDER, 1);
        vm.warp(DAY * 1 days + 1 days - 1);
    }

    function testConstructorZeroOwnerReverts() public {
        vm.expectRevert(AgentPassport.ZeroOwner.selector);
        new AgentPassport(address(0));
    }

    function testCheckInTwiceSameUtcDayReverts() public {
        vm.prank(HOLDER);
        passport.checkIn();
        vm.expectRevert(AgentPassport.AlreadyCheckedInToday.selector);
        vm.prank(HOLDER);
        passport.checkIn();
    }

    function testCheckInNextUtcDayIncrementsStreak() public {
        vm.prank(HOLDER);
        passport.checkIn();
        vm.warp((DAY + 1) * 1 days);
        vm.prank(HOLDER);
        passport.checkIn();
        (uint256 day, uint256 total, uint256 streak) = passport.getCheckIn(HOLDER);
        require(day == DAY + 1 && total == 2 && streak == 2, "Incorrect check-in stats");
    }

    function testFirstCheckInOnDayZero() public {
        vm.warp(0);
        vm.prank(HOLDER);
        passport.checkIn();
        (uint256 day, uint256 total, uint256 streak) = passport.getCheckIn(HOLDER);
        require(day == 0 && total == 1 && streak == 1, "Incorrect first check-in");
    }

    function testMintBadgeTwiceReverts() public {
        vm.prank(HOLDER);
        passport.mintBadge();
        vm.expectRevert(AgentPassport.AlreadyMinted.selector);
        vm.prank(HOLDER);
        passport.mintBadge();
    }

    function testMintBadgeIsSoulbound() public {
        vm.prank(HOLDER);
        passport.mintBadge();
        (bool minted, uint256 tokenId) = passport.getBadge(HOLDER);
        require(minted && passport.ownerOf(tokenId) == HOLDER, "Badge not issued");
        vm.expectRevert(AgentPassport.Soulbound.selector);
        vm.prank(HOLDER);
        passport.transferFrom(HOLDER, NON_HOLDER, tokenId);
        vm.expectRevert(AgentPassport.Soulbound.selector);
        vm.prank(HOLDER);
        passport.safeTransferFrom(HOLDER, NON_HOLDER, tokenId);
        vm.expectRevert(AgentPassport.Soulbound.selector);
        vm.prank(HOLDER);
        passport.approve(NON_HOLDER, tokenId);
        vm.expectRevert(AgentPassport.Soulbound.selector);
        vm.prank(HOLDER);
        passport.setApprovalForAll(NON_HOLDER, true);
    }

    function testVoteTwiceInSamePollReverts() public {
        uint256 pollId = createPoll();
        vm.prank(HOLDER);
        passport.vote(pollId, 0);
        (,,, uint256[] memory counts) = passport.getPoll(pollId);
        require(passport.hasVoted(pollId, HOLDER) && counts[0] == 1, "Vote not recorded");
        vm.expectRevert(AgentPassport.AlreadyVoted.selector);
        vm.prank(HOLDER);
        passport.vote(pollId, 1);
    }

    function testVoteWithoutAgentIdReverts() public {
        uint256 pollId = createPoll();
        vm.expectRevert(AgentPassport.NotAgentHolder.selector);
        vm.prank(NON_HOLDER);
        passport.vote(pollId, 0);
    }

    function testOnlyOwnerCanCreatePoll() public {
        vm.expectRevert(AgentPassport.NotOwner.selector);
        vm.prank(HOLDER);
        passport.createPoll("Next topic?", options(), 1 hours);
        require(createPoll() == 1, "Owner could not create first poll");
    }

    function createPoll() private returns (uint256) {
        return passport.createPoll("Next topic?", options(), 1 hours);
    }

    function options() private pure returns (string[] memory choices) {
        choices = new string[](2);
        choices[0] = "A";
        choices[1] = "B";
    }
}
