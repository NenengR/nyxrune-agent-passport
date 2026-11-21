"""No signing, keys, wallet login or transaction submission. Python stdlib only."""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

EVENTS = ("CheckIn", "BadgeMinted", "Voted", "PollCreated")
METRICS = {"CheckIn": "check_ins", "BadgeMinted": "badges", "Voted": "votes", "PollCreated": "polls"}
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
WORD = re.compile(r"0x[0-9a-fA-F]{64}\Z")
BASE = Path(__file__).resolve().parent.parent


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def validate_config(config):
    address = config.get("contract_address", "")
    if not isinstance(address, str) or not ADDRESS.fullmatch(address) or int(address, 16) == 0:
        raise ValueError("contract_address is CONTRACT_ADDRESS_TBD or invalid; wait for HAMID's verified address")
    integer(config.get("chain_id"), "chain_id", 1)
    integer(config.get("deployment_block"), "deployment_block")
    integer(config.get("confirmations"), "confirmations", 1)
    integer(config.get("block_chunk_size"), "block_chunk_size", 1)
    if config.get("event_schema_verified") is not True:
        raise ValueError("event_schema_verified must be true only after checking Garing's final ABI")
    schemas = config.get("events", {})
    topics = []
    for name in EVENTS:
        schema = schemas.get(name, {})
        topic = schema.get("topic0", "")
        if not isinstance(topic, str) or not WORD.fullmatch(topic):
            raise ValueError(f"{name}.topic0 must be the exact 32-byte event signature hash from the final ABI")
        topics.append(topic.lower())
        if name != "PollCreated":
            wallet = schema.get("wallet")
            if not isinstance(wallet, dict) or wallet.get("source") not in ("topics", "data"):
                raise ValueError(f"{name}.wallet needs source topics/data and a zero-based word index from the final ABI")
            integer(wallet.get("index"), f"{name}.wallet.index", 1 if wallet["source"] == "topics" else 0)
    if len(set(topics)) != len(EVENTS):
        raise ValueError("event topic0 values must be distinct")


