# Custom_Clash_Rules

自定义 Clash 规则集，供 SubStore / subconverter 生成订阅配置（配合 `archbridge-clean` 订阅使用）。

## 目录结构

| 路径 | 说明 |
|---|---|
| `Clash.ini` | subconverter 模板（基础版，71 个策略组） |
| `Clash_Adv.ini` | subconverter 模板（进阶版，含中转/智能组，84 组，**实际生成用的是它**） |
| `rules/` | 本地化规则集：30 个远程源（ACL4SSR / blackmatrix7 / DustinWin / Aethersailor）拉取后按链序去重生成 |
| `Academic.list` 等（根目录） | 手写小名单，各走专组（海外加速 / 谷歌学术 / Unity / GenAI / Claude / Copilot / 直连） |
| `CN_Supplement.list` | 国行域名直连补充表（cn.list 中经国内 DNS 解析为非 CN IP 的域名，强制直连） |
| `scripts/sync-rules.py` | 远程规则源同步 + 去重脚本 |

## 规则链语义（重要）

Clash 规则**从上到下匹配、命中即停**，所以：

- `rules/` 中的文件已按 ini 链序做过 first-match 去重——后面文件里被更早规则覆盖的条目已剔除（共约 2,400 条），行为与直接引用远程源完全一致
- **新增/调整名单位置后，重跑 `scripts/sync-rules.py` 保持去重**
- `rules/SteamCN.list` 刻意保留原始内容（不去重），作为独立 SteamCN 定义
- `CN_Supplement.list` 最后 120 条 `.hk/.tw/.us` 等 TLD 域名被 ProxyGFWlist 的"国外域名"裸 TLD 规则优先命中（走代理）——已知、有意搁置

## 维护

```bash
# 远程源更新后刷新本地化规则集
python3 scripts/sync-rules.py
git add -A && git commit -m "sync rules" && git push
```

新增手写名单：

1. 根目录建 `Xxx.list`，每行一条 `DOMAIN-SUFFIX,xxx.com`
2. 在两个 ini 的 `;===== 规则 =====` 区加一行：
   `ruleset=<组名>,https://raw.githubusercontent.com/orange030/Custom_Clash_Rules/main/Xxx.list`
3. 注意**链序**：放在靠前 = 优先于后面所有规则

## 生成流程

SubStore 文件 `archbridge-clean` 以 `Clash_Adv.ini` 为模板，聚合 6 个节点订阅（ab-boss / ab-liangxin / ab-jkun / ab-cf / zhehua-clean / apex）并 relay 生成。改完仓库后，SubStore 里 `refresh=true` 重新生成即可。
