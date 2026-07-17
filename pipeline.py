"""
火车票数据处理流水线
步骤: 下载邮件 → 提取票务 → 结构化解析 → 姓名过滤 → 状态合并 → 生成HTML
运行: python3 pipeline.py           # 跑完整流水线（含下载邮件）
      python3 pipeline.py --skip1   # 跳过下载邮件，直接从已有数据开始
"""
import os
import re
import json
import imaplib
import email
import pytz
from email.header import decode_header
from email.utils import parsedate_to_datetime
from collections import Counter

import config


# ====== 通用工具函数 ======

def decode_str(s):
    if s is None:
        return ''
    result = ''
    for part, charset in decode_header(s):
        if isinstance(part, bytes):
            result += part.decode(charset or 'utf-8', errors='ignore')
        else:
            result += str(part)
    return result


def convert_to_east8_time(date_str):
    if not date_str:
        return '未知日期'
    try:
        dt = parsedate_to_datetime(date_str)
        east8 = pytz.timezone('Asia/Shanghai')
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(east8).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str


def get_email_year(msg):
    date_str = msg.get('Date', '')
    if date_str:
        try:
            return parsedate_to_datetime(date_str).year
        except Exception:
            pass
    return None


def get_body_text(msg):
    for part in msg.walk():
        ct = part.get_content_type()
        cd = str(part.get('Content-Disposition'))
        if ct == 'text/html' and 'attachment' not in cd:
            charset = part.get_content_charset() or 'gbk'
            html = part.get_payload(decode=True).decode(charset, errors='replace')
            text = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.I | re.S)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.I | re.S)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            return text.strip()
    return ''


# ====== 第二步：提取票务信息 ======

def extract_ticket_lines(body, is_refund=False):
    lines = []
    if is_refund:
        parts = re.split(r'所退车票信息如下[：:]', body)
        if len(parts) > 1:
            first_line = parts[1].strip().split('\n')[0].strip()
            if first_line and len(first_line) > 10:
                if re.match(r'[一-鿿]{2,4}[，,]', first_line):
                    lines.append(first_line)
    else:
        for line in body.split('\n'):
            line = line.strip()
            if not re.match(r'\d+\.', line):
                continue
            ticket_part = line.split('。')[0].strip()
            if re.search('|'.join(config.SKIP_KEYWORDS), ticket_part):
                continue
            if len(ticket_part) < 15:
                continue
            lines.append(ticket_part)
    return lines


def extract_order_number(body):
    m = re.search(r'订单号码[：:\s]*([A-Z0-9]+)', body)
    if m:
        return m.group(1)
    m = re.search(r'订单号码\s*\n\s*([A-Z0-9]+)', body)
    if m:
        return m.group(1)
    return None


def step2_extract():
    print('=' * 50)
    print('第二步：提取票务信息')
    print('=' * 50)

    with open(config.METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    results = []
    for item in metadata:
        subject = item['subject']
        if not any(kw in subject for kw in config.TARGET_SUBJECTS):
            continue

        filepath = os.path.join(config.EMAILS_DIR, item['filename'])
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'rb') as f:
            msg = email.message_from_bytes(f.read())

        email_year = get_email_year(msg)
        body = get_body_text(msg)
        is_refund = '退票' in subject
        ticket_lines = extract_ticket_lines(body, is_refund)
        order_no = extract_order_number(body)

        if not ticket_lines:
            continue

        status = '已退票' if '退票' in subject else '正常'

        result = {
            'filename': item['filename'],
            'date': item['date'],
            'email_year': email_year,
            'subject': subject,
            'status': status,
            'order_number': order_no,
            'ticket_count': len(ticket_lines),
            'tickets_raw': ticket_lines,
        }
        results.append(result)

        print(f"[{item['date'][:10]}] {status} | {subject.split('-')[-1]} | 订单:{order_no or '无'} | {len(ticket_lines)}张票")
        for line in ticket_lines:
            print(f"    {line[:120]}")

    with open(config.TICKETS_RAW_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'\n提取完成！共 {len(results)} 封邮件，{sum(r["ticket_count"] for r in results)} 条票务信息')
    return results


