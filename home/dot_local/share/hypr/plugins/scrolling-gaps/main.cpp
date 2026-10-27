// Hyprland 0.56.2: per-window scrolling gap geometry, without fullscreen.
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/desktop/state/FocusState.hpp>
#include <hyprland/src/desktop/history/WindowHistoryTracker.hpp>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/desktop/state/ViewState.hpp>
#include <hyprland/src/layout/target/WindowTarget.hpp>
#include <hyprland/src/layout/algorithm/Algorithm.hpp>
#include <hyprland/src/layout/algorithm/tiled/scrolling/ScrollingAlgorithm.hpp>
#include <hyprland/src/managers/fullscreen/FullscreenController.hpp>
#include <hyprland/src/output/Monitor.hpp>
#include <hyprland/src/state/MonitorState.hpp>
#include <cmath>
#include <stdexcept>
#include <sstream>
#include <unordered_set>

namespace {
HANDLE handle;
CFunctionHook *positionHook, *borderHook, *roundingHook, *hitTestHook;
CHyprSignalListener focusListener;
SP<SHyprCtlCommand> stateCommand, hitTestCommand;
bool enabled = true;

// Focus belongs to each workspace, not to the desktop as a whole. Leaving a
// monitor, opening a scratchpad, or focusing a float must not resize its last
// tiled column. Native history also preserves this selection across plugin reloads.
PHLWINDOW effectiveFocus(PHLWORKSPACE workspace) {
    if (!workspace || workspace->m_id <= 0) return nullptr;
    const auto eligible = [&](const PHLWINDOW& window) {
        return window && window->m_isMapped && !window->m_isFloating
            && !window->isHidden() && window->m_workspace == workspace;
    };
    const auto active = Desktop::focusState()->window();
    if (eligible(active)) return active;
    const auto last = workspace->m_lastFocusedWindow.lock();
    if (eligible(last)) return last;
    const auto& history = Desktop::History::windowTracker()->fullHistory();
    for (auto it = history.rbegin(); it != history.rend(); ++it) {
        const auto candidate = it->lock();
        if (eligible(candidate)) return candidate;
    }
    return nullptr;
}

bool fullWidth(const Desktop::View::CWindow* w) {
    if (!enabled || !w || !w->m_isMapped || w->m_isFloating || w->m_group
        || !w->m_workspace
        || w->m_workspace->m_id <= 0)
        return false;
    const auto target = const_cast<Desktop::View::CWindow*>(w)->layoutTarget();
    if (!target || !target->space() || !target->space()->algorithm()) return false;
    auto* scrolling = dynamic_cast<Layout::Tiled::CScrollingAlgorithm*>(target->space()->algorithm()->tiledAlgo().get());
    if (!scrolling) return false;
    const auto modes = Fullscreen::controller()->getFullscreenModes(target->window());
    if (modes.internal != Fullscreen::FSMODE_NONE || modes.client != Fullscreen::FSMODE_NONE) return false;
    const auto data = scrolling->dataFor(target);
    return data && data->column && data->column->targetDatas.size() == 1
        && std::abs(data->column->getColumnWidth() - 1.F) < 0.001F;
}

bool gapless(const Desktop::View::CWindow* w) {
    return fullWidth(w) && effectiveFocus(w->m_workspace).get() == w;
}

void position(Layout::CWindowTarget* target, const Layout::STargetBox& box, uint8_t flags) {
    auto adjusted = box;
    const auto w = target->window();
    if (gapless(w.get()) && w->m_workspace->m_monitor) {
        // The tape's logical footprint stays untouched. Only the active window
        // expands, respecting panel reservations and the current scroll offset.
        const auto area = w->m_workspace->m_monitor->logicalBoxMinusReserved();
        const auto normal = target->space()->workArea();
        adjusted.visualBox = {box.logicalBox.x - (normal.x - area.x), area.y, area.w, area.h};
    } else if (fullWidth(w.get()) && w->m_workspace->m_monitor && !box.visualBox.empty()) {
        // Focus changes must not reflow terminal columns. Native scrolling has
        // already supplied the gapped visual box; retain its height and the edge
        // facing the selected column, putting the extra width offscreen.
        const auto area = w->m_workspace->m_monitor->logicalBoxMinusReserved();
        const auto reserved = w->getFullWindowReservedArea();
        const double width = area.w + reserved.topLeft.x + reserved.bottomRight.x;
        const auto focused = effectiveFocus(w->m_workspace);
        if (focused && focused->layoutTarget()
            && box.logicalBox.x < focused->layoutTarget()->position().x)
            adjusted.visualBox.x -= width - adjusted.visualBox.w;
        adjusted.visualBox.w = width;
    }
    reinterpret_cast<void (*)(Layout::CWindowTarget*, const Layout::STargetBox&, uint8_t)>(positionHook->m_original)(target, adjusted, flags);
}

int border(const Desktop::View::CWindow* w) {
    if (gapless(w)) return 0;
    return reinterpret_cast<int (*)(const Desktop::View::CWindow*)>(borderHook->m_original)(w);
}

float rounding(Desktop::View::CWindow* w) {
    if (gapless(w)) return 0.F;
    return reinterpret_cast<float (*)(Desktop::View::CWindow*)>(roundingHook->m_original)(w);
}

PHLWINDOW windowAt(const Desktop::CViewHitTester* tester, const Vector2D& pos, uint16_t properties, PHLWINDOW ignoreWindow) {
    const auto original = reinterpret_cast<PHLWINDOW (*)(const Desktop::CViewHitTester*, const Vector2D&, uint16_t, PHLWINDOW)>(hitTestHook->m_original);
    const auto found = original(tester, pos, properties, ignoreWindow);
    if (!enabled || ignoreWindow || (properties & Desktop::View::FLOATING_ONLY)) return found;
    // Native floating/special-window and popup priority must remain intact.
    if (found && (found->m_isFloating || found->onSpecialWorkspace() || found->hasPopupAt(pos))) return found;
    const auto monitor = State::monitorState()->query().vec(pos).run();
    if (!monitor || !monitor->m_activeWorkspace) return found;
    const auto focused = effectiveFocus(monitor->m_activeWorkspace);
    if (!gapless(focused.get()) || found == focused
        || (found && found->m_workspace != focused->m_workspace)
        || !focused->geometricBox(Desktop::View::IGeometric::GEOMETRIC_CURRENT).containsPoint(pos)) return found;
    // The expanded content covers a neighbor's logical footprint (and sometimes
    // a few pixels of its rendered border). Re-query actual geometry, excluding
    // that covered neighbor. Native eligibility, modal and query flags still apply.
    const auto visual = original(tester, pos, properties | Desktop::View::USE_PROP_TILED, found);
    return visual == focused ? visual : found;
}

void refresh() {
    // Include unfocused workspaces on load/unload too: their geometry may now
    // qualify, or need restoration when the hooks are disabled.
    std::unordered_set<int64_t> visited;
    for (const auto& window : Desktop::windowState()->windows()) {
        const auto workspace = window->m_workspace;
        if (workspace && workspace->m_id > 0 && workspace->m_space
            && visited.insert(workspace->m_id).second)
            workspace->m_space->recalculate();
    }
}

CFunctionHook* hook(const std::string& name, const std::string& signature, void* replacement) {
    for (const auto& match : HyprlandAPI::findFunctionsByName(handle, name)) {
        if (match.demangled != signature) continue;
        auto* result = HyprlandAPI::createFunctionHook(handle, match.address, replacement);
        if (result && result->hook()) return result;
        throw std::runtime_error("scrolling-gaps: could not hook " + signature);
    }
    throw std::runtime_error("scrolling-gaps: missing symbol " + signature);
}
}

