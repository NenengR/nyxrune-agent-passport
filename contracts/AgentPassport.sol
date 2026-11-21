// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

interface IAgentID {
    function balanceOf(address owner) external view returns (uint256);
}

/// @title NyxRune Agent Passport
/// @notice Check-in harian, badge soulbound gratis, dan vote mingguan.
/// @notice Semua fungsi utama hanya untuk pemegang Agent ID.
/// @notice Gerbang memakai balanceOf di kontrak SPACE ID Agent ID.
/// @notice Kontrak ini tidak menyimpan dana user, tidak ada withdraw, tidak ada fee.
contract AgentPassport is ERC721 {
    IAgentID public constant AGENT_ID =
        IAgentID(0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F);

    address public immutable owner;

    uint256 public nextTokenId = 1;
    uint256 public nextPollId = 1;

    mapping(address => uint256) public lastCheckInDay;
    mapping(address => uint256) public totalCheckIns;
    mapping(address => uint256) public streak;
    mapping(address => bool) public badgeMinted;
    mapping(address => uint256) public badgeTokenId;

    struct Poll {
        string question;
        string[] options;
        uint256 deadline;
        uint256[] voteCounts;
        bool exists;
    }

    mapping(uint256 => Poll) public polls;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event CheckIn(address indexed user, uint256 day, uint256 streak, uint256 totalCheckIns);
    event BadgeMinted(address indexed user, uint256 tokenId);
    event PollCreated(uint256 indexed pollId, string question, uint256 deadline);
    event Voted(uint256 indexed pollId, address indexed user, uint256 optionIndex);

    error NotAgentHolder();
    error AlreadyCheckedInToday();
    error AlreadyMinted();
    error PollNotFound();
    error PollEnded();
    error InvalidOption();
    error AlreadyVoted();
    error InvalidPollParams();

    error NotOwner();
    error ZeroOwner();
    error Soulbound();

    constructor(address initialOwner) ERC721("NyxRune Agent Passport Badge", "NXPASS") {
        if (initialOwner == address(0)) revert ZeroOwner();
        owner = initialOwner;
    }

    modifier onlyAgentHolder() {
        if (AGENT_ID.balanceOf(msg.sender) == 0) revert NotAgentHolder();
        _;
    }

    function isAgentHolder(address user) public view returns (bool) {
        return AGENT_ID.balanceOf(user) > 0;
    }

    function checkIn() external onlyAgentHolder {
        uint256 day = block.timestamp / 86400;
        if (totalCheckIns[msg.sender] != 0 && lastCheckInDay[msg.sender] == day) revert AlreadyCheckedInToday();
        if (lastCheckInDay[msg.sender] + 1 == day) {
            streak[msg.sender] += 1;
        } else {
            streak[msg.sender] = 1;
        }
        lastCheckInDay[msg.sender] = day;
        totalCheckIns[msg.sender] += 1;
        emit CheckIn(msg.sender, day, streak[msg.sender], totalCheckIns[msg.sender]);
    }

    function mintBadge() external onlyAgentHolder {
        if (badgeMinted[msg.sender]) revert AlreadyMinted();
        uint256 tokenId = nextTokenId;
        nextTokenId += 1;
        badgeMinted[msg.sender] = true;
        badgeTokenId[msg.sender] = tokenId;
        _safeMint(msg.sender, tokenId);
        emit BadgeMinted(msg.sender, tokenId);
    }

    function createPoll(
        string calldata question,
        string[] calldata options,
        uint256 durationSeconds
    ) external returns (uint256 pollId) {
        if (msg.sender != owner) revert NotOwner();
        if (options.length < 2 || options.length > 6) revert InvalidPollParams();
        if (bytes(question).length == 0 || bytes(question).length > 200) revert InvalidPollParams();
        if (durationSeconds < 3600 || durationSeconds > 604800) revert InvalidPollParams();
        pollId = nextPollId;
        nextPollId += 1;
        Poll storage poll = polls[pollId];
        poll.question = question;
        poll.deadline = block.timestamp + durationSeconds;
        poll.exists = true;
        for (uint256 i = 0; i < options.length; i++) {
            if (bytes(options[i]).length == 0 || bytes(options[i]).length > 80) revert InvalidPollParams();
            poll.options.push(options[i]);
            poll.voteCounts.push(0);
        }
        emit PollCreated(pollId, question, poll.deadline);
    }

    function vote(uint256 pollId, uint256 optionIndex) external onlyAgentHolder {
        Poll storage poll = polls[pollId];
        if (!poll.exists) revert PollNotFound();
        if (block.timestamp > poll.deadline) revert PollEnded();
        if (optionIndex >= poll.options.length) revert InvalidOption();
        if (hasVoted[pollId][msg.sender]) revert AlreadyVoted();
        hasVoted[pollId][msg.sender] = true;
        poll.voteCounts[optionIndex] += 1;
        emit Voted(pollId, msg.sender, optionIndex);
    }

    function getCheckIn(address user) external view returns (uint256, uint256, uint256) {
        return (lastCheckInDay[user], totalCheckIns[user], streak[user]);
    }

    function getPoll(uint256 pollId)
        external
        view
        returns (string memory, string[] memory, uint256, uint256[] memory)
    {
        Poll storage poll = polls[pollId];
        return (poll.question, poll.options, poll.deadline, poll.voteCounts);
    }

    function getBadge(address user) external view returns (bool, uint256) {
        return (badgeMinted[user], badgeTokenId[user]);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        string memory id = Strings.toString(tokenId);
        return string.concat(
            "data:application/json;base64,",
            Base64.encode(abi.encodePacked(
                '{"name":"NyxRune Agent Passport Badge #', id,
                '","description":"Soulbound badge for an Agent ID holder.","tokenId":', id, '}'
            ))
        );
    }

    function approve(address, uint256) public pure override {
        revert Soulbound();
    }

    function setApprovalForAll(address, bool) public pure override {
        revert Soulbound();
    }

    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        if (_ownerOf(tokenId) != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }
}