# ====== 第三步：结构化解析 ======

def parse_ticket_line(line, email_year, email_date=None):
    line = line.split('。')[0].strip()
    line = re.sub(r'^\d+[\.、]\s*', '', line)
    if not line:
        return None

    if '，' in line:
        line = line.replace(',', '，')
        parts = [p.strip() for p in line.split('，')]
    else:
        parts = [p.strip() for p in line.split(',')]

    if len(parts) < 7:
        return None

    name = parts[0]
    datetime_str = parts[1]
    stations = parts[2].replace('—', '-')
    train_no = parts[3]
    seat_no = parts[4]

    seat_class = None
    price = None
    gate = None

    for p in parts[5:]:
        if p.startswith('票价'):
            price = p
        elif p.startswith('检票口'):
            gate = p.replace('检票口', '').strip()
        elif seat_class is None:
            for sc in config.SEAT_CLASSES:
                if sc in p:
                    seat_class = sc
                    break

    if seat_class is None or price is None:
        return None

    if not re.search(r'\d{4}年', datetime_str):
        year = email_year
        if email_date:
            ticket_month = re.search(r'(\d{2})月', datetime_str)
            email_month = re.search(r'-(\d{2})-', email_date)
            if ticket_month and email_month:
                tm = int(ticket_month.group(1))
                em = int(email_month.group(1))
                if tm < em:
                    year = email_year + 1
        datetime_str = f'{year}年{datetime_str}'

    m = re.search(r'(\d{4})年(\d{2})月(\d{2})日(\d{2}):(\d{2})', datetime_str)
    departure_time = f'{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}' if m else datetime_str

    station_parts = stations.split('-', 1)
    from_station = station_parts[0].strip()
    to_station = station_parts[1].strip() if len(station_parts) > 1 else ''

    train_no = re.sub(r'次(列车)?$', '', train_no)

    price_value = None
    m_price = re.search(r'(\d+\.?\d*)', price)
    if m_price:
        price_value = float(m_price.group(1))

    return {
        'name': name,
        'datetime': datetime_str,
        'departure_time': departure_time,
        'from_station': from_station,
        'to_station': to_station,
        'train_no': train_no,
        'seat_no': seat_no,
        'seat_class': seat_class,
        'price': price,
        'price_value': price_value,
        'gate': gate or '',
    }


def step3_parse():
    print('\n' + '=' * 50)
    print('第三步：结构化解析')
    print('=' * 50)

    with open(config.TICKETS_RAW_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    structured = []
    parse_errors = []

    for email_item in raw_data:
        email_year = email_item['email_year']
        for raw_line in email_item['tickets_raw']:
            parsed = parse_ticket_line(raw_line, email_year, email_item['date'])
            if parsed:
                parsed['source_file'] = email_item['filename']
                parsed['source_date'] = email_item['date']
                parsed['subject'] = email_item['subject']
                parsed['status'] = email_item.get('status', '正常')
                parsed['order_number'] = email_item['order_number']
                parsed['email_year'] = email_year
                structured.append(parsed)
            else:
                parse_errors.append({
                    'file': email_item['filename'],
                    'line': raw_line[:100],
                })

    structured.sort(key=lambda t: t['departure_time'])

    for t in structured:
        print(f"{t['departure_time']} | {t['status']:4s} | {t['name']:4s} | {t['from_station']:10s} → {t['to_station']:10s} | {t['train_no']:8s} | {t['seat_no']:10s} | {t['seat_class']:6s} | ¥{t['price_value']:>8.2f}")

    with open(config.TICKETS_STRUCTURED_PATH, 'w', encoding='utf-8') as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f'\n解析完成！成功: {len(structured)} 条, 失败: {len(parse_errors)} 条')
    if parse_errors:
        print('解析失败:')
        for err in parse_errors:
            print(f'  [{err["file"]}] {err["line"]}')
    return structured


