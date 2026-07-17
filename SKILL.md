---
name: MyTrainTickets
description: Use when the user wants to visualize 12306 train ticket purchase history from email, set up automated ticket email parsing, or create a train ticket gallery from email data
---

# 火车票可视化

将 12306 购票邮件解析为结构化数据，生成可视化车票画廊。

## 项目文件

| 文件 | 用途 |
|------|------|
| `config.py` | 所有配置项 |
| `pipeline.py` | 完整流水线 |
| `visualize/tickets.html` | HTML 可视化模板 |

## 引导流程

**重要：必须逐步引导用户，每次只问一个问题，等用户回答后再继续下一步。**

### 步骤 1：复制文件

先将 skill 文件复制到用户项目目录：

```bash
cp -r ~/.claude/skills/MyTrainTickets/* <项目目录>/
```

### 步骤 2：选择邮件获取方式

> **WorkBuddy 用户提示：** 如果你在 WorkBuddy 中使用本 skill，可以借助 WorkBuddy 中其他邮箱相关的 skill 来获取邮件，无需手动配置 IMAP 或导出 eml 文件。

**首先问用户：**

> 你有两种方式获取 12306 的购票邮件：
> 1. **本地文件** — 已有导出的 `.eml` 文件（推荐，无需邮箱密码）
> 2. **自动下载** — 我帮你登录邮箱自动下载
>
> 你选哪种？

**如果用户选 1（本地文件）：**

引导用户通过邮件客户端导出邮件：

> 请按以下步骤操作：
> 1. 使用邮件客户端（如 Outlook、Thunderbird、Mac 邮件 App、Foxmail 等）登录你的邮箱
> 2. 搜索发件人为 `mail.12306.cn` 的所有购票邮件
> 3. 全选搜索结果（Ctrl+A / Cmd+A）
> 4. 将选中的邮件拖拽到桌面一个文件夹里（会自动导出为 `.eml` 文件）
>
> 完成后告诉我文件夹路径，我帮你配置。

用户提供路径后，修改 `config.py`：
```python
EMAIL_SOURCE = 'local'
LOCAL_EMAIL_DIR = '<用户提供的路径>'
```

**如果用户选 2（自动下载）：**

**问用户：**

> 有两种筛选 12306 邮件的方式：
> 1. **指定文件夹** — 读取邮箱中某个文件夹（如"铁路12306订票邮件"）
> 2. **收件箱筛选** — 在收件箱中按发件人筛选 `mail.12306.cn`
>
> 你选哪种？

用户选择后，**问用户：**

> 请提供以下信息：
> 1. 你的邮箱地址
> 2. 邮箱的 IMAP 服务器地址
> 3. 邮箱的 IMAP 授权码
>
> 常见邮箱的 IMAP 服务器地址：
> - QQ邮箱：`imap.qq.com`
> - 163邮箱：`imap.163.com`
> - Gmail：`imap.gmail.com`
> - Outlook：`outlook.office365.com`
>
> 授权码获取方式：登录邮箱网页版 → 设置 → 账户 → 开启 IMAP 服务 → 生成授权码（不是邮箱密码）。
>
> ⚠ **重要提醒：请检查邮箱的 IMAP 同步设置。** 很多邮箱默认只同步最近 30 天的邮件，如果你的购票邮件跨越多年，需要先将同步范围调整为"全部邮件"。

用户提供后，修改 `config.py`：
```python
# 方式 2a：指定文件夹
EMAIL_SOURCE = 'remote_folder'
IMAP_SERVER = '<用户提供的服务器地址>'
SENDER = '<用户邮箱>'
PASSWORD = '<授权码>'
IMAP_FOLDER_KEYWORD = '12306'

# 方式 2b：收件箱筛选
EMAIL_SOURCE = 'remote_inbox'
IMAP_SERVER = '<用户提供的服务器地址>'
SENDER = '<用户邮箱>'
PASSWORD = '<授权码>'
REMOTE_SENDER_FILTER = 'mail.12306.cn'
```

### 步骤 3：配置姓名过滤（可选）

**问用户：**

> 是否需要按姓名过滤车票？
> - 如果只想看某些人的票，可以设置白名单
> - 如果想排除某些人，可以设置黑名单
> - 不需要过滤可以直接跳过

根据用户回答修改 `config.py` 中的 `WHITELIST` 和 `BLACKLIST`。

**再问用户：**

> 是否需要对姓名进行脱敏？（将姓名最后一个字替换为 `*`，保护隐私）

根据用户回答修改 `config.py` 中的 `NAME_MASK`（`True` / `False`）。

### 步骤 4：运行

配置完成后，运行流水线并打开结果：

```bash
cd <项目目录>
python3 pipeline.py
open visualize/index.html
```

如果用户已有邮件数据（之前运行过），使用 `--skip1` 跳过邮件获取：

```bash
python3 pipeline.py --skip1
```

### 步骤 5：部署分享（可选）

运行完成后，**问用户：**

> 车票画廊已生成，可以直接用浏览器打开 `visualize/index.html` 查看。
>
> 如果你想分享给朋友或在手机上查看，可以部署到**问卷星的 AI 主页**：
> 1. 打开问卷星网站 (wjx.cn)
> 2. 进入"AI 主页"模块
> 3. 上传 `visualize/index.html` 文件
> 4. 生成可外部分享的链接
>
> 需要我帮你部署吗？

## 流水线步骤

```
step1: 获取邮件 → data/emails/*.eml + emails_metadata.json
step2: 提取票务 → tickets_raw.json
step3: 结构化   → tickets_structured.json
step4: 姓名过滤 → tickets_filtered.json
step6: 状态合并 → tickets_merged.json
step5: 生成HTML → visualize/index.html
```

## 可视化功能

- 蓝票(G/D/C高铁动车) / 红票(普速列车) 两种风格
- 相册、幻灯片两种浏览模式
- 按日期分组、按年份/状态/车型/乘客筛选
- 退票/改签水印标记、键盘导航（← → Esc）
- 移动端适配

## 常见问题

**Q: 远程模式只读到少量邮件？**
A: 大多数邮箱的 IMAP 默认只同步最近一段时间（30天/60天等），需在邮箱设置中将同步范围调整为"全部邮件"。

**Q: 老格式邮件日期不对？**
A: 已处理跨年日期补齐（邮件12月发、车票1月开 → 自动判定为下一年）。

**Q: 改签/退票状态不对？**
A: 通过订单号匹配原票，退票记录删除并在原票上标记状态，改签新票保持正常。