// Hyprland 0.56.2: per-window scrolling gap geometry, without fullscreen.
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/desktop/state/FocusState.hpp>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/layout/target/WindowTarget.hpp>
#include <hyprland/src/layout/algorithm/Algorithm.hpp>
#include <hyprland/src/layout/algorithm/tiled/scrolling/ScrollingAlgorithm.hpp>
#include <hyprland/src/managers/fullscreen/FullscreenController.hpp>
#include <hyprland/src/output/Monitor.hpp>
#include <cmath>
#include <stdexcept>

namespace {
HANDLE handle;
CFunctionHook *positionHook, *borderHook, *roundingHook;
CHyprSignalListener focusListener;
PHLWORKSPACEREF previousWorkspace;
PHLWINDOWREF normalFocus;
SP<SHyprCtlCommand> stateCommand;
bool enabled = true;

// Scratchpads are overlays, not navigation away from the underlying strip.
// Resolve its own last-focused window even after a plugin/config reload.
PHLWINDOW effectiveFocus() {
    const auto active = Desktop::focusState()->window();
    if (active && active->m_workspace) {
        if (active->m_workspace->m_id > 0) return active;
        const auto monitor = active->m_workspace->m_monitor.lock();
        if (monitor && monitor->m_activeWorkspace)
            return monitor->m_activeWorkspace->m_lastFocusedWindow.lock();
    }
    // Focus can briefly be null while a special workspace opens/closes.
    return normalFocus.lock();
}

bool gapless(const Desktop::View::CWindow* w) {
    const auto focused = effectiveFocus();
    if (!enabled || !w || !w->m_isMapped || w->m_isFloating || w->m_group
        || focused.get() != w || !w->m_workspace
        || w->m_workspace->m_id <= 0)
        return false;
    const auto target = focused->layoutTarget();
    if (!target || !target->space() || !target->space()->algorithm()) return false;
    auto* scrolling = dynamic_cast<Layout::Tiled::CScrollingAlgorithm*>(target->space()->algorithm()->tiledAlgo().get());
    if (!scrolling) return false;
    const auto modes = Fullscreen::controller()->getFullscreenModes(target->window());
    if (modes.internal != Fullscreen::FSMODE_NONE || modes.client != Fullscreen::FSMODE_NONE) return false;
    const auto data = scrolling->dataFor(target);
    return data && data->column && data->column->targetDatas.size() == 1
        && std::abs(data->column->getColumnWidth() - 1.F) < 0.001F;
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

void refresh() {
    const auto active = Desktop::focusState()->window();
    if (active && active->m_workspace && active->m_workspace->m_id > 0)
        normalFocus = active;
    const auto focused = effectiveFocus();
    const auto current = focused ? focused->m_workspace : nullptr;
    if (previousWorkspace && previousWorkspace->m_space) previousWorkspace->m_space->recalculate();
    if (current && current != previousWorkspace && current->m_space) current->m_space->recalculate();
    previousWorkspace = current;
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
    refresh();
    return {"scrolling-gaps", "Focus-local gaps for 100% scrolling columns; no fullscreen", "Tijpfiles", "0.1.1"};
}
APICALL EXPORT void PLUGIN_EXIT() {
    enabled = false;
    focusListener.reset();
    refresh();
}
