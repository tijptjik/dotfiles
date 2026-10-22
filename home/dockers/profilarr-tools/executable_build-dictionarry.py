#!/usr/bin/env python3
"""Build the reviewed Dictionarry snapshot into the si Profilarr database.

Only public policy data is read. The source checkout must match policy.json;
the generated SQL contains no credentials, app databases or library inventory.
"""
import argparse
import json
import pathlib
import sqlite3
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent / "profilarr-database"
TABLES = (
    "tags", "regular_expressions", "custom_formats", "regular_expression_tags",
    "custom_format_tags", "custom_format_conditions", "condition_patterns",
    "condition_languages", "condition_indexer_flags", "condition_sources",
    "condition_resolutions", "condition_quality_modifiers", "condition_sizes",
    "condition_release_types", "condition_years", "custom_format_tests",
    "quality_profiles", "quality_groups", "quality_profile_tags",
    "quality_profile_languages", "quality_group_members", "quality_profile_qualities",
    "quality_profile_custom_formats", "radarr_quality_definitions",
    "sonarr_quality_definitions",
)
EXECUTABLE_PATTERN = r"(?i)\.(?:exe|scr|lnk|msi|msp|bat|cmd|ps1|vbs|vbe|hta)(?=$|[\s\]\)])"
SAFETY_NAME = "SI: Reject executable releases"
SD_NAME = "SI: SD fallback"


def replay(connection, checkout):
    files = sorted((checkout / "ops").glob("*.sql"), key=lambda p: int(p.name.split(".")[0]))
    if not files:
        raise ValueError(f"No SQL operations in {checkout}")
    for path in files:
        connection.executescript(path.read_text())


def check_source(checkout, expected):
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != expected:
        raise ValueError(f"Review policy.json before changing upstream: {actual} != {expected}")
    if subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True):
        raise ValueError("Upstream checkout has uncommitted changes")


