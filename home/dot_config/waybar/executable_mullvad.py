#!/usr/bin/env python

import sys
import json
import subprocess

SERVER_COUNTRY_FLAGS = {
  "Albania":"🇦🇱",
  "Australia":"🇦🇺",
  "Austria":"🇦🇹",
  "Belgium":"🇧🇪",
  "Brazil":"🇧🇷",
  "Bulgaria":"🇧🇬",
  "Canada":"🇨🇦",
  "Colombia":"🇨🇴",
  "Croatia":"🇭🇷",
  "Czech Republic":"🇨🇿",
  "Denmark":"🇩🇰",
  "Estonia":"🇪🇪",
  "Finland":"🇫🇮",
  "France":"🇫🇷",
  "Germany":"🇩🇪",
  "Greece":"🇬🇷",
  "Hong Kong":"🇭🇰",
  "Hungary":"🇭🇺",
  "Ireland":"🇮🇪",
  "Israel":"🇮🇱",
  "Italy":"🇮🇹",
  "Japan":"🇯🇵",
  "Latvia":"🇱🇻",
  "Luxembourg":"🇱🇺",
  "Moldova":"🇲🇩",
  "Netherlands":"🇳🇱",
  "New Zealand":"🇳🇿",
  "North Macedonia":"🇲🇰",
  "Norway":"🇳🇴",
  "Poland":"🇵🇱",
  "Portugal":"🇵🇹",
  "Romania":"🇷🇴",
  "Serbia":"🇷🇸",
  "Singapore":"🇸🇬",
  "Slovakia":"🇸🇰",
  "South Africa":"za",
  "Spain":"🇿🇦",
  "Sweden":"🇸🇪",
  "Switzerland":"🇨🇭",
  "UK":"🇬🇧",
  "USA":"🇺🇸",
  "United Arab Emirates":"🇦🇪"
}

def write_output(text, tooltip):
    output = {
              'text': text,
              'tooltip' : tooltip,
              'class': 'custom-vpn',
              'alt': 'mullvad'}

    sys.stdout.write(json.dumps(output) + '\n')
    sys.stdout.flush()


def account():
    cmd = subprocess.Popen('mullvad account get', text=True, shell=True, stdout=subprocess.PIPE)
    account = {}
    for line in cmd.stdout:
        k, v = line.split(': ')
        account[k.strip()] = v.strip()

    device = account.get('Device name', '-')
    account_id = account.get('Mullvad account', '-')
    expiry_date = account.get('Expires at', 'Expired').split(' ')[0]

    return f'{device}\n{account_id}\n({expiry_date})'

def status():
    cmd = subprocess.Popen('mullvad status', text=True, shell=True, stdout=subprocess.PIPE)
    lines = [line.strip() for line in cmd.stdout if line.strip()]
    if not lines:
        return "👀"

    if any('disconnected' in line.lower() for line in lines):
        return "👀"

    location_line = next((line for line in reversed(lines) if ':' in line), None)
    if not location_line:
        return "👀"

    country = location_line.split(':', 1)[1].strip().split(',')[0].strip()
    if not country or country.lower() == 'null':
        return "👀"

    return SERVER_COUNTRY_FLAGS.get(country, "🇺🇳")


if __name__ == '__main__':
    write_output(
        text=status(),
        tooltip=account()
    )
