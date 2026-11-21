# NyxRune Agent Passport

Activity passport for Binance Agent ID holders on BNB Smart Chain: daily check-in, one soulbound badge per wallet, and a weekly vote. Every feature is gated by holding a Binance Agent ID, checked on chain with `balanceOf` greater than 0.

## Live contract

- Chain: BNB Smart Chain (chain ID 56)
- Contract: `0xd3a3e3a726881d2eed7e6e49331af16a7de52392`
- BscScan: https://bscscan.com/address/0xd3a3e3a726881d2eed7e6e49331af16a7de52392
- Deploy transaction: `0x265cc99781b91269095556ba08ad044798127b6946ac1001a6ea151f4669eca0`, block 134878272
- Source verification: Sourcify exact match
- Badge: NyxRune Agent Passport Badge (NXPASS), ERC721 soulbound, one per wallet, non-transferable

Live state: poll 1 is open, check-in, badge mint, and vote have all been tested on chain from the deployer wallet.

## What it does

- `checkIn()`: once per UTC day, tracks day, total check-ins, and streak.
- `mintBadge()`: mints badge token ID 1 per wallet, once, soulbound. Transfers and approvals revert.
- `createPoll(question, options, duration)`: owner only, 2 to 6 options, duration 1 hour to 7 days.
- `vote(pollId, optionIndex)`: once per wallet per poll, Agent ID holders only.

The owner can only create polls. There is no withdraw, no fee, no pause, no upgrade, no mint for other wallets, and no reset of other users.

## Repository layout

- `contracts/`: `AgentPassport.sol` and its Foundry test `AgentPassport.t.sol`
- `frontend/`: static web app (`index.html`, `app.js`, `config.js`, `style.css`)
- `indexer/`: read-only event indexer, public statistics page, tests, and demo storyboard
- `foundry.toml`: Foundry configuration

## Contract: build and test

Requirements: Foundry.

```bash
forge install openzeppelin/openzeppelin-contracts@v5.0.2
forge build
forge test
```

OpenZeppelin is not vendored in this repo; install it with the command above. The contract uses solc 0.8.24 and optimizer runs 200. Tests: 9 pass, 0 fail, including a zero owner constructor check.

## Frontend: run locally

Requirements: a browser with a wallet extension, on BNB Smart Chain (chain ID 56), holding a Binance Agent ID.

```bash
python3 -m http.server 8000 --directory frontend
```

Open `http://127.0.0.1:8000`, connect the wallet, and confirm each transaction in the wallet. The app reads the Agent ID balance on chain and only enables actions for holders.

## Indexer: run locally

Requirements: Python 3.10 or newer, no external dependencies. Node.js is only needed for the optional JavaScript tests.

```bash
cd indexer
python3 -m passport.indexer --fixture
python3 -m http.server 8000 --bind 127.0.0.1 --directory public
```

Open `http://127.0.0.1:8000` for the statistics page. For a live scan, set a public read-only RPC URL in the shell as `RPC_URL`, copy `config/indexer.example.json` to `config/indexer.local.json`, then run `python3 -m passport.indexer --rpc --config config/indexer.local.json`. The indexer only makes read-only RPC calls and never asks for a private key, seed phrase, API secret, or pairing code.

Indexer tests:

```bash
cd indexer
python3 -m unittest discover -s tests -v
node --check public/app.js
node tests/test_ui.cjs
```

## Statements

No token. No returns or rewards promised. No QR login. No unlimited approval. No collection of seed phrases, private keys, API secrets, or pairing codes. Users always confirm their own transactions in their own wallet.

## License

MIT. See `LICENSE`.