# ====== 第四步：姓名过滤 ======

def step4_filter():
    print('\n' + '=' * 50)
    print('第四步：姓名过滤')
    print('=' * 50)

    with open(config.TICKETS_STRUCTURED_PATH, 'r', encoding='utf-8') as f:
        tickets = json.load(f)

    print(f'过滤前: {len(tickets)} 张票')
    print(f'白名单: {config.WHITELIST if config.WHITELIST else "(无限制)"}')
    print(f'黑名单: {config.BLACKLIST if config.BLACKLIST else "(无)"}')

    filtered = []
    for t in tickets:
        name = t['name']
        if config.WHITELIST and name not in config.WHITELIST:
            continue
        if config.BLACKLIST and name in config.BLACKLIST:
            continue
        filtered.append(t)

    if config.NAME_MASK:
        for t in filtered:
            name = t['name']
            if len(name) == 1:
                t['name'] = '*'
            elif len(name) == 2:
                t['name'] = name[0] + '*'
            else:
                t['name'] = name[0] + '*' + name[2:]
        print('姓名脱敏: 已启用')

    with open(config.TICKETS_FILTERED_PATH, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    names = sorted(set(t['name'] for t in filtered))
    sc = Counter(t['status'] for t in filtered)
    print(f'过滤后: {len(filtered)} 张票')
    print(f'乘客: {names}')
    for s, c in sorted(sc.items()):
        print(f'  {s}: {c} 张')
    return filtered


# ====== 第六步：状态合并 ======

def step6_merge():
    print('\n' + '=' * 50)
    print('第六步：退票/改签状态合并')
    print('=' * 50)

    with open(config.TICKETS_FILTERED_PATH, 'r', encoding='utf-8') as f:
        tickets = json.load(f)

    refund_orders = set()
    change_orders = set()

    for t in tickets:
        oid = t.get('order_number')
        if not oid:
            continue
        if t['status'] == '已退票':
            refund_orders.add(oid)
        if '改签' in t.get('subject', ''):
            change_orders.add(oid)

    print(f'退票订单: {len(refund_orders)} 个')
    print(f'改签订单: {len(change_orders)} 个')

    merged = []
    for t in tickets:
        if t['status'] == '已退票':
            continue
        t = dict(t)
        oid = t.get('order_number')
        if '改签' in t.get('subject', ''):
            t['status'] = '正常'
        if oid and oid in refund_orders:
            t['status'] = '已退票'
        if oid and oid in change_orders and '改签' not in t.get('subject', ''):
            t['status'] = '已改签'
        merged.append(t)

    merged.sort(key=lambda t: t['departure_time'])

    with open(config.TICKETS_MERGED_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    sc = Counter(t['status'] for t in merged)
    print(f'\n合并前: {len(tickets)} 条')
    print(f'合并后: {len(merged)} 条')
    for s, c in sorted(sc.items()):
        print(f'  {s}: {c} 张')

    # 同步更新 filtered
    if os.path.exists(config.TICKETS_FILTERED_PATH):
        with open(config.TICKETS_FILTERED_PATH, 'r', encoding='utf-8') as f:
            filtered = json.load(f)
        filtered_merged = []
        for t in filtered:
            if t['status'] == '已退票':
                continue
            t = dict(t)
            oid = t.get('order_number')
            if '改签' in t.get('subject', ''):
                t['status'] = '正常'
            if oid and oid in refund_orders:
                t['status'] = '已退票'
            if oid and oid in change_orders and '改签' not in t.get('subject', ''):
                t['status'] = '已改签'
            filtered_merged.append(t)
        filtered_merged.sort(key=lambda t: t['departure_time'])
        with open(config.TICKETS_FILTERED_PATH, 'w', encoding='utf-8') as f:
            json.dump(filtered_merged, f, ensure_ascii=False, indent=2)
        print(f'filtered 合并后: {len(filtered_merged)} 条')

    return merged


# ====== 第五步：生成HTML ======

def step5_generate():
    print('\n' + '=' * 50)
    print('第五步：生成可视化HTML')
    print('=' * 50)

    # 数据源优先级: filtered > merged > structured
    if os.path.exists(config.TICKETS_FILTERED_PATH):
        with open(config.TICKETS_FILTERED_PATH, 'r', encoding='utf-8') as f:
            tickets = json.load(f)
    elif os.path.exists(config.TICKETS_MERGED_PATH):
        with open(config.TICKETS_MERGED_PATH, 'r', encoding='utf-8') as f:
            tickets = json.load(f)
    else:
        with open(config.TICKETS_STRUCTURED_PATH, 'r', encoding='utf-8') as f:
            tickets = json.load(f)

    tickets.sort(key=lambda t: t['departure_time'])

    with open(config.HTML_TEMPLATE, 'r', encoding='utf-8') as f:
        template = f.read()

    html = template.replace('__DATA_PLACEHOLDER__', json.dumps(tickets, ensure_ascii=False))

    with open(config.HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'生成完成！')
    print(f'  数据: {len(tickets)} 条车票')
    print(f'  输出: {config.HTML_OUTPUT}')


# ====== 第一步：获取邮件 ======

def step1_download():
    print('=' * 50)
    print('第一步：获取邮件')
    print('=' * 50)

    os.makedirs(config.EMAILS_DIR, exist_ok=True)

    source = config.EMAIL_SOURCE
    if source == 'local':
        return _step1_local()
    elif source == 'remote_folder':
        return _step1_remote_folder()
    elif source == 'remote_inbox':
        return _step1_remote_inbox()
    else:
        print(f'无效的 EMAIL_SOURCE: {source}')
        return False


def _step1_local():
    """从本地目录读取 .eml 文件"""
    local_dir = config.LOCAL_EMAIL_DIR
    if not os.path.isdir(local_dir):
        print(f'本地目录不存在: {local_dir}')
        return False

    eml_files = sorted([f for f in os.listdir(local_dir) if f.endswith('.eml')])
    if not eml_files:
        print(f'目录中没有 .eml 文件: {local_dir}')
        return False

    print(f'从本地目录读取: {local_dir}')
    print(f'共 {len(eml_files)} 个 .eml 文件\n')

    metadata_list = []
    for i, filename in enumerate(eml_files, 1):
        src_path = os.path.join(local_dir, filename)
        with open(src_path, 'rb') as f:
            raw_email = f.read()

        msg = email.message_from_bytes(raw_email)
        subject = decode_str(msg.get('Subject', ''))
        date_str = convert_to_east8_time(msg.get('Date', ''))
        from_ = decode_str(msg.get('From', ''))

        # 复制到 data/emails/ 目录
        safe_date = date_str.replace(':', '-').replace(' ', '_') if date_str != '未知日期' else f'unknown_{i}'
        dest_filename = f'{safe_date}.eml'
        dest_path = os.path.join(config.EMAILS_DIR, dest_filename)
        if os.path.exists(dest_path):
            dest_filename = f'{safe_date}_{i}.eml'
            dest_path = os.path.join(config.EMAILS_DIR, dest_filename)

        with open(dest_path, 'wb') as f:
            f.write(raw_email)

        metadata_list.append({
            'index': i,
            'filename': dest_filename,
            'date': date_str,
            'from': from_,
            'subject': subject,
        })

        print(f'  [{i}/{len(eml_files)}] {date_str}  {subject}')

    with open(config.METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    print(f'\n读取完成！共 {len(metadata_list)} 封邮件')
    return True


def _imap_connect():
    """连接邮箱，返回 mail 对象"""
    print(f'正在连接 {config.IMAP_SERVER} ...')
    mail = imaplib.IMAP4_SSL(config.IMAP_SERVER)
    mail.login(config.SENDER, config.PASSWORD)
    print('登录成功！')
    return mail


def _imap_download_all(mail, email_ids, desc=''):
    """下载邮件列表中的所有邮件"""
    total = len(email_ids)
    print(f'共 {total} 封邮件{desc}，开始下载...\n')

    metadata_list = []
    for i, num in enumerate(email_ids, 1):
        status, data = mail.fetch(num, '(RFC822)')
        if status != 'OK':
            print(f'  [{i}/{total}] 获取失败，跳过')
            continue

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_str(msg.get('Subject', ''))
        date_str = convert_to_east8_time(msg.get('Date', ''))
        from_ = decode_str(msg.get('From', ''))

        safe_date = date_str.replace(':', '-').replace(' ', '_') if date_str != '未知日期' else f'unknown_{i}'
        filename = f'{safe_date}.eml'
        filepath = os.path.join(config.EMAILS_DIR, filename)

        if os.path.exists(filepath):
            filename = f'{safe_date}_{i}.eml'
            filepath = os.path.join(config.EMAILS_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(raw_email)

        metadata_list.append({
            'index': i,
            'filename': filename,
            'date': date_str,
            'from': from_,
            'subject': subject,
        })

        print(f'  [{i}/{total}] {date_str}  {subject}')

    with open(config.METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    print(f'\n下载完成！共保存 {len(metadata_list)} 封邮件到 {config.EMAILS_DIR}')
    return True


def _step1_remote_folder():
    """登录邮箱，读取指定文件夹"""
    mail = _imap_connect()

    status, folder_list = mail.list()
    target_folder_bytes = None
    for f in folder_list:
        if config.IMAP_FOLDER_KEYWORD.encode() in f:
            target_folder_bytes = f
            break

    if target_folder_bytes is None:
        print(f'未找到包含 "{config.IMAP_FOLDER_KEYWORD}" 的文件夹')
        mail.logout()
        return False

    raw_str = target_folder_bytes.decode('utf-8', errors='ignore')
    match = re.search(r'"([^"]+)"\s*$', raw_str)
    folder_name = match.group(1)

    status, _ = mail.select(f'"{folder_name}"')
    if status != 'OK':
        print('选择文件夹失败')
        mail.logout()
        return False

    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    result = _imap_download_all(mail, email_ids)
    mail.logout()
    return result


def _step1_remote_inbox():
    """登录邮箱，在收件箱中筛选来自 12306 的邮件"""
    mail = _imap_connect()

    status, _ = mail.select('INBOX')
    if status != 'OK':
        print('选择收件箱失败')
        mail.logout()
        return False

    # 搜索 FROM 包含 12306 的邮件
    status, messages = mail.search(None, f'FROM "{config.REMOTE_SENDER_FILTER}"')
    if status != 'OK':
        print('搜索邮件失败')
        mail.logout()
        return False

    email_ids = messages[0].split()
    result = _imap_download_all(mail, email_ids, f'（发件人: {config.REMOTE_SENDER_FILTER}）')
    mail.logout()
    return result


# ====== 主流程 ======

def main():
    import sys

    skip_step1 = '--skip1' in sys.argv

    if skip_step1:
        print('跳过第一步（下载邮件）\n')
    else:
        if config.SENDER == 'your_email@qq.com':
            print('⚠ 请先在 config.py 中配置邮箱和授权码')
            print('  如果已有邮件数据，可使用: python3 pipeline.py --skip1\n')
            return
        if not step1_download():
            print('邮件下载失败，终止流水线')
            return

    step2_extract()
    step3_parse()
    step4_filter()
    step6_merge()
    step5_generate()
    print('\n' + '=' * 50)
    print('流水线执行完毕！')


if __name__ == '__main__':
    main()