#!/usr/bin/env python3
"""
sync-rules.py — 拉取远程规则集 → 按 Clash first-match-wins 链序去重 → 生成 rules/*.list

用法: 在仓库根目录运行 `python3 scripts/sync-rules.py`
生成的文件按主链顺序剔除所有"运行时永远不会命中"的规则（前面的规则优先），
行为与直接从远程源引用完全一致，但规则数大幅减少。

源清单与顺序请与 Clash.ini / Clash_Adv.ini 的 ruleset 行保持一致。
"""
import ipaddress
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/orange030/Custom_Clash_Rules/main/rules/"

# (输出文件名, 目标组, 远程URL 或 None=本地文件只登记不输出) —— 严格按 ini 链序
SOURCES = [
    ("Academic.list", "谷歌学术", None),
    ("Oversea.list", "海外加速", None),
    ("Unity.list", "Unity", None),
    ("GenAI.list", "GenAI", None),
    ("Custom_Direct.list", "全球直连", None),
    ("Custom_Direct.list", "全球直连", "https://raw.githubusercontent.com/Aethersailor/Custom_OpenClash_Rules/main/rule/Custom_Direct.list"),
    ("GamesCN.list", "游戏服务", "https://github.com/DustinWin/domain-list-custom/releases/download/domains/games-cn.list"),
    ("Steam_CDN.list", "全球直连", "https://raw.githubusercontent.com/Aethersailor/Custom_OpenClash_Rules/main/rule/Steam_CDN.list"),
    ("SteamCN.list", "全球直连", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/SteamCN/SteamCN.list"),
    ("Steam.list", "Steam", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Steam/Steam.list"),
    ("Games.list", "游戏平台", "https://github.com/DustinWin/domain-list-custom/releases/download/domains/games.list"),
    ("Custom_Proxy.list", "节点选择", "https://raw.githubusercontent.com/Aethersailor/Custom_OpenClash_Rules/main/rule/Custom_Proxy.list"),
    ("Telegram.list", "Telegram", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Telegram/Telegram.list"),
    ("OpenAI.list", "ChatGPT", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.list"),
    ("Claude.list", "Claude", None),
    ("Copilot.list", "Copilot", None),
    ("AI.list", "AI 平台", "https://github.com/DustinWin/domain-list-custom/releases/download/domains/ai.list"),
    ("GitHub.list", "GitHub", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/GitHub/GitHub.list"),
    ("Apple.list", "苹果服务", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Apple/Apple.list"),
    ("Microsoft.list", "微软服务", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Microsoft/Microsoft.list"),
    ("YouTube.list", "YouTube", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/YouTube/YouTube.list"),
    ("GoogleCN.list", "谷歌服务", "https://github.com/DustinWin/domain-list-custom/releases/download/domains/google-cn.list"),
    ("Google.list", "谷歌服务", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Google/Google.list"),
    ("XiaoMi.list", "小米服务", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/XiaoMi/XiaoMi.list"),
    ("TikTok.list", "TikTok", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/TikTok/TikTok.list"),
    ("Netflix.list", "Netflix", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Netflix/Netflix.list"),
    ("Disney.list", "Disney+", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Disney/Disney.list"),
    ("Spotify.list", "Spotify", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Spotify/Spotify.list"),
    ("Bahamut.list", "Bahamut", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Bahamut/Bahamut.list"),
    ("NetEaseMusic.list", "网易音乐", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/NetEaseMusic/NetEaseMusic.list"),
    ("ChinaMedia.list", "国内媒体", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/ChinaMedia/ChinaMedia.list"),
    ("Media.list", "国外媒体", "https://github.com/DustinWin/domain-list-custom/releases/download/domains/media.list"),
    ("MediaIP.list", "国外媒体", "https://github.com/DustinWin/geoip/releases/download/ips/mediaip.list"),
    ("PrivateTracker.list", "全球直连", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/PrivateTracker/PrivateTracker.list"),
    ("Download.list", "全球直连", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Download/Download.list"),
    ("ProxyGFWlist.list", "节点选择", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ProxyGFWlist.list"),
    ("CN_Supplement.list", "全球直连", None),
    ("CNIP.list", "全球直连", "https://github.com/DustinWin/geoip/releases/download/ips/cnip.list"),
]

KEEP_ALL = {"SteamCN.list"}  # 单独保留，不去重


RE_RULE = re.compile(r'^(DOMAIN|DOMAIN-SUFFIX|DOMAIN-KEYWORD|IP-CIDR|IP-CIDR6|GEOIP|PROCESS-NAME|MATCH),(.+)$')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ClashforWindows/0.20.39"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse(text):
    rules = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(("#", ";", "//", "payload:")):
            continue
        m = RE_RULE.match(ln)
        if not m:
            continue
        typ, rest = m.group(1), m.group(2)
        fields = rest.split(",")
        val = fields[0].strip().strip("'\"")
        extra = fields[1:]
        if typ in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"):
            val = val.lower()
        rules.append((typ, val, extra))
    return rules


def is_covered(typ, val, suf, dom, kw, ips):
    if typ == "DOMAIN":
        if val in dom:
            return True
        if any(val == s or val.endswith("." + s) for s in suf):
            return True
        if any(k in val for k in kw):
            return True
    elif typ == "DOMAIN-SUFFIX":
        if any(val == s or val.endswith("." + s) for s in suf):
            return True
        if any(k in val for k in kw):
            return True
    elif typ == "DOMAIN-KEYWORD":
        if any(k in val for k in kw):
            return True
    elif typ in ("IP-CIDR", "IP-CIDR6"):
        try:
            net = ipaddress.ip_network(val, strict=False)
            if any(net.version == p.version and net.subnet_of(p) for p, _ in ips):
                return True
        except ValueError:
            pass
    return False


def fmt(typ, val, extra):
    s = f"{typ},{val}"
    if extra:
        s += "," + ",".join(extra)
    return s


def main():
    suf, dom, kw, ips = set(), set(), set(), []
    total_in = total_out = 0
    for name, group, url in SOURCES:
        if url is None:
            rules = parse(open(name, encoding="utf-8").read())
            for t, v, e in rules:
                if t == "DOMAIN": dom.add(v)
                elif t == "DOMAIN-SUFFIX": suf.add(v)
                elif t == "DOMAIN-KEYWORD": kw.add(v)
                elif t in ("IP-CIDR", "IP-CIDR6"):
                    try: ips.append((ipaddress.ip_network(v, strict=False), len(ips)))
                    except ValueError: pass
            print(f"{name:22s} {group:8s} [本地] {len(rules):6d} (只登记不输出)")
            continue
        try:
            raw = fetch(url)
        except Exception as e:
            print(f"!! {name}: 拉取失败 {e}")
            continue
        rules = parse(raw)
        kept = [fmt(t, v, e) for t, v, e in rules] if name in KEEP_ALL else []
        if name in KEEP_ALL:
            for t, v, e in rules:
                if t == "DOMAIN": dom.add(v)
                elif t == "DOMAIN-SUFFIX": suf.add(v)
                elif t == "DOMAIN-KEYWORD": kw.add(v)
                elif t in ("IP-CIDR", "IP-CIDR6"):
                    try: ips.append((ipaddress.ip_network(v, strict=False), len(ips)))
                    except ValueError: pass
        else:
            kept = []
        for typ, val, extra in rules:
            if is_covered(typ, val, suf, dom, kw, ips):
                continue
            kept.append(fmt(typ, val, extra))
            if typ == "DOMAIN":
                dom.add(val)
            elif typ == "DOMAIN-SUFFIX":
                suf.add(val)
            elif typ == "DOMAIN-KEYWORD":
                kw.add(val)
            elif typ in ("IP-CIDR", "IP-CIDR6"):
                try:
                    ips.append((ipaddress.ip_network(val, strict=False), len(ips)))
                except ValueError:
                    pass
        with open(f"rules/{name}", "w", encoding="utf-8") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))
        print(f"{name:22s} {group:8s} {len(rules):6d} -> {len(kept):6d}  (-{len(rules) - len(kept)})")
        total_in += len(rules)
        total_out += len(kept)
    print(f"\n总入 {total_in} -> 总出 {total_out} (-{total_in - total_out})")
    print(f"\nini 引用示例: {BASE}<文件名>")


if __name__ == "__main__":
    main()