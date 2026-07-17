# MyTrainTickets

将 12306 购票邮件解析为结构化数据，生成可视化车票画廊。

## 效果预览
![](https://pubdz.paperol.cn/ryjimage/20260717151554614.png)

## 功能

- 从邮件中自动提取 12306 购票信息（支持本地 .eml 文件或 IMAP 远程下载）
- 支持高铁动车（蓝票）和普速列车（红票）两种视觉风格
- 多种浏览模式：相册视图、幻灯片播放
- 按年份、状态、车型、乘客筛选
- 退票/改签状态自动标记（水印）
- 姓名脱敏保护隐私
- 键盘导航（← → Esc）、移动端适配
- 丰富的动画效果（发牌入场、扫光、3D 倾斜、二维码发光等）

## 安装
从 GitHub 安装：
```
/install https://github.com/renyajun/my-train-tickets
```

从 Gitee 安装：
```
/install https://gitee.com/renyajun/my-train-tickets
```
## 使用

安装后在 Claude Code 中直接说：

> 帮我可视化我的 12306 火车票

Skill 会逐步引导你完成配置和运行。

## 文件结构

```
├── SKILL.md              # Skill 定义文件
├── config.py             # 配置文件（邮件、过滤、脱敏等）
├── pipeline.py           # 完整流水线脚本
├── visualize/
│   └── tickets.html      # HTML 可视化模板
└── data/                 # 运行时生成的中间数据（已 gitignore）
```

## 配置说明

运行前需在 `config.py` 中配置：

| 配置项 | 说明 |
|--------|------|
| `EMAIL_SOURCE` | 邮件获取方式：`local` / `remote_folder` / `remote_inbox` |
| `IMAP_SERVER` | IMAP 服务器地址（远程模式） |
| `SENDER` / `PASSWORD` | 邮箱地址和 IMAP 授权码（远程模式） |
| `WHITELIST` / `BLACKLIST` | 姓名过滤白名单/黑名单 |
| `NAME_MASK` | 是否对姓名脱敏 |

## 本地运行

```bash
# 首次运行（获取邮件 + 解析 + 生成可视化）
python3 pipeline.py

# 跳过邮件获取，仅重新解析已有数据
python3 pipeline.py --skip1

# 查看结果
open visualize/index.html
```

## 部署分享

生成的 `visualize/index.html` 可部署到问卷星 AI 主页，生成可外部分享的链接。