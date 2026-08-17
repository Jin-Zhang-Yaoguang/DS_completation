const CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"];
const ANIMALS = ["GOOSE", "COW", "SHEEP"];
const PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"];
const ALL_ITEMS = [...new Set([...PRODUCTS, ...ANIMALS])];
const BASE_PRICE = {WHEAT:25,CARROT:35,TOMATO:60,STRAWBERRY:120,MELON:250,EGG:50,MILK:160,WOOL:200,FERTILIZER:100};
const EMOJI = {WHEAT:"🌾",CARROT:"🥕",TOMATO:"🍅",STRAWBERRY:"🍓",MELON:"🍈",GOOSE:"🪿",COW:"🐄",SHEEP:"🐑",EGG:"🥚",MILK:"🥛",WOOL:"🧶",FERTILIZER:"🟤"};
const LABEL = {WHEAT:"小麦",CARROT:"胡萝卜",TOMATO:"番茄",STRAWBERRY:"草莓",MELON:"甜瓜",GOOSE:"鹅",COW:"牛",SHEEP:"羊",EGG:"鸡蛋",MILK:"牛奶",WOOL:"羊毛",FERTILIZER:"肥料"};
const SHOP_LABEL = {BAKERY:"面包店",PIZZA_SHOP:"披萨店",BRUNCH_SPOT:"早午餐店",YARN_STORE:"羊毛店",ICE_CREAM_SHOP:"冰淇淋店",PET_CAFE:"宠物咖啡店",SMOOTHIE_SHOP:"果昔店",FARMERS_MARKET:"农贸市场"};

let state = null;
let selectedUnit = 0;
let unitDrafts = [];
let marketDraft = [];
let selectedCell = null;
let busy = false;

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function toast(message, isError = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = isError ? "show error" : "show";
  setTimeout(() => { el.className = ""; }, 2600);
}

function setBusy(value) {
  busy = value;
  document.body.classList.toggle("busy", value);
  $("submit-turn").disabled = value || state?.game.done;
}

function resetDrafts() {
  if (!state) return;
  const me = state.farms[state.game.humanPlayer];
  unitDrafts = [["PASS"], ...(me.hands || []).map(() => ["PASS"] )];
  selectedUnit = Math.min(selectedUnit, unitDrafts.length - 1);
  marketDraft = [];
  renderDrafts();
}

function unitName(index) { return index === 0 ? "主农民" : `临时工 ${index}`; }

function formatAction(action) {
  if (!action || !action.length) return "—";
  return action.map((value, index) => index === 1 && LABEL[value] ? LABEL[value] : value).join(" ");
}

function money(value) { return `$${Math.floor(Number(value || 0)).toLocaleString("zh-CN")}`; }

function renderBoard(target, farm, playerId, interactive) {
  target.innerHTML = "";
  const unitMap = new Map();
  const addUnit = (pos, text, cls) => {
    if (!pos) return;
    const key = `${pos[0]},${pos[1]}`;
    const values = unitMap.get(key) || [];
    values.push({text, cls}); unitMap.set(key, values);
  };
  addUnit(farm.farmer, "F", interactive ? "human" : "bot");
  (farm.hands || []).forEach((pos, i) => addUnit(pos, `H${i+1}`, interactive ? "human" : "bot"));
  (farm.tiles || []).forEach((row, y) => row.forEach((tile, x) => {
    const cell = document.createElement("button");
    cell.className = "farm-cell";
    cell.type = "button";
    let icon = ""; let meta = "";
    if (tile === "LOCKED") { cell.classList.add("locked"); icon = ""; }
    else if (tile === null) { cell.classList.add("empty"); }
    else if (tile.kind === "WEED") { cell.classList.add("weed"); icon = "🌿"; }
    else if (tile.kind === "PLANT") {
      cell.classList.add("plant"); icon = EMOJI[tile.crop] || "🌱";
      meta = tile.yield_units > 0 ? String(tile.yield_units) : tile.watered_today ? "💧" : "";
    } else if (tile.kind === "COOP" || tile.kind === "PASTURE") {
      cell.classList.add("structure"); icon = tile.animal ? (EMOJI[tile.animal] || "🐾") : (tile.kind === "COOP" ? "🪺" : "▱");
      meta = tile.yield_units > 0 ? String(tile.yield_units) : "";
    }
    cell.innerHTML = `<span class="tile-icon">${icon}</span>${meta ? `<span class="tile-meta">${meta}</span>` : ""}`;
    (unitMap.get(`${x},${y}`) || []).forEach(unit => {
      const badge = document.createElement("span"); badge.className = `unit-badge ${unit.cls}`; badge.textContent = unit.text; cell.appendChild(badge);
    });
    cell.title = `(${x}, ${y})`;
    cell.addEventListener("click", () => { selectedCell = {tile, x, y, farm, playerId, interactive}; renderCellDetail(); });
    target.appendChild(cell);
  }));
}

