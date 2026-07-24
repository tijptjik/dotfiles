-- Base24 - Rosé Punk

local colors = {
    -- Darkest Black (The Darkest Background)
    base11 = "rgb(08080C)",
    -- Darker Black (Darker Background)
    base10 = "rgb(110F18)",
    -- Black (Background)
    base00 = "rgb(191724)",
    -- Darkest Gray (Status Bar)
    base01 = "rgb(1F1D2E)",
    -- Dark Gray (Selection Background)
    base02 = "rgb(26233A)",
    -- Bright Black (Comments, Invisibles, Line Highlighting)
    base03 = "rgb(555169)",
    -- Light Gray (Status bars)
    base04 = "rgb(6E6A86)",
    -- White (Default Foreground, Caret, Delimiters, Operators)
    base05 = "rgb(E5E5E5)",
    -- Lighter White (Not often used)
    base06 = "rgb(ECEBEF)",
    -- Bright White (Not often used)
    base07 = "rgb(F5F5F7)",

    -- Dark Red (Deprecated Highlighting)
    base0F = "rgb(D75959)",
    -- Red (Variables, Elements, Markup Link Text, Markup Lists, Diff Deleted)
    base08 = "rgb(EB6F92)",
    -- Bright Red
    base12 = "rgb(FF6B95)",

    -- Orange (Integers, Boolean, Constants, XML Attributes, Markup Link Url0
    base09 = "rgb(F6C177)",

    -- Yellow (Classes, Markup Bold, Search Text Background)
    base0A = "rgb(F4B7B5)",
    -- Bright Yellow
    base13 = "rgb(FACDCC)",

    -- Green (Strings, Inherited Class, Markup Code, Diff Inserted)
    base0B = "rgb(31748F)",
    -- Bright Green
    base14 = "rgb(2F87AB)",

    -- Cyan (Support, Regular Expressions, Escape Characters, Markup Quotes)
    base0C = "rgb(9CCFD8)",
    -- Bright Cyan
    base15 = "rgb(9BDFEB)",

    -- Blue (Functions, Methods, Attribute IDs, Headings)
    base0D = "rgb(7188FF)",
    -- Bright Blue
    base16 = "rgb(8596ED)",

    -- Magenta (Keywords, Storage, Selector, Markup Italic, Diff Changed)
    base0E = "rgb(FF53A6)",
    -- Bright Magenta
    base17 = "rgb(E56EA1)",
}

-- Aliases

colors.fx_black = colors.base11
colors.fx_white = colors.base05

colors.fx_magenta = colors.base0E

colors.fx_active = colors.base01
colors.fx_inactive = "rgba(26233Aaa)"

return colors
