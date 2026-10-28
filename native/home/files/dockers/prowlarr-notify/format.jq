def clean:
  gsub("[._]+"; " ") | gsub("\\s+"; " ") | gsub("^ +| +$"; "");
def before_tech:
  . as $text |
  (try (match("(?:^|[ ._-])(?:[0-9]{3,4}p|4K|REMUX|BluRay|BDRip|BRRip|WEB(?:[ ._-]?(?:DL|Rip))?|HDTV|DVDRip|H[ ._-]?26[45]|x26[45]|HEVC|AVC|HDR(?:10\\+?)?|DV|FLAC|MP3)(?:[ ._-]|$)"; "i").offset // null) catch null) as $offset |
  if $offset == null then $text else $text[:$offset] end | clean;
def cap($regex): try (capture($regex; "i") // null) catch null;
def token($regex): (cap($regex).value // "");
def size_label($bytes):
  (try ($bytes | tonumber) catch 0) as $n |
  if $n >= 1073741824 then "\(($n / 1073741824 * 10 | round) / 10) GiB"
  elif $n >= 1048576 then "\(($n / 1048576 | round)) MiB"
  else "" end;
def release($e):
  ($e.prowlarr_release_title // "Unknown release") as $raw |
  ($e.prowlarr_source // "Prowlarr") as $app |
  ($e.prowlarr_release_indexer // "") as $indexer |
  ($raw | cap("^(?<series>.+?)[ ._-]+(?<episode>S[0-9]{1,3}E[0-9]{1,3}(?:-?E[0-9]{1,3})*)(?:[ ._-]+(?<rest>.*))?$")) as $tv |
  ($raw | cap("^(?<series>.+?)[ ._-]+(?<episode>20[0-9]{2}[._-][0-9]{2}[._-][0-9]{2})(?:[ ._-]+(?<rest>.*))?$")) as $daily |
  ($raw | before_tech) as $front |
  ($front | cap("^(?<name>.+?) +\\(?(?<year>(?:19|20)[0-9]{2})\\)?$")) as $movie |
  (if $tv != null then
     {icon:"📺", title:(($tv.series | clean) + " · " + ($tv.episode | ascii_upcase)), detail:($tv.rest // "" | before_tech)}
   elif $daily != null then
     {icon:"📺", title:(($daily.series | clean) + " · " + ($daily.episode | gsub("[._]"; "-"))), detail:($daily.rest // "" | before_tech)}
   elif ($app | ascii_downcase) == "radarr" and $movie != null then
     {icon:"🎬", title:($movie.name + " (" + $movie.year + ")"), detail:""}
   else
     {icon:(if ($app | ascii_downcase) == "sonarr" then "📺" elif ($app | ascii_downcase) == "lidarr" then "🎵" else "📥" end), title:(if $front == "" then ($raw | clean) else $front end), detail:""}
   end) as $media |
  # Preserve the natural resolution / source / codec order, not alphabetical.
  [($raw | token("(?<value>(?:2160|1080|720|576|480)p|\\b4K\\b)")),
   ($raw | token("(?<value>REMUX|BluRay|BDRip|BRRip|WEB(?:[ ._-]?(?:DL|Rip))?|HDTV|DVDRip)")),
   ($raw | token("(?<value>H[ ._-]?26[45]|x26[45]|HEVC|AVC)")),
   ($raw | token("(?:^|[ ._-])(?<value>HDR10\\+?|HDR|DV)(?:[ ._-]|$)"))] |
  map(select(. != "") | gsub("[._]"; "")) as $tech |
  size_label($e.prowlarr_release_size // "0") as $size |
  [($media.icon + " <b>" + ($media.title | @html) + "</b>"),
   (if $media.detail != "" then ($media.detail | @html) else empty end),
   "",
   (if ($tech | length) > 0 then "<code>" + ($tech | join(" · ") | @html) + "</code>" else empty end),
   (["Grabbed by " + $app, $indexer, $size] | map(select(. != "")) | join(" · ") | @html)] | join("\n");

with_entries(.key |= ascii_downcase) as $e |
($e.prowlarr_eventtype // "" | ascii_downcase) as $event |
if $event == "grab" then release($e)
elif $event == "applicationupdate" then
  "⬆️ <b>Prowlarr · Updated</b>\n\n<code>" + (($e.prowlarr_update_previousversion // "?") | @html) + " → " + (($e.prowlarr_update_newversion // "?") | @html) + "</code>\n" + (($e.prowlarr_update_message // "Update completed.") | @html)
elif $event == "healthissue" then
  "⚠️ <b>Prowlarr · Needs attention</b>\n\n" + (($e.prowlarr_health_issue_message // "Check Prowlarr health.") | @html)
elif $event == "healthrestored" then
  "✅ <b>Prowlarr · Recovered</b>\n\n" + (($e.prowlarr_health_restored_message // "The issue has cleared.") | @html)
else error("Unsupported Prowlarr notification event") end |
if ($e.prowlarr_telegram_preview // "") == "1" then "🧪 <b>Formatting preview · already grabbed</b>\n\n" + . else . end |
{text:., parse_mode:"HTML"}
