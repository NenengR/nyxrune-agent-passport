import { config } from "./config.js";

const wallet = window.ethereum;
const ui = Object.fromEntries(
  ["connect", "refresh", "wallet", "gate", "status", "activity", "badge", "poll",
    "options", "checkIn", "mintBadge", "vote", "copyPrompt", "agent-prompt"].map(id => [id, document.getElementById(id)])
);
const selectors = {
  balanceOf: "70a08231", getCheckIn: "0786e6e4", getBadge: "c254de88",
  getPoll: "1a8cbcaa", hasVoted: "43859632", checkIn: "183ff085",
  mintBadge: "da1b3cb0", vote: "b384abef",
};
const isAddress = value => /^0x[0-9a-f]{40}$/i.test(value ?? "") && !/^0x0{40}$/i.test(value);
const word = n => BigInt(n).toString(16).padStart(64, "0");
const dataFor = (method, ...args) => "0x" + selectors[method] + args.map(word).join("");
const request = (method, params = []) => wallet.request({ method, params });
const read = (to, method, ...args) => request("eth_call", [{ to, data: dataFor(method, ...args) }, "latest"]);
const show = message => { ui.status.textContent = message; };
const messageFor = error => Number(error?.code) === 4001
  ? "Request rejected in wallet." : (error?.message || "Wallet request failed.");

let ready;
let busy = false;
let revision = 0;

function reset() {
  ready = undefined;
  for (const key of ["checkIn", "mintBadge", "vote", "options"]) ui[key].disabled = true;
  ui.options.replaceChildren();
  ui.activity.textContent = "Days are counted in UTC.";
  ui.badge.textContent = "One badge per wallet. Badges cannot be transferred.";
  ui.poll.textContent = "Poll not loaded yet.";
}

async function identity(method = "eth_accounts") {
  const [account] = await request(method);
  const chain = BigInt(await request("eth_chainId"));
  return { account, chain };
}

function uintAt(data, byteOffset) {
  const start = 2 + byteOffset * 2;
  const hex = data.slice(start, start + 64);
  if (!Number.isSafeInteger(start) || !/^[0-9a-f]{64}$/i.test(hex)) {
    throw new Error("Invalid contract response.");
  }
  return BigInt("0x" + hex);
}

function decodePoll(data) {
  const uint = offset => uintAt(data, offset);
  const stringAt = offset => {
    const length = Number(uint(offset));
    const start = 2 + (offset + 32) * 2;
    const bytes = data.slice(start, start + length * 2);
    if (length > 200 || bytes.length !== length * 2 || !/^[0-9a-f]*$/i.test(bytes)) {
      throw new Error("Invalid poll text.");
    }
    return new TextDecoder().decode(Uint8Array.from(bytes.match(/../g) ?? [], b => parseInt(b, 16)));
  };
  const optionsOffset = Number(uint(32));
  const length = Number(uint(optionsOffset));
  if (length > 6) throw new Error("Invalid poll options.");
  const head = optionsOffset + 32;
  const options = Array.from({ length }, (_, index) => stringAt(head + Number(uint(head + index * 32))));
  return { question: stringAt(Number(uint(0))), options, deadline: uint(64) };
}

function buildAgentPrompt(poll) {
  const options = poll.options.map((option, index) => `${index} ${option}`).join(", ");
  return `Use my Binance Agentic Wallet (baw) on BNB Smart Chain (chain ${config.chainId}) to interact with the NyxRune Agent Passport contract at ${config.passport}.\n\nDo these three things, one at a time, each with a fresh preview first and only after my confirmation:\n1. checkIn() once per UTC day.\n2. mintBadge() once to claim my soulbound badge.\n3. Vote on poll ${config.pollId}, "${poll.question}": ${options}. I choose option N (replace N with the option number you want).\n\nAll calls are free except gas. Do not sign or send anything else.`;
}

async function copyPrompt() {
  const text = ui["agent-prompt"].textContent;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  ui.copyPrompt.textContent = "Copied";
  setTimeout(() => { ui.copyPrompt.textContent = "Copy prompt"; }, 2000);
}
ui.copyPrompt.addEventListener("click", copyPrompt);

