# yhay81's chassis, verbatim, Apache-2.0.
# https://www.kaggle.com/code/yhay81/three-day-shop-router
# Nothing below this line is mine. The SHA-256 of each file is asserted after
# it is written, so a silent edit cannot survive a run.
import hashlib, pathlib, base64, zlib

_K = pathlib.Path("/kaggle/working")
WORK = _K if _K.exists() else pathlib.Path.cwd()   # runs the same off Kaggle
EXPECTED = {}
SOURCES = {}
EXPECTED['policy_plugin_abi.hpp'] = '4eb7647da3660688685a8ff032bd1ada6558605a27ae6b86fc338a91f8b45476'
SOURCES['policy_plugin_abi.hpp'] = r"""// Stable C ABI between the native tournament and separately compiled policies.
#pragma once

#include "runtime_types.hpp"

#include <cstdint>

namespace kag::native {

inline constexpr uint32_t POLICY_PLUGIN_ABI_VERSION = 1;

using PluginAbiVersion = uint32_t (*)();
using PluginCreate = void* (*)();
using PluginDestroy = void (*)(void* context);
using PluginAct = int (*)(
    void* context,
    const State* state,
    const Config* config,
    int seat,
    Action* output);

}  // namespace kag::native
"""

EXPECTED['runtime_types.hpp'] = '0010c15079e2114e36b5de8b281375db83f202e769e30b27cc437fc0e3ad11f1'
SOURCES['runtime_types.hpp'] = r"""// SPDX-License-Identifier: Apache-2.0
// Minimal Kaggriculture types required by the submitted tape router.
#pragma once

#include <cstdint>

namespace kag {

enum Item : std::uint8_t {
    WHEAT = 0,
    CARROT,
    TOMATO,
    STRAWBERRY,
    MELON,
    EGG,
    MILK,
    WOOL,
    FERTILIZER,
    GOOSE,
    COW,
    SHEEP,
    N_ITEMS,
};

inline constexpr int N_PRODUCTS = 9;
inline constexpr int N_CROPS = 5;
inline constexpr int N_ANIMALS = 3;
inline constexpr int MAX_UNITS = 40;
inline constexpr int BOARD = 10;
inline constexpr int MAX_SHOP_INSTANCES = 8;

inline bool is_animal(std::uint8_t item) {
    return item >= GOOSE && item < N_ITEMS;
}

enum Op : std::uint8_t {
    OP_PASS = 0,
    OP_NORTH,
    OP_SOUTH,
    OP_EAST,
    OP_WEST,
    OP_PICKUP,
    OP_DROP,
    OP_PLACE,
    OP_PLANT,
    OP_WATER,
    OP_HARVEST,
    OP_FERTILIZE,
    OP_DIG,
    OP_BUILD_COOP,
    OP_BUILD_PASTURE,
    OP_FEED,
    OP_COLLECT_FERTILIZER,
    OP_CARE,
};

enum MOp : std::uint8_t {
    M_NONE = 0,
    M_HIRE,
    M_BUY_LAND,
    M_BUY_SEED,
    M_BUY_PRODUCT,
    M_BUY_ANIMAL,
    M_SELL,
};

enum ShopId : std::uint8_t {
    SHOP_BAKERY = 0,
    SHOP_BRUNCH_SPOT,
    SHOP_FARMERS_MARKET,
    SHOP_ICE_CREAM_SHOP,
    SHOP_PET_CAFE,
    SHOP_PIZZA_SHOP,
    SHOP_SMOOTHIE_SHOP,
    SHOP_YARN_STORE,
};

enum TileKind : std::uint8_t {
    T_EMPTY = 0,
    T_LOCKED,
    T_WEED,
    T_COOP,
    T_PASTURE,
    T_PLANT,
};

struct CropDef {
    int seed;
};

inline constexpr CropDef CROPS[N_CROPS] = {{10}, {20}, {50}, {100}, {80}};

struct AnimalDef {
    int cost;
};

inline constexpr AnimalDef ANIMALS[N_ANIMALS] = {{300}, {400}, {500}};
inline constexpr int LAND_PRICES[3] = {1000, 2000, 4000};

inline int fib(int n) {
    int previous = 1;
    int current = 1;
    for (int index = 0; index < n; ++index) {
        const int next = previous + current;
        previous = current;
        current = next;
    }
    return previous;
}

struct Config {
    int episode_steps = 720;
    int max_orders = 10;
    int hire_mult = 1;
};

struct Tile {
    TileKind kind = T_EMPTY;
};

struct Farm {
    double money = 0;
    Tile tiles[BOARD][BOARD]{};
    int n_units = 1;
    int n_quadrants = 1;
    int hires_today = 0;
    std::int16_t shed[N_ITEMS]{};
    std::int16_t inv[MAX_UNITS][N_ITEMS]{};
};

struct Market {
    std::int32_t inventory[N_PRODUCTS]{};
    std::int32_t prices[N_PRODUCTS]{};
};

struct State {
    Farm farms[2]{};
    Market market{};
    std::uint8_t shops[MAX_SHOP_INSTANCES]{};
    int n_shops = 0;
    int step = 0;
};

struct UnitAction {
    std::uint8_t op = OP_PASS;
    std::uint8_t arg = 0;
    std::int16_t n = 1;
};

struct Order {
    std::uint8_t op = M_NONE;
    std::uint8_t item = 0;
    std::int32_t n = 0;
};

struct Action {
    UnitAction units[MAX_UNITS]{};
    int n_units = 1;
    Order orders[16]{};
    int n_orders = 0;
};

}  // namespace kag
"""