function renderCellDetail() {
  const el = $("cell-detail");
  if (!selectedCell) { el.className = "empty-state"; el.textContent = "选择一块地查看状态"; return; }
  const {tile, x, y, farm, interactive} = selectedCell;
  const units = [];
  if (farm.farmer?.[0] === x && farm.farmer?.[1] === y) units.push("主农民");
  (farm.hands || []).forEach((p, i) => { if (p[0] === x && p[1] === y) units.push(`临时工 ${i+1}`); });
  let lines = [`<strong>${interactive ? "你的" : "Bot 的"}格子 (${x}, ${y})</strong>`];
  if (tile === "LOCKED") lines.push("未解锁土地；可以通行，不能耕作");
  else if (tile === null) lines.push("空地");
  else if (tile.kind === "WEED") lines.push("杂草：使用 DIG 清除");
  else if (tile.kind === "PLANT") {
    lines.push(`${EMOJI[tile.crop] || "🌱"} ${LABEL[tile.crop] || tile.crop}`);
    lines.push(`种植日 ${Number(tile.planted_day)+1} · 可收获 ${tile.yield_units || 0}`);
    lines.push(`${tile.watered_today ? "今日已浇水" : "今日未浇水"} · 连续缺水 ${tile.consecutive_unwatered || 0}`);
    if ((tile.fertilized_until_day ?? -1) >= 0) lines.push(`施肥效果至第 ${Number(tile.fertilized_until_day)+1} 日`);
  } else if (tile.kind === "COOP" || tile.kind === "PASTURE") {
    lines.push(`${tile.kind === "COOP" ? "鸡舍" : "牧场"}${tile.animal ? ` · ${EMOJI[tile.animal]} ${LABEL[tile.animal]}` : " · 空"}`);
    if (tile.animal) lines.push(`产物 ${tile.yield_units || 0} · ${tile.fed_today ? "已喂食" : "未喂食"} · ${tile.cared_today ? "已照料" : "未照料"}`);
  }
  if (units.length) lines.push(`单位：${units.join("、")}`);
  el.className = "cell-detail"; el.innerHTML = lines.map((line, i) => i ? `<p>${line}</p>` : line).join("");
}