def prepare(connection, policy):
    prefix = policy["upstream"]["customFormatPrefix"]
    # Arr custom formats are global and matched by name. A namespace prevents
    # an import from changing formats still used by existing legacy profiles.
    connection.execute("UPDATE custom_formats SET name = ? || name", (prefix,))
    connection.execute("INSERT INTO tags(name) VALUES ('si acquisition')")
    for acquisition in policy["acquisitions"]:
        source = acquisition["sourceProfile"]
        if source == "SD":
            continue
        name = acquisition["name"]
        row = connection.execute("SELECT description FROM quality_profiles WHERE name=?", (source,)).fetchone()
        if row is None:
            raise ValueError(f"Dictionarry profile not found: {source}")
        ceiling = next(x["maximumResolution"] for x in policy["tiers"] if x["name"] == acquisition["maximum"])
        floor = acquisition["minimumResolution"]
        if floor > ceiling:
            raise ValueError(f"Minimum resolution exceeds maximum for {name}")
        fallback = "SD" if floor == 0 else f"{floor}p"
        minimum = acquisition["minimum"] or "None"
        description = f"Dictionarry: {source}. Enforced resolution floor: {fallback}. Upstream scoring and upgrade cutoff.\n\nRequested tier window: target {name}; maximum {acquisition['maximum']}; minimum {minimum}. Cross-preset tier bounds are not native Arr limits and are not enforced by this snapshot.\n\n{row[0]}"
        connection.execute("UPDATE quality_profiles SET name=?, description=? WHERE name=?", (name, description, source))
        connection.execute("INSERT INTO quality_profile_tags VALUES (?, 'si acquisition')", (name,))
        tag = "media:" + acquisition["upgradeTo"]
        connection.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
        connection.execute("INSERT INTO quality_profile_tags VALUES (?, ?)", (name, tag))
        # Enforce the displayed resolution interval in actual allowed qualities,
        # including grouped members. A renamed profile alone changes no rules.
        members = connection.execute("SELECT quality_group_name, quality_name FROM quality_group_members WHERE quality_profile_name=?", (name,)).fetchall()
        for group, quality in members:
            if not floor <= resolution(quality) <= ceiling:
                connection.execute("DELETE FROM quality_group_members WHERE quality_profile_name=? AND quality_group_name=? AND quality_name=?", (name, group, quality))
                position = connection.execute("SELECT COALESCE(MAX(position),0)+1 FROM quality_profile_qualities WHERE quality_profile_name=?", (name,)).fetchone()[0]
                connection.execute("INSERT INTO quality_profile_qualities(quality_profile_name,quality_name,position,enabled) VALUES (?,?,?,0)", (name, quality, position))
        for quality, enabled in connection.execute("SELECT quality_name,enabled FROM quality_profile_qualities WHERE quality_profile_name=? AND quality_name IS NOT NULL", (name,)).fetchall():
            if enabled and not floor <= resolution(quality) <= ceiling:
                connection.execute("UPDATE quality_profile_qualities SET enabled=0 WHERE quality_profile_name=? AND quality_name=?", (name, quality))

    connection.execute("INSERT INTO regular_expressions(name,pattern,description) VALUES (?,?,?)", (SAFETY_NAME, EXECUTABLE_PATTERN, "Boundary-aware executable suffix rejection."))
    connection.execute("INSERT INTO custom_formats(name,description) VALUES (?,?)", (SAFETY_NAME, "Reject explicit executable payload names, without rejecting Batman or Adventure."))
    connection.execute("INSERT INTO custom_format_conditions(custom_format_name,name,type,arr_type,required) VALUES (?, 'Executable suffix', 'release_title', 'all', 1)", (SAFETY_NAME,))
    connection.execute("INSERT INTO condition_patterns VALUES (?, 'Executable suffix', ?)", (SAFETY_NAME, SAFETY_NAME))
    for title, kind, match in (
        ("Example.Movie.2025.1080p.WEB-DL.exe", "movie", 1),
        ("Example.Movie.2025.1080p.WEB-DL.scr]", "movie", 1),
        ("The.Batman.S01E01.1080p.WEB-DL", "series", 0),
        ("Adventure.Time.S01E01.1080p.WEB-DL", "series", 0),
    ):
        connection.execute("INSERT INTO custom_format_tests(custom_format_name,title,type,should_match,description) VALUES (?,?,?,?,?)", (SAFETY_NAME, title, kind, match, "Executable boundary regression"))

    sd_profile = next(x["name"] for x in policy["acquisitions"] if x["sourceProfile"] == "SD")
    connection.execute("INSERT INTO quality_profiles(name,description,upgrades_allowed,minimum_custom_format_score,upgrade_until_score) VALUES (?,?,0,200000,200000)", (sd_profile, "SD only, up to 576p. Any bitrate or codec; original/English audio, executable, full-disc and known-bad release protections. No automatic upgrades."))
    connection.execute("INSERT INTO quality_groups(quality_profile_name,name) VALUES (?, 'SD')", (sd_profile,))
    sd_qualities = {"SDTV", "DVD", "WEBDL-480p", "WEBRip-480p", "Bluray-480p", "Bluray-576p"}
    for index, quality in enumerate(sorted(sd_qualities)):
        connection.execute("INSERT INTO quality_group_members(quality_profile_name,quality_group_name,quality_name,position) VALUES (?, 'SD', ?, ?)", (sd_profile, quality, index))
    connection.execute("INSERT INTO quality_profile_qualities(quality_profile_name,quality_group_name,position,enabled,upgrade_until) VALUES (?, 'SD', 0, 1, 1)", (sd_profile,))
    for index, (quality,) in enumerate(connection.execute("SELECT name FROM qualities WHERE name NOT IN ('SDTV','DVD','WEBDL-480p','WEBRip-480p','Bluray-480p','Bluray-576p') ORDER BY name").fetchall(), 1):
        connection.execute("INSERT INTO quality_profile_qualities(quality_profile_name,quality_name,position,enabled) VALUES (?,?,?,0)", (sd_profile, quality, index))
    connection.execute("INSERT INTO quality_profile_languages VALUES (?, 'Any', 'simple')", (sd_profile,))
    connection.execute("INSERT INTO quality_profile_tags VALUES (?, 'si acquisition')", (sd_profile,))
    connection.execute("INSERT INTO tags(name) VALUES ('media:SD:1')")
    connection.execute("INSERT INTO quality_profile_tags VALUES (?, 'media:SD:1')", (sd_profile,))
    connection.execute("INSERT INTO custom_formats(name,description) VALUES (?, 'Known SD qualities only; no bitrate or codec restriction.')", (SD_NAME,))
    for value in ("720p", "1080p", "2160p"):
        condition = "Not " + value
        connection.execute("INSERT INTO custom_format_conditions(custom_format_name,name,type,arr_type,negate,required) VALUES (?,?, 'resolution', 'all', 1, 1)", (SD_NAME, condition))
        connection.execute("INSERT INTO condition_resolutions VALUES (?,?,?)", (SD_NAME, condition, value))
    connection.execute("INSERT INTO quality_profile_custom_formats VALUES (?,?, 'all', 200000)", (sd_profile, SD_NAME))
    safety = {"3D", "Audio Description", "Banned Groups", "Banned Groups (Regular)", "Banned Groups (Release Title)", "Banned Language Groups", "Banned Dual Audio Groups", "CAM", "Extras", "Full Disc", "Full Disc (Quality Match)", "German DL", "Not Original or English", "Sing Along", "Upscale"}
    source_name = next(x["name"] for x in policy["acquisitions"] if x["sourceProfile"] == "720p Quality")
    for format_name, arr_type, score in connection.execute("SELECT custom_format_name,arr_type,score FROM quality_profile_custom_formats WHERE quality_profile_name=? AND score<0", (source_name,)).fetchall():
        if format_name.removeprefix(prefix) in safety:
            connection.execute("INSERT INTO quality_profile_custom_formats VALUES (?,?,?,?)", (sd_profile, format_name, arr_type, score))
    for acquisition in policy["acquisitions"]:
        connection.execute("INSERT INTO quality_profile_custom_formats VALUES (?,?, 'all', -10000000)", (acquisition["name"], SAFETY_NAME))
    # Renaming/upgrading automation, delay profiles and media settings are not
    # part of this snapshot. Quality definitions are deliberately upstream's
    # unrestricted limits so old caps don't block Compact or Remux profiles.