EXPECTED['six_day_budget_guard.hpp'] = '2e55caa0d637a3cc246c194a64ba02d35817f787a01a08784a0a8fdd91734cd0'
SOURCES['six_day_budget_guard.hpp'] = r"""// SPDX-License-Identifier: Apache-2.0
// Fund a 144-turn tape segment by selling only inventory above its static reserve.
#pragma once

#include "runtime_types.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>

namespace kag::native {

inline constexpr int SIX_DAY_TURNS = 144;

struct SixDayRequirements {
    double purchase_budget = 0.0;
    std::array<int, N_ITEMS> starting_items{};
};

struct SixDayBudgetGuardSettings {
    int interval_turns = SIX_DAY_TURNS;
    int minimum_unit_price = 2;
    bool sales_first = true;
    bool protect_static_consumption = true;
};

inline int planned_quantity(int quantity) noexcept {
    return std::max(1, quantity);
}

template <typename ActionAt>
SixDayRequirements calculate_six_day_requirements(
    const State& state,
    const Config& config,
    int seat,
    int start,
    int end,
    ActionAt action_at) {
    SixDayRequirements result;
    std::array<int, N_ITEMS> item_balance{};
    std::array<int, 6> hires_by_day{};
    int quadrants = state.farms[seat].n_quadrants;

    for (int step = start; step < end; ++step) {
        const Action action = action_at(step);
        for (int index = 0; index < action.n_units; ++index) {
            const UnitAction& operation = action.units[index];
            const int quantity = planned_quantity(operation.n);
            if (operation.op == OP_FEED) {
                --item_balance[WHEAT];
                result.starting_items[WHEAT] = std::max(
                    result.starting_items[WHEAT], -item_balance[WHEAT]);
            } else if (operation.op == OP_FERTILIZE) {
                --item_balance[FERTILIZER];
                result.starting_items[FERTILIZER] = std::max(
                    result.starting_items[FERTILIZER], -item_balance[FERTILIZER]);
            } else if (operation.op == OP_PLACE && operation.arg < N_ITEMS) {
                item_balance[operation.arg] -= quantity;
                result.starting_items[operation.arg] = std::max(
                    result.starting_items[operation.arg],
                    -item_balance[operation.arg]);
            }
        }
        for (int index = 0; index < action.n_orders; ++index) {
            const Order& order = action.orders[index];
            const int quantity = planned_quantity(order.n);
            if (order.op == M_HIRE) {
                const int day = std::min(5, std::max(0, (step - start) / 24));
                ++hires_by_day[day];
            } else if (order.op == M_BUY_LAND) {
                const int extra = quadrants - 1;
                if (extra >= 0 && extra < 3) {
                    result.purchase_budget += LAND_PRICES[extra];
                    ++quadrants;
                }
            } else if (order.op == M_BUY_SEED && order.item < N_CROPS) {
                result.purchase_budget += CROPS[order.item].seed * quantity;
            } else if (
                order.op == M_BUY_PRODUCT &&
                (order.item == WHEAT || order.item == FERTILIZER)) {
                result.purchase_budget += state.market.prices[order.item] * quantity;
                item_balance[order.item] += quantity;
            } else if (order.op == M_BUY_ANIMAL && is_animal(order.item)) {
                result.purchase_budget += ANIMALS[order.item - GOOSE].cost * quantity;
                item_balance[order.item] += quantity;
            }
        }
    }
    for (int day = 0; day < static_cast<int>(hires_by_day.size()); ++day) {
        const int first_hire = day == 0 ? state.farms[seat].hires_today : 0;
        for (int index = 0; index < hires_by_day[day]; ++index) {
            result.purchase_budget += config.hire_mult * fib(first_hire + index);
        }
    }
    return result;
}

inline int owned_in_hands(const Farm& farm, int item) noexcept {
    int result = 0;
    for (int unit = 0; unit < std::min(farm.n_units, MAX_UNITS); ++unit) {
        result += std::max(0, static_cast<int>(farm.inv[unit][item]));
    }
    return result;
}

inline int existing_sale(const Action& action, int item) noexcept {
    int result = 0;
    for (int index = 0; index < action.n_orders; ++index) {
        const Order& order = action.orders[index];
        if (order.op == M_SELL && order.item == item && order.n > 0) {
            result += order.n;
        }
    }
    return result;
}

inline bool add_budget_sale(
    Action& action,
    const Config& config,
    int item,
    int quantity) noexcept {
    if (quantity <= 0) return true;
    for (int index = 0; index < action.n_orders; ++index) {
        Order& order = action.orders[index];
        if (order.op == M_SELL && order.item == item) {
            order.n += quantity;
            return true;
        }
    }
    const int limit = std::max(0, std::min(16, config.max_orders));
    if (action.n_orders >= limit) return false;
    action.orders[action.n_orders++] = {
        M_SELL,
        static_cast<std::uint8_t>(item),
        quantity,
    };
    return true;
}

inline void budget_sales_first(Action& action) noexcept {
    std::array<Order, 16> ordered{};
    int output = 0;
    for (int index = 0; index < action.n_orders; ++index) {
        if (action.orders[index].op == M_SELL) ordered[output++] = action.orders[index];
    }
    for (int index = 0; index < action.n_orders; ++index) {
        if (action.orders[index].op != M_SELL) ordered[output++] = action.orders[index];
    }
    std::copy(ordered.begin(), ordered.end(), action.orders);
}

inline Action apply_six_day_budget_guard(
    const State& state,
    const Config& config,
    int seat,
    const Action& input,
    const SixDayRequirements& requirements,
    const SixDayBudgetGuardSettings& settings = {}) noexcept {
    Action result = input;
    if (seat < 0 || seat > 1 || settings.interval_turns <= 0 ||
        state.step % settings.interval_turns != 0) {
        return result;
    }
    const Farm& farm = state.farms[seat];
    double available_cash = farm.money;
    for (int item = 0; item < N_PRODUCTS; ++item) {
        const int sold = std::min(
            std::max(0, static_cast<int>(farm.shed[item])),
            existing_sale(result, item));
        available_cash += sold * state.market.prices[item];
    }
    double shortfall = requirements.purchase_budget - available_cash;
    if (shortfall <= 0.0) return result;

    struct Candidate {
        int item = 0;
        int quantity = 0;
        int price = 0;
    };
    std::array<Candidate, N_PRODUCTS> candidates{};
    int count = 0;
    for (int item = 0; item < N_PRODUCTS; ++item) {
        const int price = state.market.prices[item];
        if (price < settings.minimum_unit_price) continue;
        const int protected_total = settings.protect_static_consumption
            ? requirements.starting_items[item]
            : 0;
        const int protected_shed = std::max(
            0,
            protected_total - owned_in_hands(farm, item));
        const int available = std::max(
            0,
            static_cast<int>(farm.shed[item]) - protected_shed -
                existing_sale(result, item));
        if (available > 0) candidates[count++] = {item, available, price};
    }
    std::stable_sort(
        candidates.begin(),
        candidates.begin() + count,
        [](const Candidate& left, const Candidate& right) {
            if (left.price != right.price) return left.price > right.price;
            return left.item < right.item;
        });

    int added = 0;
    for (int index = 0; index < count && shortfall > 0.0; ++index) {
        const Candidate& candidate = candidates[index];
        const int needed = static_cast<int>(std::ceil(shortfall / candidate.price));
        const int quantity = std::min(candidate.quantity, needed);
        if (!add_budget_sale(result, config, candidate.item, quantity)) continue;
        shortfall -= static_cast<double>(quantity * candidate.price);
        ++added;
    }
    if (added > 0 && settings.sales_first) budget_sales_first(result);
    return result;
}

}  // namespace kag::native
"""

EXPECTED['policy.cpp'] = 'abdb6b13cb91504409de0cf53679c5443f309f1fe937f676e68707830744392b'
SOURCES['policy.cpp'] = r"""// SPDX-License-Identifier: Apache-2.0
#include "policy_plugin_abi.hpp"
#include "six_day_budget_guard.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <sstream>
#include <stdexcept>

namespace {

constexpr int kSegmentTurns = 72;
constexpr int kDecisionStep = 360;
#include "tape.inc"

kag::Action decode_action(const char* encoded) {
    kag::Action action{};
    std::istringstream input(encoded);
    if (!(input >> action.n_units >> action.n_orders) ||
        action.n_units < 0 || action.n_units > kag::MAX_UNITS ||
        action.n_orders < 0 || action.n_orders > 16) {
        throw std::runtime_error("invalid encoded tape action counts");
    }
    for (int index = 0; index < action.n_units; ++index) {
        int operation = 0, argument = 0, quantity = 0;
        if (!(input >> operation >> argument >> quantity))
            throw std::runtime_error("invalid encoded unit action");
        action.units[index] = {
            static_cast<std::uint8_t>(operation),
            static_cast<std::uint8_t>(argument),
            static_cast<std::int16_t>(quantity),
        };
    }
    for (int index = 0; index < action.n_orders; ++index) {
        int operation = 0, item = 0, quantity = 0;
        if (!(input >> operation >> item >> quantity))
            throw std::runtime_error("invalid encoded market order");
        action.orders[index] = {
            static_cast<std::uint8_t>(operation),
            static_cast<std::uint8_t>(item),
            quantity,
        };
    }
    int trailing = 0;
    if (input >> trailing) throw std::runtime_error("trailing encoded tape value");
    return action;
}



int plant_tiles(const kag::Farm& farm) {
    int result = 0;
    for (int y = 0; y < kag::BOARD; ++y)
        for (int x = 0; x < kag::BOARD; ++x)
            result += farm.tiles[y][x].kind == kag::T_PLANT;
    return result;
}


int select_route(const kag::State& state, int seat) {
    static_cast<void>(seat);
    // Route 1: segment72_b01_0091_0ebdd1a079
    if (state.n_shops >= 1 &&
        state.shops[0] == kag::SHOP_BAKERY &&
        static_cast<double>(state.market.inventory[kag::FERTILIZER]) <= 10232.5) return 1;
    // Route 1: segment72_b01_0091_0ebdd1a079
    if (state.n_shops >= 1 &&
        state.shops[0] == kag::SHOP_PET_CAFE &&
        static_cast<double>(plant_tiles(state.farms[1 - seat])) <= 64.5) return 1;
    return 0;
}

struct Context {
    std::array<std::array<kag::Action, kTurns>, kRoutes> actions{};
    int selected_route = 0;

    Context() {
        for (int route = 0; route < kRoutes; ++route)
            for (int step = 0; step < kTurns; ++step)
                actions[route][step] = decode_action(kEncodedTapes[route][step]);
    }

    kag::Action action_for(int step) const {
        if (step < 0 || step >= kTurns) return kag::Action{};
        return actions[selected_route][static_cast<std::size_t>(step)];
    }

    kag::Action act(const kag::State& state, const kag::Config& config, int seat) {
        if (state.step < 0 || state.step >= kTurns) return kag::Action{};
        if (state.step == 0) selected_route = 0;
        if (state.step == kDecisionStep) selected_route = select_route(state, seat);

        const kag::Action input = action_for(state.step);
        if (state.step % kSegmentTurns != 0) return input;
        const int end = std::min(kTurns, state.step + kSegmentTurns);
        const auto requirements = kag::native::calculate_six_day_requirements(
            state,
            config,
            seat,
            state.step,
            end,
            [&](int step) { return action_for(step); });
        kag::native::SixDayBudgetGuardSettings settings;
        settings.interval_turns = kSegmentTurns;
        return kag::native::apply_six_day_budget_guard(
            state, config, seat, input, requirements, settings);
    }
};

}  // namespace

extern "C" std::uint32_t kag_policy_abi_version() {
    return kag::native::POLICY_PLUGIN_ABI_VERSION;
}
extern "C" void* kag_policy_create() {
    try { return new Context{}; } catch (...) { return nullptr; }
}
extern "C" void kag_policy_destroy(void* context) {
    delete static_cast<Context*>(context);
}
extern "C" int kag_policy_act(
    void* raw_context,
    const kag::State* state,
    const kag::Config* config,
    int seat,
    kag::Action* output) {
    if (!raw_context || !state || !config || !output || seat < 0 || seat > 1) return 1;
    try {
        *output = static_cast<Context*>(raw_context)->act(*state, *config, seat);
        return 0;
    } catch (...) {
        return 2;
    }
}
"""