class Rpc:
    ALLOWED = {"eth_chainId", "eth_blockNumber", "eth_getLogs", "eth_getBlockByNumber", "eth_getCode"}

    def __init__(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("RPC_URL must be an HTTP(S) read-only endpoint without embedded login")
        self.url = url
        self.request_id = 0

    def call(self, method, params):
        if method not in self.ALLOWED:
            raise ValueError("RPC method is not read-only/allowed")
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        request = Request(self.url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read(16 * 1024 * 1024 + 1)
        except (URLError, TimeoutError, OSError) as exc:
            # Do not expose URLs or credentials from provider errors.
            raise ValueError(f"RPC transport failed ({type(exc).__name__}); check endpoint/network") from None
        if len(body) > 16 * 1024 * 1024:
            raise ValueError("RPC response exceeds 16 MiB; reduce block_chunk_size")
        result = json.loads(body)
        if result.get("id") != self.request_id or "error" in result or "result" not in result:
            raise ValueError("RPC returned an error or invalid response; check provider limits and reduce block_chunk_size")
        return result["result"]


def decode_wallet(log, mapping):
    if mapping["source"] == "topics":
        words = log["topics"]
    else:
        data = log.get("data", "")
        if not isinstance(data, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{64})*", data):
            raise ValueError("Malformed event data")
        words = ["0x" + data[i:i + 64] for i in range(2, len(data), 64)]
    try:
        word = words[mapping["index"]]
    except IndexError:
        raise ValueError("Wallet word missing; check final ABI mapping") from None
    if not WORD.fullmatch(word) or int(word[2:26], 16) != 0 or int(word[26:], 16) == 0:
        raise ValueError("Invalid ABI address word")
    return "0x" + word[-40:].lower()


def collect(rpc, config):
    validate_config(config)
    if int(rpc.call("eth_chainId", []), 16) != config["chain_id"]:
        raise ValueError("RPC chain ID does not match config")
    start = config["deployment_block"]
    latest = int(rpc.call("eth_blockNumber", []), 16)
    end = latest - config["confirmations"]
    if end < start:
        raise ValueError("Deployment block has not reached configured confirmation depth")
    anchor = rpc.call("eth_getBlockByNumber", [hex(end), False])
    if not anchor or not anchor.get("hash"):
        raise ValueError("Confirmed head unavailable")
    code = rpc.call("eth_getCode", [config["contract_address"], hex(end)])
    if code in ("0x", "0x0", None):
        raise ValueError("No contract bytecode at configured address/confirmed block")
    topics = {schema["topic0"].lower(): name for name, schema in config["events"].items() if name in EVENTS}
    timestamps = {}
    events = []
    size = config["block_chunk_size"]
    for lower in range(start, end + 1, size):
        upper = min(lower + size - 1, end)
        logs = rpc.call("eth_getLogs", [{"address": config["contract_address"], "fromBlock": hex(lower),
                                       "toBlock": hex(upper), "topics": [list(topics)]}])
        if not isinstance(logs, list):
            raise ValueError("RPC logs must be an array")
        for log in logs:
            if log.get("removed"):
                raise ValueError("Removed log encountered; rerun after chain settles")
            if log.get("address", "").lower() != config["contract_address"].lower():
                raise ValueError("RPC log address mismatch")
            topic = log.get("topics", [""])[0].lower()
            if topic not in topics:
                raise ValueError("RPC returned an unexpected event topic")
            number = int(log["blockNumber"], 16)
            if not lower <= number <= upper:
                raise ValueError("RPC log outside requested block range")
            if number not in timestamps:
                block = rpc.call("eth_getBlockByNumber", [hex(number), False])
                if not block or not block.get("hash"):
                    raise ValueError("Event block unavailable")
                timestamps[number] = (int(block["timestamp"], 16), block["hash"])
            timestamp, block_hash = timestamps[number]
            if log.get("blockHash") != block_hash:
                raise ValueError("Event block hash mismatch; rerun after chain settles")
            name = topics[topic]
            event = {"id": f"{number}:{int(log['transactionIndex'], 16)}:{int(log['logIndex'], 16)}",
                     "event": name, "timestamp": timestamp}
            if name != "PollCreated":
                event["wallet"] = decode_wallet(log, config["events"][name]["wallet"])
            events.append(event)
    final_anchor = rpc.call("eth_getBlockByNumber", [hex(end), False])
    if not final_anchor or final_anchor.get("hash") != anchor["hash"]:
        raise ValueError("Confirmed head changed during scan; output not published, rerun")
    return events, {"chain_id": config["chain_id"], "from_block": start, "to_block": end,
                    "confirmations": config["confirmations"], "confirmed_block_hash": anchor["hash"]}


def aggregate(events, source, contract_address="0xd3a3e3a726881d2eed7e6e49331af16a7de52392", scan=None):
    totals = {"unique_active_agent_addresses": 0, **{metric: 0 for metric in METRICS.values()}}
    days, seen, wallets = {}, {}, set()
    for event in events:
        name = event.get("event")
        if name not in EVENTS:
            raise ValueError(f"Unknown event: {name}")
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Event id is required for deduplication")
        integer(event.get("timestamp"), "event.timestamp")
        wallet = event.get("wallet") if name != "PollCreated" else None
        if name != "PollCreated" and (not isinstance(wallet, str) or not ADDRESS.fullmatch(wallet) or int(wallet, 16) == 0):
            raise ValueError("Activity event wallet is invalid")
        wallet = wallet.lower() if wallet else None
        normalized = (name, wallet, event["timestamp"])
        if event_id in seen:
            if seen[event_id] != normalized:
                raise ValueError("Conflicting duplicate event id")
            continue
        seen[event_id] = normalized
        day = datetime.fromtimestamp(event["timestamp"], timezone.utc).date().isoformat()
        bucket = days.setdefault(day, {**{metric: 0 for metric in METRICS.values()}, "wallets": set()})
        metric = METRICS[name]
        totals[metric] += 1
        bucket[metric] += 1
        if wallet:
            wallets.add(wallet)
            bucket["wallets"].add(wallet)
    totals["unique_active_agent_addresses"] = len(wallets)
    daily = []
    for day, bucket in sorted(days.items()):
        unique = len(bucket.pop("wallets"))
        daily.append({"day": day, "unique_active_agent_addresses": unique, **bucket})
    return {"schema_version": 1, "source": source, "is_fixture": source == "local-fixture",
            "status": "LOCAL FIXTURE — NOT LIVE" if source == "local-fixture" else "READ-ONLY RPC SNAPSHOT",
            "contract_address": contract_address, "generated_at": datetime.now(timezone.utc).isoformat(),
            "scan": scan, "totals": totals, "daily": daily,
            "metric_note": "Alamat unik yang aktif pada event Passport; bukan jumlah seluruh pemegang Agent ID atau identitas unik. Hari tanpa event tidak ditampilkan."}


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", action="store_true", help="Explicit synthetic local sample, no RPC")
    mode.add_argument("--rpc", action="store_true", help="Read only, requires verified config and RPC_URL")
    parser.add_argument("--config", type=Path, default=BASE / "config/indexer.local.json")
    parser.add_argument("--output", type=Path, default=BASE / "public/data/stats.json")
    args = parser.parse_args()
    try:
        if args.fixture:
            events = json.loads((BASE / "fixtures/events.json").read_text())
            stats = aggregate(events, "local-fixture")
        else:
            config = json.loads(args.config.read_text())
            validate_config(config)  # Fail closed BEFORE any network call.
            rpc = Rpc(os.environ.get("RPC_URL", ""))
            events, scan = collect(rpc, config)
            stats = aggregate(events, "rpc", config["contract_address"], scan)
        atomic_write(args.output, stats)
    except (ValueError, OSError, KeyError, TypeError, IndexError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {args.output}: {stats['status']}; totals={json.dumps(stats['totals'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
