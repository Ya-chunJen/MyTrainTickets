"""
项目配置文件 —— 所有可配置项集中在此文件
"""
import os

# ====== 项目路径 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EMAILS_DIR = os.path.join(DATA_DIR, 'emails')
VISUALIZE_DIR = os.path.join(BASE_DIR, 'visualize')

# ====== 邮件获取方式 ======
# 'local'        - 读取本地目录中的 .eml 文件
# 'remote_folder' - 登录邮箱，读取指定文件夹
# 'remote_inbox'  - 登录邮箱，在收件箱中筛选来自 12306 的邮件
EMAIL_SOURCE = 'remote_folder'

# ====== 本地模式配置 ======
LOCAL_EMAIL_DIR = '/path/to/eml/files'   # 存放 .eml 文件的目录

# ====== 远程模式配置 ======
# 常见邮箱 IMAP 服务器地址：
#   QQ邮箱: imap.qq.com
#   163邮箱: imap.163.com
#   Gmail: imap.gmail.com
#   Outlook: outlook.office365.com
IMAP_SERVER = 'imap.qq.com'
SENDER = 'your_email@example.com'       # 邮箱地址
PASSWORD = 'your_imap_auth_code'        # 邮箱IMAP授权码（非邮箱密码）
# remote_folder 模式：搜索包含此关键词的文件夹
IMAP_FOLDER_KEYWORD = '12306'
# remote_inbox 模式：筛选发件人包含此关键词的邮件
REMOTE_SENDER_FILTER = '12306@rails.com.cn'

# ====== 邮件筛选（step2） ======
TARGET_SUBJECTS = ['用户支付通知', '用户改签通知', '候补订单兑现成功通知', '用户退票通知']
# 过滤关键词（票务行中如果包含这些词则跳过）
SKIP_KEYWORDS = ['温馨提示', '购票不成功', '重复支付', '未到帐', '未到账',
                 '退票费', '报销凭证', '网站购票', '改签', '退票', '怎么办', '身份信息核验']

# ====== 席别类型（step3） ======
SEAT_CLASSES = ['商务座', '特等座', '一等座', '二等座', '软卧', '硬卧', '硬座', '无座',
                '软座', '高级软卧', '硬卧代硬座', '软卧代软座', '动卧']

# ====== 姓名过滤（step4） ======
WHITELIST = [
    # '任三伟',
    # '李第三',
]
BLACKLIST = [
    '张华',
]
# 是否对姓名脱敏（将最后一个字替换为 *）
NAME_MASK = True

# ====== HTML 可视化（step5） ======
HTML_TEMPLATE = os.path.join(VISUALIZE_DIR, 'tickets.html')
HTML_OUTPUT = os.path.join(VISUALIZE_DIR, 'index.html')

# ====== 中间数据文件路径 ======
METADATA_PATH = os.path.join(DATA_DIR, 'emails_metadata.json')
TICKETS_RAW_PATH = os.path.join(DATA_DIR, 'tickets_raw.json')
TICKETS_STRUCTURED_PATH = os.path.join(DATA_DIR, 'tickets_structured.json')
TICKETS_FILTERED_PATH = os.path.join(DATA_DIR, 'tickets_filtered.json')
TICKETS_MERGED_PATH = os.path.join(DATA_DIR, 'tickets_merged.json')