async function refresh() {
  const current = ++revision;
  reset();
  ui.gate.textContent = "Agent ID not checked yet";
  if (!wallet?.request) {
    show("Open this page in a browser with a wallet installed.");
    return;
  }
  try {
    const { account, chain } = await identity();
    if (current !== revision) return;
    ui.wallet.textContent = isAddress(account) ? account : "Wallet not connected";
    if (!isAddress(account)) return;
    if (chain !== BigInt(config.chainId)) {
      show("Switch your wallet to chain ID " + config.chainId + ".");
      return;
    }
    const balance = uintAt(await read(config.agentId, "balanceOf", account), 0);
    if (current !== revision) return;
    ui.gate.textContent = balance > 0n ? "Agent ID active" : "This wallet does not hold an Agent ID";
    if (!isAddress(config.passport)) {
      show("Passport contract address is not configured.");
      return;
    }

    const [activity, badge] = await Promise.all([
      read(config.passport, "getCheckIn", account), read(config.passport, "getBadge", account),
    ]);
    if (current !== revision) return;
    const day = uintAt(activity, 0);
    const total = uintAt(activity, 32);
    const streak = uintAt(activity, 64);
    const minted = uintAt(badge, 0) === 1n;
    const today = BigInt(Math.floor(Date.now() / 86_400_000));
    ui.activity.textContent = `${total} check-ins · streak ${streak} days · UTC`;
    if (minted) ui.badge.textContent = "Badge #" + uintAt(badge, 32) + " already minted.";
    const available = balance > 0n && !busy;
    ready = { account, chain };
    ui.checkIn.disabled = !available || (total > 0n && day === today);
    ui.mintBadge.disabled = !available || minted;

    const pollId = BigInt(config.pollId);
    if (pollId < 1n || pollId >= 2n ** 256n) throw new Error("Poll ID in the config is invalid.");
    const [pollData, voted] = await Promise.all([
      read(config.passport, "getPoll", pollId), read(config.passport, "hasVoted", pollId, account),
    ]);
    if (current !== revision) return;
    const poll = decodePoll(pollData);
    if (poll.options.length < 2) {
      ui.poll.textContent = "No poll exists for ID " + pollId + ".";
      return;
    }
    ui["agent-prompt"].textContent = buildAgentPrompt(poll);
    const ended = poll.deadline < BigInt(Math.floor(Date.now() / 1000));
    const alreadyVoted = uintAt(voted, 0) === 1n;
    ui.poll.textContent = poll.question
      + (alreadyVoted ? " · Vote already recorded." : ended ? " · Poll closed." : "");
    ui.options.replaceChildren(...poll.options.map((option, index) => {
      const element = document.createElement("option");
      element.value = String(index);
      element.textContent = option;
      return element;
    }));
    ui.vote.disabled = ui.options.disabled = !available || ended || alreadyVoted;
  } catch (error) {
    if (current === revision) show(messageFor(error));
  }
}

async function send(method, ...args) {
  if (busy || !ready || ui[method].disabled) return;
  const expected = ready;
  const current = ++revision;
  busy = true;
  for (const key of ["checkIn", "mintBadge", "vote", "options", "connect", "refresh"]) ui[key].disabled = true;
  try {
    const { account, chain } = await identity();
    if (current !== revision || account?.toLowerCase() !== expected.account.toLowerCase() || chain !== expected.chain) {
      throw new Error("Wallet or network changed. Check the status and try again.");
    }
    show("Review and confirm the transaction in your wallet.");
    const hash = await request("eth_sendTransaction", [{
      from: account, to: config.passport, data: dataFor(method, ...args), value: "0x0",
    }]);
    show("Transaction sent: " + hash + ". Refresh the status after the transaction is confirmed.");
  } catch (error) {
    show(messageFor(error));
  } finally {
    busy = false;
    ui.connect.disabled = ui.refresh.disabled = false;
    await refresh();
  }
}

ui.connect.disabled = ui.refresh.disabled = !wallet?.request;
ui.connect.addEventListener("click", async () => {
  ui.connect.disabled = true;
  show("");
  try {
    await request("eth_requestAccounts");
    await refresh();
  } catch (error) {
    show(messageFor(error));
  } finally {
    ui.connect.disabled = false;
  }
});
function onChange() {
  if (!busy) show("");
  void refresh();
}
ui.refresh.addEventListener("click", onChange);
wallet?.on?.("accountsChanged", onChange);
wallet?.on?.("chainChanged", onChange);
ui.checkIn.addEventListener("click", () => send("checkIn"));
ui.mintBadge.addEventListener("click", () => send("mintBadge"));
ui.vote.addEventListener("click", () => send("vote", config.pollId, ui.options.value));
// No auto-connect on page load: the wallet is only touched after the user
// clicks Connect or Refresh, so installed extensions (OKX, Phantom, and
// others) never pop up a connect prompt on refresh.
async function loadStats() {
  try {
    const response = await fetch("./data/stats.json?v=" + Date.now(), { cache: "no-store" });
    if (!response.ok) return;
    const stats = await response.json();
    const set = (id, value) => {
      const element = document.getElementById(id);
      if (element && Number.isFinite(Number(value))) element.textContent = String(value);
    };
    set("stat-addresses", stats.unique_addresses);
    set("stat-checkins", stats.checkins);
    set("stat-badges", stats.badges);
    set("stat-votes", stats.votes);
    set("stat-polls", stats.polls);
    if (stats.label) {
      const note = document.getElementById("stats-note");
      if (note) note.textContent = stats.label + ".";
    }
    if (Number.isFinite(Number(stats.unique_addresses))) {
      const count = Number(stats.unique_addresses);
      const fill = document.getElementById("target-fill");
      const label = document.getElementById("target-label");
      if (fill) fill.style.width = Math.min(100, (count / 30) * 100) + "%";
      if (label) label.textContent = count + " of 30 target Agent ID addresses";
    }
  } catch {
    // The static numbers in the HTML stay visible if the stats file cannot be loaded.
  }
}
void loadStats();