EXPECTED['submission_bridge.cpp'] = 'a92ca5b78cae850987a7262122eb83ec9f9a313430e906e1ac08bfe1fd887ff1'
SOURCES['submission_bridge.cpp'] = r"""// SPDX-License-Identifier: Apache-2.0
// Packed Python-observation bridge linked directly with ShopForge SixDay Guard R1.
#include "policy_plugin_abi.hpp"
#include "runtime_types.hpp"

#include <algorithm>
#include <cstdint>

extern "C" std::uint32_t kag_policy_abi_version();
extern "C" void* kag_policy_create();
extern "C" void kag_policy_destroy(void* context);
extern "C" int kag_policy_act(
    void* context,
    const kag::State* state,
    const kag::Config* config,
    int seat,
    kag::Action* output);

namespace {

#pragma pack(push, 1)
struct PackedTile {
    std::uint8_t kind = 0;
};

struct PackedFarm {
    double money = 0;
    PackedTile tiles[kag::BOARD][kag::BOARD]{};
    std::int32_t n_units = 1;
    std::int32_t n_quadrants = 1;
    std::int32_t hires_today = 0;
    std::int16_t shed[kag::N_ITEMS]{};
    std::int16_t inv[kag::MAX_UNITS][kag::N_ITEMS]{};
};

struct PackedObservation {
    std::int32_t step = 0;
    std::int32_t n_shops = 0;
    std::int32_t market_inventory[kag::N_PRODUCTS]{};
    std::int32_t market_prices[kag::N_PRODUCTS]{};
    std::uint8_t shops[kag::MAX_SHOP_INSTANCES]{};
    PackedFarm farms[2]{};
};

struct PackedAction {
    std::uint8_t unit_ops[kag::MAX_UNITS]{};
    std::uint8_t unit_args[kag::MAX_UNITS]{};
    std::int16_t unit_ns[kag::MAX_UNITS]{};
    std::int32_t n_units = 1;
    std::uint8_t order_ops[16]{};
    std::uint8_t order_items[16]{};
    std::int32_t order_ns[16]{};
    std::int32_t n_orders = 0;
};
#pragma pack(pop)

void fill_state(const PackedObservation& observation, kag::State& state) {
    state = kag::State{};
    state.step = observation.step;
    state.n_shops = std::max(0, std::min(observation.n_shops, kag::MAX_SHOP_INSTANCES));
    for (int index = 0; index < state.n_shops; ++index)
        state.shops[index] = observation.shops[index];
    for (int item = 0; item < kag::N_PRODUCTS; ++item) {
        state.market.inventory[item] = observation.market_inventory[item];
        state.market.prices[item] = observation.market_prices[item];
    }
    for (int player = 0; player < 2; ++player) {
        const PackedFarm& source = observation.farms[player];
        kag::Farm& farm = state.farms[player];
        farm.money = source.money;
        farm.n_units = std::max(1, std::min(source.n_units, kag::MAX_UNITS));
        farm.n_quadrants = std::max(0, std::min(source.n_quadrants, 4));
        farm.hires_today = source.hires_today;
        for (int y = 0; y < kag::BOARD; ++y) {
            for (int x = 0; x < kag::BOARD; ++x) {
                farm.tiles[y][x].kind =
                    static_cast<kag::TileKind>(source.tiles[y][x].kind);
            }
        }
        for (int item = 0; item < kag::N_ITEMS; ++item) {
            farm.shed[item] = source.shed[item];
        }
        for (int unit = 0; unit < kag::MAX_UNITS; ++unit)
            for (int item = 0; item < kag::N_ITEMS; ++item)
                farm.inv[unit][item] = source.inv[unit][item];
    }
}
void pack_action(const kag::Action& action, PackedAction& packed) {
    packed = PackedAction{};
    packed.n_units = std::max(1, std::min(action.n_units, kag::MAX_UNITS));
    for (int unit = 0; unit < packed.n_units; ++unit) {
        packed.unit_ops[unit] = action.units[unit].op;
        packed.unit_args[unit] = action.units[unit].arg;
        packed.unit_ns[unit] = action.units[unit].n;
    }
    packed.n_orders = std::max(0, std::min(action.n_orders, 16));
    for (int index = 0; index < packed.n_orders; ++index) {
        packed.order_ops[index] = action.orders[index].op;
        packed.order_items[index] = action.orders[index].item;
        packed.order_ns[index] = action.orders[index].n;
    }
}

struct Session {
    void* context[2]{};
    int last_step[2]{-1, -1};

    ~Session() {
        for (void*& value : context) {
            if (value != nullptr) kag_policy_destroy(value);
            value = nullptr;
        }
    }

    void reset(int seat) {
        if (context[seat] != nullptr) kag_policy_destroy(context[seat]);
        context[seat] = kag_policy_create();
        last_step[seat] = -1;
    }
};

Session session;

}  // namespace

extern "C" std::uint32_t kag_submission_abi_version() {
    return kag_policy_abi_version() == kag::native::POLICY_PLUGIN_ABI_VERSION ? 1u : 0u;
}

extern "C" int kag_submission_act(
    const PackedObservation* observation,
    int seat,
    int episode_steps,
    PackedAction* output) {
    if (observation == nullptr || output == nullptr || seat < 0 || seat > 1)
        return 1;
    if (session.context[seat] == nullptr || observation->step == 0 ||
        observation->step < session.last_step[seat]) {
        session.reset(seat);
    }
    if (session.context[seat] == nullptr) return 1;
    kag::State state;
    fill_state(*observation, state);
    kag::Config config;
    if (episode_steps > 0) config.episode_steps = episode_steps;
    kag::Action action;
    if (kag_policy_act(session.context[seat], &state, &config, seat, &action) != 0)
        return 1;
    pack_action(action, *output);
    session.last_step[seat] = observation->step;
    return 0;
}
"""