APICALL EXPORT std::string PLUGIN_API_VERSION() { return HYPRLAND_API_VERSION; }
APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE owner) {
    handle = owner;
    if (std::string(__hyprland_api_get_hash()) != __hyprland_api_get_client_hash())
        throw std::runtime_error("scrolling-gaps: rebuild for this Hyprland ABI");
    positionHook = hook("setPositionGlobal", "Layout::CWindowTarget::setPositionGlobal(Layout::STargetBox const&, unsigned char)", reinterpret_cast<void*>(position));
    borderHook = hook("getRealBorderSize", "Desktop::View::CWindow::getRealBorderSize() const", reinterpret_cast<void*>(border));
    roundingHook = hook("rounding", "Desktop::View::CWindow::rounding()", reinterpret_cast<void*>(rounding));
    hitTestHook = hook("windowAt", "Desktop::CViewHitTester::windowAt(Hyprutils::Math::Vector2D const&, unsigned short, Hyprutils::Memory::CSharedPointer<Desktop::View::CWindow>) const", reinterpret_cast<void*>(windowAt));
    focusListener = Event::bus()->m_events.window.active.listen([] { refresh(); });
    stateCommand = HyprlandAPI::registerHyprCtlCommand(handle, {"scrolling-gaps:state", true,
        [](eHyprCtlOutputFormat, std::string) {
            std::string result = "[";
            for (const auto& window : Desktop::windowState()->windows()) {
                if (!window->m_isMapped) continue;
                if (result.size() > 1) result += ",";
                const auto current = window->size(Desktop::View::IGeometric::GEOMETRIC_CURRENT);
                const auto goal = window->size(Desktop::View::IGeometric::GEOMETRIC_GOAL);
                result += std::format(R"({{"address":"0x{:x}","gapless":{},"current":[{},{}],"goal":[{},{}]}})",
                    reinterpret_cast<uintptr_t>(window.get()), gapless(window.get()), current.x, current.y, goal.x, goal.y);
            }
            return result + "]";
        }});
    hitTestCommand = HyprlandAPI::registerHyprCtlCommand(handle, {"scrolling-gaps:hit-test", false,
        [](eHyprCtlOutputFormat, std::string request) {
            std::istringstream input(request);
            std::string command;
            double x, y;
            if (!(input >> command >> x >> y) || !std::isfinite(x) || !std::isfinite(y))
                return std::string("usage: scrolling-gaps:hit-test X Y");
            const auto window = Desktop::viewState()->hitTest().windowAt({x, y},
                Desktop::View::RESERVED_EXTENTS | Desktop::View::INPUT_EXTENTS | Desktop::View::ALLOW_FLOATING);
            return window ? std::format("\"0x{:x}\"", reinterpret_cast<uintptr_t>(window.get())) : std::string("null");
        }});
    refresh();
    return {"scrolling-gaps", "Stable-width scrolling columns with workspace-local gaps", "Tijpfiles", "0.1.5"};
}
APICALL EXPORT void PLUGIN_EXIT() {
    enabled = false;
    focusListener.reset();
    refresh();
}