function renderDrafts() {
  if (!state) return;
  const tabs = $("unit-tabs"); tabs.innerHTML = "";
  unitDrafts.forEach((action, index) => {
    const button = document.createElement("button");
    button.className = index === selectedUnit ? "active" : "";
    button.innerHTML = `<strong>${unitName(index)}</strong><small>${formatAction(action)}</small>`;
    button.onclick = () => { selectedUnit = index; renderDrafts(); };
    tabs.appendChild(button);
  });
  $("unit-drafts").innerHTML = unitDrafts.map((a, i) => `<span><b>${unitName(i)}</b> ${formatAction(a)}</span>`).join("");
  const orders = $("market-orders"); orders.innerHTML = "";
  marketDraft.forEach((order, index) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${formatAction(order)}</span><button title="上移">↑</button><button title="下移">↓</button><button title="删除">×</button>`;
    const buttons = li.querySelectorAll("button");
    buttons[0].onclick = () => moveMarket(index, -1);
    buttons[1].onclick = () => moveMarket(index, 1);
    buttons[2].onclick = () => { marketDraft.splice(index, 1); renderDrafts(); };
    orders.appendChild(li);
  });
  if (!marketDraft.length) orders.innerHTML = '<li class="empty-state">尚未添加市场订单</li>';
}

function moveMarket(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= marketDraft.length) return;
  [marketDraft[index], marketDraft[target]] = [marketDraft[target], marketDraft[index]];
  renderDrafts();
}

function setUnitAction(action) {
  if (!unitDrafts.length) return;
  unitDrafts[selectedUnit] = action;
  renderDrafts();
}

function fillSelect(select, items) {
  select.innerHTML = items.map(item => `<option value="${item}">${EMOJI[item] || ""} ${LABEL[item] || item}</option>`).join("");
}

function updateMarketBuilder() {
  const op = $("market-op").value;
  let items = PRODUCTS;
  if (op === "BUY_SEED") items = CROPS;
  if (op === "BUY_ANIMAL") items = ANIMALS;
  if (op === "BUY_PRODUCT") items = ["WHEAT", "FERTILIZER"];
  fillSelect($("market-item"), items);
  const simple = op === "HIRE" || op === "BUY_LAND";
  $("market-item").disabled = simple;
  $("market-quantity").disabled = simple;
}

function renderStorage() {
  const privateState = state.private;
  const entries = obj => Object.entries(obj || {}).filter(([,v]) => Number(v) > 0);
  const itemChips = obj => entries(obj).length ? entries(obj).map(([k,v]) => `<span class="item-chip">${EMOJI[k] || "📦"} ${LABEL[k] || k}<b>${v}</b></span>`).join("") : '<span class="muted">空</span>';
  const shedCount = entries(privateState.shed).reduce((sum,[,v]) => sum + Number(v), 0);
  let html = `<section><h4>仓库 <small>${shedCount}/100</small></h4><div class="chips">${itemChips(privateState.shed)}</div></section>`;
  html += `<section><h4>种子</h4><div class="chips">${itemChips(privateState.seeds)}</div></section>`;
  (privateState.inventories || []).forEach((inv, i) => { html += `<section><h4>${unitName(i)}随身</h4><div class="chips">${itemChips(inv)}</div></section>`; });
  $("storage").innerHTML = html;
}

function renderMarket() {
  const prices = state.market.prices || {}, inventory = state.market.inventory || {};
  $("market-table").innerHTML = PRODUCTS.map(item => {
    const price = Number(prices[item] || 0), base = BASE_PRICE[item] || price;
    const cls = price > base ? "up" : price < base ? "down" : "";
    return `<tr><td>${EMOJI[item] || ""} ${LABEL[item]}</td><td class="${cls}">$${price}</td><td>${Number(inventory[item] || 0).toLocaleString("zh-CN")}</td></tr>`;
  }).join("");
}

function renderHistory() {
  const history = [...(state.history || [])].reverse();
  $("history").innerHTML = history.length ? history.map(row => `
    <article>
      <strong>第 ${row.step} 回合</strong>
      <p>你：${formatAction(row.human.farmer)}${row.human.market.length ? ` · 市场 ${row.human.market.map(formatAction).join(" / ")}` : ""}</p>
      <p>Bot：${formatAction(row.bot.farmer)}${row.bot.market.length ? ` · 市场 ${row.bot.market.map(formatAction).join(" / ")}` : ""}</p>
      <small>金币变化：你 ${signed(row.humanMoneyDelta)} · Bot ${signed(row.botMoneyDelta)}</small>
    </article>`).join("") : '<div class="empty-state">执行回合后会显示双方动作</div>';
}

function signed(value) { return `${Number(value) >= 0 ? "+" : ""}${Number(value).toLocaleString("zh-CN")}`; }

function render() {
  const game = state.game;
  const humanFarm = state.farms[game.humanPlayer], botFarm = state.farms[game.botPlayer];
  $("day").textContent = game.day + 1; $("hour").textContent = game.hour + 1; $("step").textContent = game.step;
  $("human-money").textContent = money(humanFarm.money); $("bot-money").textContent = money(botFarm.money);
  $("bot-name").textContent = `${state.bot.name} · ${state.bot.version}`;
  $("human-land").textContent = `${(humanFarm.unlocked_quadrants || []).length}/4 象限`;
  $("bot-land").textContent = `${(botFarm.unlocked_quadrants || []).length}/4 象限`;
  $("game-status").textContent = game.done ? ({win:"你获胜了",loss:"Bot 获胜",tie:"平局"}[game.result]) : `${game.days} 天赛季 · Seed ${game.seed}`;
  renderBoard($("human-board"), humanFarm, game.humanPlayer, true);
  renderBoard($("bot-board"), botFarm, game.botPlayer, false);
  $("shops").innerHTML = (state.town.unlocked_shops || []).length ? state.town.unlocked_shops.map(shop => `<span>${SHOP_LABEL[shop] || shop}</span>`).join("") : '<span class="muted">尚未解锁</span>';
  renderCellDetail(); renderStorage(); renderMarket(); renderHistory(); renderDrafts();
  $("submit-turn").disabled = busy || game.done;
  if (game.done) toast({win:"恭喜，你赢了！",loss:"本局由 Bot 获胜",tie:"本局平局"}[game.result]);
}

async function submitTurn() {
  if (busy || state.game.done) return;
  setBusy(true);
  try {
    const action = {farmer: unitDrafts[0] || ["PASS"], hands: unitDrafts.slice(1), market: marketDraft};
    state = await api("/api/step", {method:"POST", body:JSON.stringify(action)});
    resetDrafts(); render();
  } catch (error) { toast(error.message, true); }
  finally { setBusy(false); }
}

async function fastForward(turns) {
  if (busy || state.game.done) return;
  setBusy(true);
  try {
    state = await api("/api/fast-forward", {method:"POST", body:JSON.stringify({turns})});
    resetDrafts(); render();
  } catch (error) { toast(error.message, true); }
  finally { setBusy(false); }
}

async function startNewGame() {
  setBusy(true);
  try {
    const payload = {days:Number($("new-days").value), seed:Number($("new-seed").value || 0), humanPlayer:Number($("new-seat").value)};
    state = await api("/api/new", {method:"POST", body:JSON.stringify(payload)});
    selectedCell = null; resetDrafts(); render(); $("new-game-dialog").close();
  } catch (error) { toast(error.message, true); }
  finally { setBusy(false); }
}

function bindEvents() {
  document.querySelectorAll("[data-unit-action]").forEach(button => button.onclick = () => setUnitAction([button.dataset.unitAction]));
  $("plant-button").onclick = () => setUnitAction(["PLANT", $("plant-item").value]);
  $("inventory-button").onclick = () => setUnitAction([$("inventory-op").value, $("inventory-item").value, Number($("inventory-quantity").value || 1)]);
  $("market-op").onchange = updateMarketBuilder;
  $("add-market-order").onclick = () => {
    if (marketDraft.length >= 10) return toast("每回合最多 10 笔市场订单", true);
    const op = $("market-op").value;
    marketDraft.push(op === "HIRE" || op === "BUY_LAND" ? [op] : [op, $("market-item").value, Number($("market-quantity").value || 1)]);
    renderDrafts();
  };
  $("submit-turn").onclick = submitTurn;
  $("clear-draft").onclick = resetDrafts;
  document.querySelectorAll("[data-fast]").forEach(button => button.onclick = () => fastForward(Number(button.dataset.fast)));
  $("new-game-button").onclick = () => $("new-game-dialog").showModal();
  $("new-game-form").onsubmit = event => { event.preventDefault(); startNewGame(); };
}

async function init() {
  fillSelect($("plant-item"), CROPS); fillSelect($("inventory-item"), ALL_ITEMS); updateMarketBuilder(); bindEvents();
  try { state = await api("/api/state"); resetDrafts(); render(); }
  catch (error) { toast(error.message, true); }
}

init();