# tape.inc is the chassis's recorded action TABLE, not logic: 108,478 bytes of
# generated data. It is carried compressed so the page stays readable, and its
# SHA-256 is checked exactly like the others.
EXPECTED['tape.inc'] = '30b724c3c905d0c03e4ef38d36f96fb7acbd6abef5371abbedee36ea3717e09f'
SOURCES['tape.inc'] = zlib.decompress(base64.b64decode(
"eNrNfU2vJTdy5V6/4qKXg4ZNRpDMJIxZDmYxu4F3hhcaddkW3CMJahmYQaP/+9S7+cVgnBOZpaoB3EK/Vr+Xl8nLZDIiTpw48fd///rvn3769Ov3v3360+v7H3778eefXn/6/rfv/+71Pz59+uX127/9+JfXv/z450+vv3z65fuPq17/8uvP//vz7z+9fv30/Z++/1+f//TLz3/+8Yf/+/rzz//64w9/990PP//0l98+/Z9ffn39+NNvr3//x//49ae/vP7ra8n9H+a//c+f/+O3Tx9/lP1Prx/+7ftf/8tr+/d//28//fDznz796R+//+XTX/5pv/if/2kb8Z8/f+qv370+/+evf8iv/Eqf/8mv8vFT//DHj1+l92/zq33+ub7088/l88/yyrL/gf2sH5+Vj//JL/k8VjsG3v5y/J983fH4w8etsvnEOWKeb1Wuj78/IZ8nWa4/VP/xZbiJ+WB//2bxk9sHWV74c2X8837fbRLD5MDnxmuWbW7dLQmb5v7163Bpjm+nw8T2yZp7b39hn/Mz2+/dye3MLcznlmCaad+B+zT3f7+uf/9+v7IM99+uHyfZhzF1GKHj7Xpz9+0363Alu3t/cPfxNwnc/bpmHX6mx3dXN2Zyd0/k7uPP9fGV/fGVCVz5sRY1Okw+X1PPb+1/1uGa8ZUtZJx962ZwTzPUAt7sPPzuuG7bxbn5lzG387rjTVo+L6t5+J//sr0Kx+91v17cl5BhhOv6sl+//X6fRh8+UKYbyD7xZL6fO+vMVeMxYHfudU0brsyVXJSGu6Xwmv7gmvKNxvlW89H/ZOOk33nNx8PcXrlt2zAr/zHPal8r8pa+L5qOf/eCvreQTO9V/C6Tazp438PDxbwG6CwfpjQepHn6iscxpfFAlZjH4qdU3EjFT8mPNN5OhtNgfIdz8nNSN/3Vz2kcKie2TuNtV7fiZIWGgbYzrZivpeM92/vPm9+4j7o7kW4l7Ldwf/Vrlonjo8M1xlvs85lul4xYzS98IfXG7T5eyBbYy9lpzujVdZvyfDfbvDX5Lm7za0xe1+PSyEWzV1b8xo8ftlMFoyZ/bXO7e9g8wK0zb0BxvzLfq8wjjS6m/V7d2XDvV+7fS90SZLsFh++lblj/vYQcAt0N6q9M0AHf3mIdNqi1YJd7oterPO6c8chReIvDKRJ37IxH9duU2dUzY8tsgM3jG521egTG7tI2XNuciyL++TFvRkI3ehkn0KYzosanw/tR6HOjDd92YNmZuS5m8evkRIMjQT9meFxah2XPsb+w+GG7t/PN7SMlkYa/HfUqOnr1waTS/O4hK76O8UQfllj8MbMQJ8Ssm84vhHXGxB0L44E2Pd7x1NleutU93+LsdWLeS3Xv1mxAs31T3EXIG4rHU3KNn566t3l2pfW9CJXa781Dufa1Prb3dX+XmQOue+hXTgyqRK61NTDbJo+cghPCMfu8YK/gfGX9sR1b/DFMvnMO2PtWmMkHM+/M5PsXaToWLptvgoAY9bGORprPnME8nrPdLOX2sxuIbR2OxsssGfemg9NguLS5s7STSwsZVNyV4r1yj0J1Dxlu33CKHYYt4Y+m7RPFD9vcNP3XUuLWZIdZCfEI+nTlhRh/vOFCzPj2/n88NgHGvAXjP0fPMjdYkSMg2xM499Tlo1X3NS6grZrfjIfTMc77i6TzAwoGKvgG+4fFg9vJI8/s0zl5nDl5ADqTj6s/kcb3lv3h/enl/U9OxxtNXN3uRm3bxwaIbtsyo7v5ccqv+40E+C/q0Tf/h+MO10BHvFyZW7TcDLU5YH3fGtMH9tHBoqo5JPq8wDpsRHVTyzOOfjz74pNDubhBVmAc+/sgzs5uHL8rg8fTgR86ord9GGQZT7vqnKdi00Y6eFJ92KwN+HyFJBaurXY8GP/SqUtEFLgmx2cFRK2KAJbTq70+i7JUnVjmPny6e/umGHgbjZC9tXWrsWU9fj/fWYklBLauD9u4OOSdhbz2bfp8232EC+ZXM0UXXo9Tf28b2UcwJ4xHizv5BufW+/j/9TyZ5LFJ2Szdh1e6nOd+Aalh/PshcWwfY3U/C/mNOQzAfVjKB30cOJHT7yqPwbp3Las5BG1c2OAQMh2cy3Bw2KzTaHAuyzyajOnlaf54FnLMtsFabPcZwRZ1mSk8go4PFqe18nwsKt2gfQrS9++/ECNW3LGWSVDjPzscGOZ46J65oMQR9eepR0nUnVTiztMe4qM8IOkQrVs8Uo7wkPnGylCW8WT1VoAtrGL7Rb+xkgxMdyYgEWNRiCeQhkM8kSizk32Z3O70eTyPXKCs4/VZc4iPEMj+8q7hp9lPY0/nSGI17szT836LV+ro9NcdYdDQgbPDbQO9BxF0zLIAPQF/8u1ML5//2yAs6L3I7Vo1h1a7WE5vz273yfeX/WQ2vekzI6CyXyAuAMmhE3N4jzlf51O1vnQ+bXHC7+tkQjbCFDBTSsIbMtQ0t8WanhyNyPM42+SaN6+GDZUIEjG/m9HKWfRVSepoAj3B2rEz2qO/5jAMFs9/owrOKHWWZFw7dSdKmIF2ac9zah4d2Z9ECaMFmxYdl039M+jE6QImBi2bT+oISeWanNywbJdbxtBB78CPsY75nsJClNE/7VEW/8xgbFOrxB00j0DI7Yr5lkuU4/Y4GXQcxm02JvESoSaZpZ/ZTeezFIKFdOAnd2fqzNx2fgDJtFmTJ9jwbRDdtDkamVzIv0GQ3BAVfQE8d/leZYiZFMD2m7FFsPw6M1+PWCCnM7Ao7G00LzAb/XxB04WbVQ++GditjifKtG39gd38MC30JYYpTaHO8sClQVFPDrKFPKp0FoWsU/UevbGBDuQ4ZpRRFDkO1mh2AEzKYpuM5KTufR/cLfXZGDuhSszR8n40bX+Vt13+8d3PuRmPmS6Yj6J0XK8VRezJL1i/M0ZpRqaMN67kZ/IzAnBnZ9+0O2ogmI+S7A7gT0wn6bDMSpe5kfkUv8y7qQCrLGQq2VqJ+UuBNabrY76VOJ+q+5VRSrkcxnCkbZ4NdGOIeSrLXkjhnjiexo6enH5CED4OyHJlM3oPV6edXJ8aN2ToxnDwC03c5ZgF6WhKSMsUX3wHSuXYTTJlyPODsSO7uiGbdRs6UZiT/iTcz228TM9R+nOZwofqR00I7Y3Bo8MaJGfjjiEVZLc7z3snllsCg6ono/h0M8h1TaQZMqKGJxJAEU9KT5Y3BEBA0+RGFOuCfNCpzXzb+1dlS12V482UN9JaTkBi+3eEt5a34byu3Cmii3G9y0vKuGWvg+g9Hzfd5ZoUTOG0afQsx6RBodY498K8QuNBybQy16wTK+pi9DCIwG8zeo9/jOxLLQDtzIc7dvjBtZ2nvH9UTdnVtfiG9lX9/Ou1ImjGHnpZPdV0eZE0rznLjneNDdyZXwAe5LWT30Da7tHqeINEziGU9jCoXLtelbOOxSZXc55Wo4PjzNKPzHmZKGqRENpDHK3ldGUF0kMACXQFZ3AF/9MOD1Cm0rEU0c0RFmz+x474wA2wI5oQAsTD23mxRVe6LVIeeCj91lNor262/UgxKc4Exj8FhsfvgywB0oBOUNB4O7HZoAxoEooMEqCPVh8F+Lvq6DFomM+0+9LsaI8tDRM9QPHsiQxivXJ15W/uu30MdB5ehcVd+1CYdnYRMjKaLiJBlUfr6t0oO9HMHoUldywRMxHNFBAczFp2D4IoKFbxTmMj5T7i+Bu4uvecpz+Tx+cv3mx1StIf/I7CWMfVL0thaDmdp3iTCoZaCXBiZzptFvdQVrfPJZ5oZw9e2X4tBCaYLDZgWBnO0bRhvW1L3mV2RSp24p6m7pMQ6MjzgakZo3gHq/uvLYQV5FM84r+ygq/cI2qoWQSw1S13cziTfaCV6FZX/6ST4QYNWz2ReRaWJjY2AHxx5ig8/qtHA/rXoAHWuvpovO6VLLMVG4qpywRtFZb2oWC3gZKUI4iFJQkdwJ2sFTYPu7BfAfh3eccP5nXfflXCYrt+crrWCfpl0QHAth30m2aQYDkfkfBaH2FoHVqbzMyAzGtzTabdEL9SNJnD+Sngi3VvFcafYh2eNBMhJ85XYkB994+dL9DKGLZ5Yk/JBP21GPZdcfW//WICvp4+dAscCgkf/10l9LjKiwtBoNFObDbAiUqszHNlc+n+fElujyTKfRpfzeojRRCPymyAo2RF8gFB4klgZ1ISW9pEEOnTgqUrsg6rH3mx9DBE/xrUeiiuWn6fudopkQwvZgiyC0+P1DOA2iRGxCug621ZbFADIQxpKwT1tLQQ5OcthErgj+5pLO8qNxLtoepLT/Pp99Xg4HCbhlqYC569BIpZrY6WvjHlI4RGNUBhHKgSoDDOe8xrvF7C1quQmMwf3RfpYuTVJRZj39BFTwPp9thKDWNhzoD4TeYULCaLy1xz+zQBBdHXz0t4KM/MLx/2gVymkrN5JjE1lg4qzHtKbMGEpYAYhex2vQBjLKbFKl+vzFyv7sOq2/XqLH2mlHM7vgCJ8JHN0wABbpok0/oxO0aYZKYy4ZklZsUfmcduzeO603e/KoxT62zPwG0FNNjRPn6Y537+dT2IcnLmUD4OkR5HMJ0mIdv+z3o9WQ/pZhDvmUTf8k6+yRDyvJnEdkRrfJIH9jxYNzKSh7MS6uj5LPY4KwsB1XPEc445swmdKbPljIUQPLecceU5yw4KPJbLbBTG7DL/ZxgxsviNuEwwXs1bzoGpMniIEoGTdRwNRBdg4Xu8eshDos6W0H10Ks75JZMQWDM6i7dLBghlFHEHHhdiGBRcNjN9/cR8SvXOVSWgowdvgy0Gvnb2uwZ5lZmRT4GZWIn7BBfMsa8Qv3dhLmXxOygRboQytwmGLCvFN4mvKqNN7aw6Bdh/6jUZoyr+7UhsGXsAkuYJJH2SE/W3mOPO9jrTn7+PF3yYqnVKdgrJw3FkcKc/CywDq+88gjgwdgxvM6RJLSgvp4S6PznaySGIJp1QSBUPAqIAyW+u9Lhw9cySxBNoB1CzO86VuUFn3rsyeNnOkzs4vHKKpJCuj6JsH13PzFb1fZuCMkkgxkSrmgGfY2VL0Mepl2erSpNoElZq2EUVNGWQlN+nAXhicFmFYvafvdSM8p3reJ/1flkRTugSiZwOSEqoxPN+FDwaikfV02vNdSCG5zLyfuomlBFsLvS8FuBy4TS6FX+h2tVI8LdjbsZphW5YloXwgKfUz5z5LN4foWBfj79zJtB/UOsOBY124oietaSIeIqK3z2gfux83bJV85cHOD6gH6FoPM77rqGV73HcrN8m/Vlep5Zp9NbNqgp1N9fYyr/H1tOibiGih6kvu38G45VY7XLFktsJlbZbJCoX5mksKG0E9+o8rA1rE03IxmWS58hUI0gZ+ppfQdH/Ma7Gn8spLicSIL41zjeHVc0og5RzPGEEgLOXHr3BBQUeOtVRoHNEmMxS5mLDw8CZFi8l4NpVb5xWv8hMMRllMGqcxx1mLEcPjeTDJ7uP76rh7Fuou1x3sXsPsH2EQpcpYjSde6/6TwLGPhAUIdW258ALBiGQ8mVlQaA7NmbY1xKFPzsU6/RwF0YWmgT1Pz5q1zqzCgKg7BnbvXPqdK1BOhpU4XpH4WOMdg6/MHz2WB/9cF6Ld31XUpHc3p84n2gDvoRQ1eTFP1Rh50lilDSv3WeZ5InXjOncF6AxwaTE4H1FnoYGWMGyY9hPudtX+qxbUOGrvY6KskYGml9h+XEe3IAAYNBJDOYJkFACQYqMBg2aewCnY8QZij//C3daExt5IQJrYt5qgK814k4g8c6KKW9p8g566Bf0GOvowOmg4bCNdhNNontuMnZoFuYUouRwwZbiWGxk5xrL7K+2YqtdFVsdJa91ptD5tWYKEyWCevyKVJZhvyvUWsHI3NzlRGq9QQDd6VNUGijnzGrVhXhu1sKyGLkTBXwQ3q7mTUwIk7nSXtk6rgyon87mZXgXFcCIi18RfVKyXfyCZFR5w3RSwJ+T9zkkJIYU5u95OrLODocV/xBWVtVjv9sZ1wSx5Fhgn5IIOh13YVw3eSCwZXbz7lhNSYrY7gPp2ZFS+Da+yToby144/rR8izHq3vH9N3Y2GlcWr3tblwn9twJjR/Z+gWXnwOlgRSLqFNEN6uHpK+jcZy8I8GJ8QnA5kvHu1O9skEoVc2SAb0D8DQKZQk0qZfgpOEKFEO8Af9DWNYo/Btu4IkrxzRy2nGDSsdcruJwMC1C9k6h8aJv2qgwyzi2YNUhrV0oy6Q6tQaFmRxAHql1tmDRvT1FU0b96KkJjEBOfs8/mIIxG6WJ7f3vCDLz2PEhRAfbFOjxFhBkIc+iQmlxj4WsBPnph8ig3p8iC7bI9leQVdZ1U9ky9jwZdxn4TVgHHv6DsozIYF6SOFtb2pOMc5AxxFFKxtxviaZ81SgD21hb2jWKQ/eq9wZVBsQAYHTYq3G5IPS37o69cX72A/QYRsOWmwFf3zNzwUnofiUoKAUZS9uyJb5ReqTtvokDdh7pbT89KPDyP5SqLZj7HkwSI0kRoQeKFLgJnxMeRs4EiDjouFZfJLJJAEm3m7c4xnpFJboZp9IxHKJRaTqE6MlrlPFNCLW5Ac9ad21xAF+ver8mZlb0uNwz2Roh3x8idmRaOe2RQ6OoPa9DWZqw7VMZAqixGf/vvgYeq1FHk2cPRcZnWWiepJIHuQ78ps+t+rTtwY5r7HuXmISh1xvg6gDeMqNDBtVAKvHeKPo3ni9keoEtDo6hpp+dTnyKBbjcI4tKwLqjomEJOSGZiUIycSuMQ9R5INyzod+qPCeAitUO0KHq9NYnVciHPauUZYbAsI4pQwPMUqjPU2AFzQgkaYTNtuHFnNSzqTqxh8ASwF1po2BkbtqPKiG8CfxQz/ZHGORZG1L2Lg3VB5Nb5qDB3I/yYZgU79eKNJMRB15iygHYiSODYdD9nQgoVniJDY3k6oLSQEcehRfK3ybJpJCTnsEQMcnAOWKudN6i3PIZ0kx/3T+a6j0yBkjL2u9w6PNk7+Qb8hYz/TIvzkNOzMuwChY5M0Bvw+Lvz6YLIV8Hi0zIkpcQVcJkwKYnO3HGX3hH80vBlRiWrAlNe3fprFiLJFDxLUYEq8lA0Vo4trNYjY0bEtN6A/VIZh7SRyszOISgEWxTyHUgHmAmDovPasQvfLjpnAvdZ3EJCpAkx60DkxAlCwji54kQzEDkNPUHGkqa8K+sZphuGkEFEuBnw0ekKfbQBEEkDLJ9CXUXW/BuwTcu3gkPKkANhUgajB1FmHlSKOacwQQfK65RsSMVvCFGekZu6ORIqAU4J1GqRJ5IFSvLY+LhlAIg88CGsNyKU5dIZOH2r4It8Bb7uJQ7oVuJkGEqF8tXvlJgFDmuYtku0dN79XJmP2Z+loBG3INNwj6Y40kPtKVpnw+gacJ0Z4bBQ8EmBD+LPzq0qoNxoaqxkyx/+x14N4MgmQ7yCXiFW3ZJpYlfdWdLBc1wZ8TJg9AAwh1qxSdIvJscosKX5RigiYyfrfI4A0koP+tp0uiKbONsmaF8MHaKh3r6MS8wqii42dJ6gABuMJs8FUeJE+nfVAhiIXpoYEAzIr2lGROeJU/UlkHgSV82dvB/1pWQQ4JfNpJZvykPNdQJHCgBHhGgrPeCETJF6duWmyljVDCiZ+Jc1LlrOpOqLMcchAlPiilEEnKk7lXFonlEOXonSJ2JuDmMrL/wspI6ms7KTgY7kkRKFrb8adYUKNdjG7Nh7yZS3Vhrz0WgP1dCJxy8hHYQ6RFS3J4NkSAvrwoX6htYYJJofgpuoMoBnDWvVmx9faf6AKhkh/ZWLOH1Cbcr9fCoexV/AgSqwjomMR43cplsJofQOygcRYUoJfFLIeALSRlTci8mcdBbtRehJYseE0sqoDouwHYCyopYcA4CyskRDmc4DXObo43aQYvCde4RSYkAdSyWO0cqYtGoVXx2G0uNmBCAfmpBel4dQ5BXKRgrzKhOFUJ4LPXaW1EksndM2WfndNf1CB+bzUOuZIPPlLEwIMh7ZOCuItjAwPM0tJETzLshg5uqAd03Z+xuOPluZxvUpFsLTJ+CorZ4Bha6Ld4ol9resLq4yc5VjhDwLKxPL4nklkF0FkALUYsSf6Su4AVz5zMhca1xUD5gr5aYIlnG5eoygwKWXG+GBLMzVRsixXXQBLuIa5yyUu1ONPi8AzwAXV1glBiBYKwW3lYlLgcKlSg0rAx41Sm3Oa11jnatM7X5n/CPUEkiZ7JU/D726wNlWDyCDibJZ0p1vDDIMZSKBXGkG5pUxZ/uVUIKhehcgJyJS2p0l9p178YuTYpm1QroTrGDcxiAlqojObHyi6VpKLYmhj+KHZfU8v6+65vA+Lusgmwr18rvUwLbkTAMVtSNppJ69C+9cEEMm6bTcMyb9lZjzIVRUipc6GvPH2SRIDGav01gAQhprbWdKrAykZ/qTSWePkcSlpEJKizsAy/XARjYR1RPODQTCKoC3L5WEFWE+fbpbOe7T+dPlMsgv36RoZo5ZZkwJWLGU+AdC+D6H6xPUg8hBAIPLzKFDROBRPAKQGJSZUOVexl0WszIFlkJsJFelyJQNiLJIrBBnfrx5PnR49lWYAJZG9b4JNg3NrCA0Szjzzs+zSsVDE1GqUMp5yAGTlpCTOUoL+Lolpjn0EKRdJ2eqo7Jn4dHNuM4SlSjNy4GY/EvYoOOGxdO5HB/TNwIspyz+LUzUQqRQ5rs4kLR/TRInFAf3eMgu6bVXSC7fAA+Z623F2sY2thuEPomckpWVlKiP+aHlpRPlFQuVyimB2Ji6BnJJ2MD1aiQJNfnlmZyIx8PbNXCCoTavzKHPK42KjTys4m6P/+nyJufw7fWkAxdA7wWshe43mNs/LlS2sdJwbeMMoE54AaLRPKCwUjTISDhCMCPdJHi2Oaoz+3jzrj7cpkpago5amU1aZzRUIIk2zjWbtniohLrEh2wnWZLLYZAX7DDWac4KhPYdaSv5de0Pcird27SM9HaXG3ZWB9ypDOgUyUktt0dSORrJIsCTdtyJ4ORRojrSLRNcMJGzhxq8Gbs15zQb9S0qkSXpcxWbDmX8OnfEXmh2qjOwZkWxnszK5OvrQX8tc0AtVMA4P1coJ9f49lj1K7pjlUnp68IfHnfHQirl1ulj9Rc9ppcevTrOcdNNmzmUHV9wpP7AoXiRXlWNlPbiwwOI+WfK4AbHweD+6GR7MvaWOUNjsZ07AEVDrso3IikCpZsqCUOue+jgsMrszdSQiMqrY224ctwseX9mYYAAw/tX1DtFx140Qw/yO0Sp38VWVyuVPt4g2ClK008LJe9659w86TW2lY2YpcG4KUSOOkuQFAKcjGoFJ6d09a9sIy9Tj51X3k1ZyKlCu8NA+o6wDGU5zViHbFRKGXpvjNkzXUhRA4v8VyZ/DvtupRgnkyd65YXRYv1vKslzzD5+DUsx6BPqoEMByJkwQRBQLA6+NBD/6g98ZEjrnaXznzgKHf/GFqLsYolfx/xMUylKM4tS3zmSQpXI33SeNjhzDjxIplcXq0wFLcS5lb+thag0BGEa+mEJBAL/MgMlUJMH62UIG2Bl5fB9RA32ivab6LOTaKHMGPCmYZ11asxS72LRxDye4k/QvX32XRPuFQB7wPaeiQ8XgWX+xEHuFyqnu3Y3FTw0Ug/KjxMknnHz0JhC2rENClWE76wCrwzJJVvGv7zTmZ9f0MX2aQBi48XhDqCopvslUFpGjSijEqr+wr0q4JNKRFYglcJ97entygFrupO+NIljLkw6rRPX0H5pIZwrZeVm681XrrHzn0ESvj+ZIkJczbsvBCkwHU4QPz4x1OEoScKkKQNiIjX+FMtkJfwMpyP/pl9ZzISwVR4D8CRfZe3LLsCooVZWFordtwmXGFACoUJShRyQSis78g4U5Dq96F84dkYF+zJrF5S43USOsDvUJ0dIARWjdcnEnhtj0biHBDvQZJZoGfc8TawG+gwkij/LJ+RBtmJlVHtEEhvGpQuZSIREpOAvER8G4DGhEJLHHHfA3kpLaAGxEBy7g2meYDisLKEylpkpRLtjTzhbQuJKlwJBIREY09OZrpTvx1Y3x8AVA36QVPjqQGzP83wLkQsn0foT+80vEdvWUahGGRftSF8w40Dxy5ddJVT5OKJf+xfPb0QDZ1pvQO/r+F5gnjfQT++hdLgLgqBEd47ta3+wDLYzeH9CYBSO64ujIjxyDVqcKbioH8tXOQP6qFuYPuoQMoCRhQD4+oCv6FQWCsegetg5pdwE+/2GzcRaLN8G+qH70G9AOeZRMMwJtUdXnLEjVEqanlViGVAjU9Y4SpkoEzA1H6cG7AopjDQtr/s2WPa7M0RYyXiKo3mi5pSIFkQjruGg9TF5ZuALNnorkMC5zuGpc2cs+yoPkkNfMl6PltJCWtl/1bkiFaEMDaodHE0YqnUe9HXb3wjlcWQKgE4XqgGODAmfUMH2XBSRi7X0hSxGITTSxp7b+w/nDuu0N0+x2St3ODW38O+f0yqLW48QJ0UZXeRK9lh7RW+UN9q42ZhTANoWNZhpNWnEtu+2j2bBf/vjd9+9Pv/nr3/I1o/RM5Q/h1j38oM3lis3ZrtutQv1I+n5YWnbgM9nvCv2PxzfvDnd7XcjdHMrS+3/yANsOhD5SgVMH1+Gm5gPHlLvGel9D6s3f86CmgeSXBxCgCd64Jtjg/vwY4C3UtxagM/pMDHDDNjvvf2FfY6mNDu5He2lbP4wfy6dxUMFBuHv3+9XWrpRIbzr9kpIIxG4MNHdt9+sw5Xs7v3B3RUUEI13n5GL1V0Z313dmB67SOTuvmnQkyv74ytxjFBe9cb7rxMsPROCjmvGV7aQcYL+f2aoBbzZowk4rkM2qdhTvJ5v0pbIcKo7mwl5/17364WEJdsI1/Vlv377PeDclekGsk88eXNW/ddLBPFK7prmM+r+IkJkB9f0B9eUbzTOt5qP/icbJ/3Oa/JeKbh7eGHRWbWvFa+8q0GTicHNkOm9it9lck0H73t4uACps+5HaiSwLu6Y0nigGmELdkqEa2inVHAss18kjPuU/JxIiZedExMzsJMSD6AOF2kEFwxnWuFQatu7wOVr1N2JzLjMx+yaQklE1zUdxy77NcZb7EBJreJGN37Fnr6QeuN2Hy9kC+zl7DTzljLOhZV9aPoaF+fRURHN4tyvHGaKzJWVoGvdX7rEemHZz1VImsa7dTdkS/O9Cs5pG7eSMmG8Xwm0QWA5SZvR7I77MuyXSlj2IOGVCTrg21usBtNIAFD4uOZ8lceds0TZyX0Hb86PED1ONVF6c86dl1FS9/iSKSHL5NJm1BeYwGLDxwK7FDUEz9N9hjOixqfD+1Hoc6OdaAMFa9lbCPkci18jHOU4YfW6tEbqt9ZfWJhmafamSXFm25hwkqxGXkVHrz6YlBPkQlZ8dWmmfTEkFvsvfnaCs7fWGRPGv0GPdzE5x3VI2l/P12dmEvNeKslLiZ8muQh5Q/F4Sq7x01P3Ns+utL4XoVL7vXko177Wx/a+DgU27F3+CP0KVFwvseEcW9lip0BgnXrBXsH5yvpjO7b4heGfhc08Rwn+6XBnHR+Ayeeqqc7mA34VQ33yLY+3XYH7wdzT82efc+p2nSnd1ftgPj2QwZZvgVxh9gYspP4aswjokts3nGKHNtfoivtE8cO2SETMPA+WKEzOrRFyOiSAGH+84ULM+Pb+fzw2Aca8BeM/R89yeiQXOB8eWz3XtacuH80rbI+Vd8mBStmY7T72sriS9kzixpqaftU+slmwP9hbG58lMW1d/3H1JxLV90tTLeOysXDS8UaHSujJuDHLVpRwQnTblhndTTmbZfRLhZYlrSv5w3GHa6AjXq7MLVpuhtocsL5vjekD++jK2lnouXZQhboSuhVqKdC3jKRLDmWf2V9hJaocXrWxG8fvyuDxdJwAPNHbDojzTg96BILPtJEOnlQnXHkLSJeAlng8mLi5LHcYrs8KiFoV6qis7rMoS9UjGf39052JQLGmq+pvbd1qbFmP38931pBPmROcNmcmJJICVqOL0w3Mr2aKCcgWqXHAZR+hx9y3zgmXex771V/1PJnksUnZLN2HV7oEMnI1VB05IYDrMVb3s5DfmMMA3IelfNDHuUzTlEBCMVj3rmVF3MeFlJLaY958xuR5TkXlFcTbo8mAKpXmeBZyzLbBWmz3GcEWdZkpPIKODxantfJ8LCrdoH0K0vfvvxAjVtyxxug0CtjjCg+m7pkLIUsdzJq0dttvKe487Q+Y9J2cph6tWzxSjvCQ+cbKUJbxZPVWgC2s0rIc/I2VZGC6MwEpVHXynkAaDvH0ilrWKCmwGXenz+N55AJlHa/PUt11oAriP025ugtNHuazxi5O+s3n/RavmLrcuiMMGjpwdjg9aL4JKmplFqAn4E/uFb7vauOFwRFWvnLjRVkZ5JPl9Pbsdp98f9lPZtObPjMCKvsF4mnooRNzeI85z2WCehGYBMQkyisOMzFTSsKbiJx8zW2xpidHIwaE7uygn8WzoULN5+HdjFbOoq/K5AvT3dqxM7ojMQwl01ti0KKCM0p9FWTGla5MYCRqvnVOzaMj+5MoYbQwSTpkHH/aNFx9ULGElk2IfFSJq4iHZUuBxhzrBTzGOuZ7CgtRRv80boJ2qotnJyXHjFbYE2ZasPKg2KhQx2HcZmMSLxFqEqgLuthN57MUgoXwBgErqqnJJ/iWSabNmjwhNTWnvtOwORqZ3BfIY5U5Kvqd8lh5QNI8bM9EskYLXo+3eD1so9hDEGT/a1hKY+GO9/NWEBKBllZ1PFGmbesPbCoBqAGnQKexfIT05Ge7VotmC3lU6SwKWSegxWRsoAM5jhllKp6NpCf7zaS4PrmGFcA61mZ1EtbfyBYuu5LDsjf+1H2PnHNLsdAX8GvKPLm5qwRS6mu3WjnncnWwSVcCkyogFWTSdK+zb+o5/2A+SrI7gD8xnaTDMuuNRljH0sZ2mXdTsbBiWiGckdNKzF8KrDFdH/OtxPlUQBdGKeVyGENZ140W9aA4jluZsAp9sWJohfZJLz8hCB8HZLnSrhhvwcZpJ9enxg0ZujEc/Cqlh5ivlsPf5LnSY8O+1ErPPBnp3q5uyGaFailPfhLup613+oLxlil8qFB3JoXSjLRD5KRcBeRx7lqD0/S3ObqDMr1EKnORTn9jKj4a6ehb7JM13TpEBlnZJahrnDoJllez823vX5UtdVWON3OTzConILH9O8Jby97Jtg0JM7Un/sfwUsYtex1E5RRTFzdsYR6ioRG0dy2YLYo0hVrj3AvzCo0HJdPK1KmGFRR1MXoYROC3Gb3Ht4IdvuhLQDoRiIE613ae8v5RNWVX1+KXF2t81YbJ0Bl76GX1VFPU3+Mco8414WzgzvwC8CCvnfwG0naPVscbJHIOQZmIEZVr16ty1rHY5GrOL9iKKtENnQtQQQCoRbqRPhU3D6sAUV5hP00gejoBofUMUdXOdv1COecpfFj893+i/giUIEYa3iwCUY7nl3dVpzzwUPqtp/Ch5zQ3idBH+tCZyB3M4bHMLe3VpY/97awA5bDTp1B5NkiAPlp9FODvapTGNMxnTkLqC5GXneIKOUHx7IkMkzq5Rr0kLimfZgvFO8J5NJAiyuOr7aabaKH83bpmopkOc8fjo7DkjiWUHgIzBQQHs5b9RdpTAX2Hzgx0JyKlPvsG5pmBIrbiwp4a5eWQJpLEIa8tIG7P5+kFpNFQKwFOkDQA6vrUXPqwE6KMmShVCFa2XwuBCSaLDRhWhnNUvIwn6DmFpH8z8yVW2l3GRx8a5k2BYoKQ4BppzRCgZZL99K598norhBpq5TgrSQUnfyZ3JvZUGQxhnnQy3KBhqycyz8LSxMYGgC/OHIXHf/VoQP8aNCC75pQVWF0lioqXEtMAbZXXk9ZCBZ2wDODOgFiqlFQ/prbvdIXJNzsWZ1cnbsYuLieGkkNLeLZ6TxMRBkQHANt20C+Rt97Vs1n2XRhah9YmMzMg89oQAesalv/5yRzOT6HS0kDHep00EdsxJTTKhK8skZryhPuBBVoZwzZP7CmZoL8Ww74rrv63X0zA19OHboFDIeHjv6uEHld58Zp0nUt2+9kAJyqxMs+VzaX788V3dQwkiRORNU8sHoWtpFiyArRNTzwJ/KD5EFUctOzWnCa9wlg+MTFY/wtTsq+we1FevqJ9kVC8+HH7oiP1DKA2iRHxCuh6WxabdwCqLGm/sMGU+nkLoRL4o3say7vKjUR7qPrS03z6fTU4ONymoRbmgqOWNwt6aTOxPsD57kBYtM8Ek0SF6oDHvMbrJWy9ConJ/NF9kS5GXl1iMfYNXfQ0kG6PrdQwFuYMiN9kvkkxanCTMcQ5E3IqCfRWtmzJTyvoal1ZkcFCJ9aoctwSq8wltmDCUkCMQna7XvoKu0clWnUP1isz16v7sOp2vTpLnynl3I4vQGINEBoRcgbOyGkS82QSMwk+KeQ6fs2wf++NeezWPK47fferwji1zvYM3FbYG/eyj+++9LNkbz6N7rLr+4cRTKdJyKP13Ho9WQ/pZtQRIplsWTtzgkfDwHaQ3aBanj31CwHrRkbycFZCHT2fxR5nZSGganVB35m6zCZ0psyWMxZC8NxyxpXnLDso8Fgus1EYs2vS9FwuG8EtfiMuE4xX85ZzYKoMHqJE4GQdRwPRBVj4Hq8e8pCosyV0H126oW7JJATWQFOgYMkAoYwi7sDjQgyDErYhAC1ZkLlf/e2VmbWVeoI1NhKZqflnvmASm4mVuE9wwXxj+c6EQYBLCYT+E+FGKHObYMiyUnyT+Koy2lTaLxfYf+o1GaMq/u1IbBl7AJLmCSR9khP1tzgMq/4eYzr6Giddqr5pXmOYmUcDml5MZXezUUskiZ8BIWKFbXi4SvppwRvu0+Yfpf8uSg7oqSkIqO+A5ZsDUCpgqkd/2CsLlG+gSN7lfHkXzs7ji83XmfXKTGaguGE7G1Znq12mUDZkHeb0Ii3rMo8tKIMHtPtTn7JETgdY2+WgkRAjNDQQhnFHZpEjkFwqk8pBnZpyVwoUkOobWCsO1lXounbS5SIn1jnARjpw0yZPtatAFc41qIW9BFhClGYZr1lV91HWgyqjqv6zt8i0AAujVtAgobxIL0S5CbaBkSeaC/ODT5R32WiPD5oU7eTIZx0kURNgkxssAAbLMdLj36oVMCoWhqgBvTfSpHHrGg6b64DgALn6neSkPgaeyGUMZM7tQa60f0v7vx7mXwN1hQoN+JZJ3cjketb6Autva9jWa9AKyFPpDMcVijrmxDvioXq3zri98nrSFA9G6oUmqDqjfgC0lQM+rOWotaEMd0RdujViaGMCNi3AQodfRnKt4zRXcMo1ljVg2UvLVu3MwRF+/Llt/AZsML02s/NJmD9QZjHhimaM0pObvklnDRGs7Khv4ocsPUUxFqwZg5gmnS0eXfs+re2CmyMCxn2hkFhGcUC6mqsVFqubr7qy5A3yJUCvO7SuIKZXqMWjqLoDeIk5JimA3rWFKPxKLG+YCHNp24pnG0eunAC6ja9uEu/u6MKnyt930OgGNGHi8BXydwp7gKDRYnfoW8EZenC+v1XbtlKKXCYKsDBftkdpc/uBo+XObmJ/j2Df7AZ0WzTl6VDZQO0rLBs+akdWn5DGhU0jgqAPhGwKdyZDW2cyARUPCOs/ucNa6DkjlhsjJC+bQ+chOMUtohB7EkJrTICXOoQ8GdRA4PIrGqHnF2mZZj2qNdRGQ0Qp5Fz5qtdcKagE+VJXK7r5jQXY/TJiCJkRplYTUC57bkgxepX8MypPmAeIvIswYrdPOMmqgFqARpkLYBsszC34WAGBrRMLYWrwCsL+wi0EE/IqiPIsKkdPc5CZEGkMKL8CAJLjH/IkZYcYDwvzA4QFpKwfpTWUwrzscvqnDURkTDtxfq30Qm2FhWJCjCr4wOoclruOK+gNAofv22FJ8CklQg4vN5FN8iAlieldQj+jBgDTjr/IZ1+dXW9cnLvunVEuCq7xIw/7v/2zwMrtcuii6FRbw7ap1cDCtnvwXXWCBIRs1sKemhgViX15dYYFOhukUtEZGZAPHacL3lnUvHdhcsMdwYGKjwEveofKgixeZpuSDiuiHmEAWQfara+j2FNPk6qsACZRBc427VUZshktmHVn50zmyh4TG05hlt36R4h8BiCLKSOlpCjex1koo1Rv5uwPVCRIq3Sxfb/nc+SFyLcDxbrOAvXtKXazqxtLNOWbYM8shkBEcTiVEtl/9BRZsBm3p5K8osaNyp6pB6Omw47BgCA+4sigXWcEyACca2GdQzpOMrTzBgyX6aezkdO8zxrl0K6T6dYXbL3EmiCv3nddEe1VnXrQvFHhdkMCZNkffZeflQtysRZAq15uamR1xx8U9weSWJWHIU+IgPDVvkfd+QclSDSgcP5CHtqdz5FD9rvS2Ig0M0PD0uqnLU8i4FHejEv1WUAs16jKmXm7b/Kgmag/MZmb8QiFasUpFBhGq5xnVuUxOg03gLHLKQ6chpj08vQyqxxdbkjgjUBEx8idmZYgtAa1ov6wBp1hxtI9ZaEVQ8CvJBPxUJU6ijwtNkfVw1rrpDYk0H3oN5Vq3a91B25Mc9+j3DwEpc4YXwfwhhEhN7gWnLCBYtjqzhezPTqN+xdStwbPpz5FAt1uECBbRBuJomMKOSGZ6SkxfieNQ9R7IN0Qid9qmkxDFgkGFp6V0zPJL1SYqACxF1utmNmypAGOQYwEoVI9jR0wJzqjQQXdqTmlM0XeoyN58sqaXZfkuaKF1QEyd6X72ruvdkGKmX4d0hhjOqTujRCsCyK3zkcF+Yh14jrIkyryeuD/Y6jFzmcAzy/MqzH2yuYJMlW/FkpiJENjhTcgVpBRdXWLFGR3J0RQhpJ5H1GmaarrOJEEmTNCd+yLfpNFne8jU6CkLG8ktw5PFpCWT9crCUnzmeLtyOlZGXaBQkemiQ2o8N35dEHkq2DxaSWPQga6A0WUOYC0ZabOpQ/nhlkorSFIa1BWy+W6duuvWYgkU/AsRTWeyEPRWHyVUzB4sn1Yb4nzd52VqnZsJmcICsEWJSb0oHyY4txcmQ1kToCPkTOB+yxuISHShDgyIHISurFBz/bq/IYVuCKdPsGFVDtRCQrrGSZEktVpQUtQ6sYkV1foow2ASBpg+RRKE7L+2aDQsXwrOKQMORCmBjB6EGXiCeZEXJKMthqq6aoEpCQt3+ZTv3pDxUvPSKhkBi48fS9Pqv4VUp6UHLcMAJEHPoT1RoRSSToDp29FcJGvwNe9xAHdSpyMAXpJkFzIFc8R46XztF2ihHj3c2U+ZvcOiFAgPAHyaqd+LXdtbuWbOpNDQMEMXWe/zBy9IKZLULXD8iZulxtZijXgd/aN/D2ti2d8Z1ZuqgzfAIldzxbo4DmucTECPK0AmEOtGCD5KJgyAnMo3JpZEkVmiysQ0koPWsN0uiKbvtlGqi1XLlY/RgftcRNh0MSVIm/rO0EBNhhNvuJTX0FjT/OuWgDDhqK0YRnYj8VjFCaJnMD5Bko1hWh7FCSaoa9H3ZltqUhm6ofp/wM2MhVrbHQQD44IkSd6wAmZIvXsNN+UVRoxoMTmdkHForJARRhDEwD7vNP7EtMNLNjROARjQYZ60+cD5FyWeWxFBmkh4Q/tEpmmXGPzSInC7lmNukKFGmxjduy9ZMpbK435aLSHym7F45eQDkIdIip9k0EypIUtKIT6hqigD+WH4CaqDOBZGZvg4qHZ8ZXmD6gYEJIwEVvkrRcvPNFEJ3ga/AUcqALrmMh41AttupV4EKxMBL6IMKUEPilkPAFpI6qPxcivnUV7EXqS2DGhtE6+Q3kNxdW2QgGUlSUaynQeDOc8+ebCUgy++Y1QSox4EcdKHKOVafyrFU11GEqP9fxBPjQhySsPocgrVF4U5lUmCqE810rsLKmTWDqnbcrsu2v6hQ7M56HWM0HGJC1YT6BMNW8HZwXRFgaGp7mFhGjeBRnMXB3KOAe7Ue+qxNWrvPFCTyGYXmHspcyq1wAhWmJ/y5bPKDNXd3WfwgQTsnheCWRXAaQAdenwZ/oKbgBXPjMy1+pTLilmrhS2DjXmcvUYQYFLLzdaJVmYq42QY7voAlzENc5ZKHenGn1eAJ4BLi6wBLTOQim4rUyfyaNsqOJK2aLmsLQbUnJrLBWVqd3vjH+E1FWUFTn68xAV+afj1XfIYKJslnTnG4MMQ5lIIFeagXllzNl+JZRgqN4FyInofHZniX3zW/zipFiprBCB/xWM22IRClqvSipZYLqWUkti6KP4YUEDouedhWjDgcs6yCbkvPwuIectOdNAw4GRNFLP9n93Loghk3D5mZj0V2LOB6KnooCR1mRwNgnqCLvXaSwAIY3lqjMlVkLfoDEPNBxZbx6IkqOMFRweqMVRB9pPODdTdgjU2NCT47kizKdPdyvHfTp/ulxJGPT5mZljlhlTAlYsJf6BEL7P4foE9SByEMDgMnPoEBH485u+4leMwYWdcFwDIjDiAyqrPGfS053yJREbkAp0KGMXIXPG4S7xRjM/8H8mbASAd6hTkoQz7/w8q1R/09tk0teTHGcL2OWKnxZ9Yy0xtcQ0hx6CtOvkTHW70AhLBAqlQqoyg+VATP4l7HFxw+LpVBQNKHN5GVOLKhafbUEWIoVK2U6IzE74S5M4ob62x0N2Ocm9QnL5BnjIXG87qR60sWMf9Emucv5K5P/H/NDy0onymmHa5pSMsYFgodU5EtakVyCZsbAaD0SMZw2QBi2OBENtXplDn1cygqQ0rOJuj//p8ibn8O31pIkVQO8FrIXuN5g7KC5UVa3ScG3jDKBmcgGi0TygsFI0yAoJLXerCsmweb6PnSlAMdZQiA6BVwJUHhZaGsPkc8e5TrKZlRqbFrIKfJbkchjkBZt0dZqzAqG9o7ride0Pcird27Rs1iDxcu8afvFtXWc6xSClU+5akQB4F2e64Uk77kRw8nj5bZlSVG16BSRUZmAAIlrTRn2L6qwrKEtZNkzm0lLGKjcoO9UZWLOiWM8pfayvBy2qzAG1cC2e5yLf5BrfYap+RYOpYvITI/7wuMHUjEi4PZlZ/UWP6aWHlPg66BuGndpQdnzBkfoDh+JGdshtYHx4IBUcyuAGx8Hg/uhkezJRx6UMjcU2vwAUDbkq3zIT90k3zSum9GA79emWUaVu9GZqSETl1bE2XDlulrw/szBAgOH9K2o/omM7l0ER7A5R6nex1dWNpCM5N9rhiDeJR+Rd75ybJx1rG5owVifyx3Luz+Wmi4e8on5qTnmpnJzS1b+yjbxMPXZeeUNiIacK1amE9B1hGcpLDLJDNiqlDL03xuyZLqSogUX+K5UKb5SuTXEyok1mrWdhtFj/m0ryHLOPX8NSjB5raa7IwXdNuKjKJZAn7mgdH9SMKCHzAHXE545Cj4XBrwA+169kfqapFKWZRanvHAlD7Ddyzm4MCHiQjPg3q0wFXbi5lb+thbhXtvSj6q1+pOV0SiRKOk+1gQS6EGqBBJy/Dzu1V7TfRJ+dRAtlxoA3TddMlCt5LJqYx1OQiN+bIXzXx3oFwB6wvUYoHYiuwycOcr8FKUHIRLc4FkI8MuLqQflxgsQzbh4aU0g7tgEqmKJS0GWyWetUxr+805mfX9AFNgZRIuZp4mN5pD//rFAqC4O+ileItiodwmzeekelcF97ertywJrGlEgnjMzKWzPzAxWYJuexCxlDmK4c+so1dv4zSML3J1NEiKt594UgBQqkgKsP2zNyfufGm4KYVf55017VsYo3sk43Lb9iJoSt8hiAJ/kqa192AUYNtbKyUOy+TbjEgBIIFZIq5IBUWtmRd6AgV94N5MnYGRXsk1Yg5RW2JiPYnXVxOhO1CWldMrHnxlg0hPyo7IXMEi3jnqeJ1UCfgUTxg/LvfbZiZVR7RBIbxqULmUiEpMSfRK01aHkBixWVNRbYO44xHp8QHLuDaZ5gOKwsoTKWoNyt42NPOFtC4kqXAkEhERjT05mulO8Xt22gwBUDfpDw8upAbM/zfPd4EE6i9Sf2m18itsGIUI0yLtqRvmDGgeKXL7tKqPJxnZsjLu//dpJpvQG9r+N7gXle5XyhHlECX8nLl9Oa8hSvZrwMtrl2f0JgFI7ri6MiPHINWpwpuKgfy1c5A3ojlnmjUsKYAoUA+PqAr+hUFgrHoHrYDaTcBPv9hs3EuhTfBvqh+9BvQDnmUTDMCbVTUpyxI1RKmp5VYhk6yI0IiRGViTIBU/NxakzfXVj3APp1Eyqlu747Q4SVjKc4midqToloQTTiGvrmFtC06dgvIFG7IaAiP1/ujj6QfZUHyaEvGa9HS2khrey/6lyRilAG3ORlS0ylqz0bQ4LjZANAiI0L1QBHhoRPqGB7LorIxVr6QhajEBppY8/t/Qe1LSo6Jy41P5o3tcNF0yqLW48QJ0UZXeRK9lh7RW+UN9q42ZhTADosNZhpBc260rvV9t/++N13f/uH7/4fw/xwfA=="
)).decode()

for name, text in SOURCES.items():
    data = text.encode()
    got = hashlib.sha256(data).hexdigest()
    assert got == EXPECTED[name], f"{name}: {got} != {EXPECTED[name]}"
    (WORK / name).write_bytes(data)
    print(f"{name:<28} {len(data):>9,} bytes   sha256 {got[:16]}  ok")