def resolution(name):
    for value in (2160, 1080, 720, 576, 480):
        if str(value) in name:
            return value
    return 576 if name in {"SDTV", "DVD"} else 0


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def export_sql(connection, policy):
    lines = ["-- @operation: export", "-- @entity: batch", "-- @name: Dictionarry acquisition catalogue", "-- Generated by profilarr-tools/build-dictionarry.py; edit policy.json, not this file.", "-- Upstream: " + policy["upstream"]["repository"] + " @ " + policy["upstream"]["commit"], "-- Dictionarry content is MIT licensed; see UPSTREAM-LICENSE.", ""]
    for table in TABLES:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(" + table + ")") if row[1] not in {"id", "created_at", "updated_at"}]
        column_list = ",".join(columns)
        for row in connection.execute(f"SELECT {column_list} FROM {table} ORDER BY {column_list}"):
            values = [
                "\n".join(value_line.rstrip() for value_line in value.split("\n"))
                if column == "description" and isinstance(value, str) else value
                for column, value in zip(columns, row)
            ]
            lines.append(f"INSERT INTO {table}({column_list}) VALUES ({','.join(literal(v) for v in values)});")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=pathlib.Path)
    parser.add_argument("--schema", required=True, type=pathlib.Path)
    parser.add_argument("--check", action="store_true", help="Verify generated SQL without writing")
    args = parser.parse_args()
    policy = json.loads((ROOT / "policy.json").read_text())
    check_source(args.upstream, policy["upstream"]["commit"])
    schema_commit = subprocess.check_output(["git", "-C", str(args.schema), "rev-parse", policy["upstream"]["schemaVersion"] + "^{commit}"], text=True).strip()
    check_source(args.schema, schema_commit)
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    replay(connection, args.schema)
    replay(connection, args.upstream)
    prepare(connection, policy)
    problems = connection.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        raise ValueError(f"Foreign key violations: {problems}")
    sql = export_sql(connection, policy)
    # Validate the actual portable output, not just the in-memory source.
    check = sqlite3.connect(":memory:")
    check.execute("PRAGMA foreign_keys=ON")
    replay(check, args.schema)
    check.executescript(sql)
    if check.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Generated snapshot has foreign key violations")
    output = ROOT / "ops/1.dictionarry-acquisitions.sql"
    if args.check:
        if not output.exists() or output.read_text() != sql:
            raise ValueError("Generated snapshot is stale; rebuild it")
    else:
        output.write_text(sql)
    print(f"Validated {len(policy['acquisitions'])} acquisition profiles; {len(sql.encode()) // 1024} KiB of public policy SQL")


if __name__ == "__main__":
    main()
