// Exercise the last-response race without a GUI, torrents or private data.
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <functional>
#include <memory>
#include <thread>
#include <libtransmission-app/favicon-cache.h>

using Icon = std::shared_ptr<int>;
static std::string cache_dir;

namespace transmission::app
{
template<> Icon FaviconCache<Icon>::create_from_file(std::string_view) const { return {}; }
template<> Icon FaviconCache<Icon>::create_from_data(void const*, size_t) const { return {}; }
template<> std::string FaviconCache<Icon>::app_cache_dir() const { return cache_dir; }
// Model the UI queue being drained before the curl response callback releases
// its reference. The unpatched response-owned worker then tries to join itself.
template<> void FaviconCache<Icon>::add_to_ui_thread(std::function<void()> callback) { callback(); }
}

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    cache_dir = argv[1];
    if (std::filesystem::exists(cache_dir)) return 3;
    std::atomic<bool> finished{ false };
    {
        transmission::app::FaviconCache<Icon> cache;
        // Loopback only; closed ports return an empty response without a server.
        cache.load("http://127.0.0.2:1/announce", [&](Icon const*) { finished = true; });
        auto const deadline = std::chrono::steady_clock::now() + std::chrono::seconds(20);
        while (!finished && std::chrono::steady_clock::now() < deadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        if (!finished) return 4;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    return 0;
}
