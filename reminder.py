import os
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timedelta
import requests
import pytz


# ==================== 钉钉加签计算函数 ====================
def generate_signed_url(access_token: str, secret: str) -> str:
    """
    根据钉钉自定义机器人的加签规则，生成带签名的完整 Webhook URL。
    规则：timestamp + "\n" + secret → HMAC‑SHA256 → Base64 → URL‑Encode
    """
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    secret_enc = secret.encode("utf-8")
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    webhook_url = (
        f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
        f"&timestamp={timestamp}&sign={sign}"
    )
    return webhook_url


# ==================== 发送钉钉消息 ====================
def send_dingtalk_message(webhook_url: str, content: str):
    """通过钉钉 Webhook 发送 Markdown 消息到群聊"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "📊 流量高峰提醒",
            "text": content,
        },
    }
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
    result = response.json()
    if result.get("errcode") == 0:
        print("✅ 消息发送成功")
    else:
        print(f"❌ 消息发送失败: {result}")


# ==================== 地区配置 ====================
regions = [
    ("德国", "Europe/Berlin"),
    ("美国（东部）", "US/Eastern"),
    ("美国（西部）", "US/Pacific"),
    ("英国", "Europe/London"),
    ("法国", "Europe/Paris"),
    ("澳大利亚", "Australia/Sydney"),
    ("奥地利", "Europe/Vienna"),
    ("瑞士", "Europe/Zurich"),
    ("希腊", "Europe/Athens"),
    ("匈牙利", "Europe/Budapest"),
    ("波兰", "Europe/Warsaw"),
    ("捷克", "Europe/Prague"),
    ("比利时", "Europe/Brussels"),
    ("荷兰", "Europe/Amsterdam"),
    ("西班牙", "Europe/Madrid"),
    ("墨西哥", "America/Mexico_City"),
    ("加拿大", "America/Toronto"),
]

# 流量高峰期定义（当地时间）
# 对于欧美地区，通常晚间流量高峰集中在 20:00 - 23:00
# 说明：需要提前 1 小时提醒，当当前时间 >= 高峰起始时间前 1 小时 且 尚未达到高峰起始时间时触发提醒
traffic_peak_config = {
    "Germany": {"hour": 20, "minute": 0},              # 德国 20:00
    "USA_Eastern": {"hour": 21, "minute": 0},          # 美国东部 21:00
    "USA_Pacific": {"hour": 21, "minute": 0},          # 美国西部 21:00
    "UK": {"hour": 20, "minute": 0},                   # 英国 20:00
    "France": {"hour": 20, "minute": 0},               # 法国 20:00
    "Australia": {"hour": 19, "minute": 0},            # 澳大利亚 19:00
    "Austria": {"hour": 20, "minute": 0},              # 奥地利 20:00
    "Switzerland": {"hour": 20, "minute": 0},          # 瑞士 20:00
    "Greece": {"hour": 21, "minute": 0},               # 希腊 21:00
    "Hungary": {"hour": 20, "minute": 0},              # 匈牙利 20:00
    "Poland": {"hour": 20, "minute": 0},               # 波兰 20:00
    "Czech": {"hour": 20, "minute": 0},                # 捷克 20:00
    "Belgium": {"hour": 20, "minute": 0},              # 比利时 20:00
    "Netherlands": {"hour": 20, "minute": 0},          # 荷兰 20:00
    "Spain": {"hour": 21, "minute": 0},                # 西班牙 21:00
    "Mexico": {"hour": 20, "minute": 0},               # 墨西哥 20:00
    "Canada": {"hour": 21, "minute": 0},               # 加拿大 21:00
}

# 将地区名称映射到配置键
region_to_peak_key = {
    "德国": "Germany",
    "美国（东部）": "USA_Eastern",
    "美国（西部）": "USA_Pacific",
    "英国": "UK",
    "法国": "France",
    "澳大利亚": "Australia",
    "奥地利": "Austria",
    "瑞士": "Switzerland",
    "希腊": "Greece",
    "匈牙利": "Hungary",
    "波兰": "Poland",
    "捷克": "Czech",
    "比利时": "Belgium",
    "荷兰": "Netherlands",
    "西班牙": "Spain",
    "墨西哥": "Mexico",
    "加拿大": "Canada",
}


# ==================== 峰值提醒判断 ====================
def should_remind_before_peak(peak_hour: int, peak_minute: int, advance_hours: int = 1) -> bool:
    """
    判断当前时间是否处于指定高峰时间之前 advance_hours 小时的提醒窗口内。
    返回 True 表示需要提醒。
    """
    now = datetime.now()
    target_time = now.replace(hour=peak_hour, minute=peak_minute, second=0, microsecond=0)
    if target_time <= now:
        # 如果今天的高峰时间已经过去，则计算明天的高峰时间
        target_time += timedelta(days=1)
    remind_time = target_time - timedelta(hours=advance_hours)
    # 如果当前时间已经 >= 提醒时间，且尚未到达高峰时间，则触发提醒
    return remind_time <= now < target_time


def get_reminder_message() -> str:
    """
    生成提醒消息内容
    """
    # 北京时间
    beijing_tz = pytz.timezone("Asia/Shanghai")
    beijing_now = datetime.now(beijing_tz)
    beijing_time_str = beijing_now.strftime("%Y-%m-%d %H:%M:%S")

    # 构建消息内容
    lines = []
    lines.append("## 📡 欧美地区流量高峰提醒")
    lines.append("")
    lines.append(f"### 📅 中国时间（北京）：**{beijing_time_str}**")
    lines.append("---")
    lines.append("| 🌍 地区 | 🕐 当地时间 | ⏰ 高峰时间 | ⏱️ 剩余提醒 |")
    lines.append("|--------|-----------|-----------|-----------|")

    reminders = []

    for region_name, timezone_str in regions:
        tz = pytz.timezone(timezone_str)
        local_now = datetime.now(tz)
        local_time_str = local_now.strftime("%Y-%m-%d %H:%M:%S")

        # 获取该地区的高峰时间配置
        peak_key = region_to_peak_key[region_name]
        peak_config = traffic_peak_config[peak_key]
        peak_hour = peak_config["hour"]
        peak_minute = peak_config["minute"]

        # 计算距离高峰的小时和分钟
        peak_today = local_now.replace(hour=peak_hour, minute=peak_minute, second=0, microsecond=0)
        if local_now >= peak_today:
            peak_today += timedelta(days=1)
        time_diff = peak_today - local_now
        hours_left = int(time_diff.total_seconds() // 3600)
        minutes_left = int((time_diff.total_seconds() % 3600) // 60)

        # 判断是否需要提前提醒（高峰前一小时）
        if should_remind_before_peak(peak_hour, peak_minute, advance_hours=1):
            if hours_left < 1:
                remain_msg = f"🟢 **{int(minutes_left)}分钟后** 高峰即将到来"
            else:
                remain_msg = f"🔔 **{hours_left}小时{minutes_left}分钟后**"
            reminders.append(region_name)
        else:
            remain_msg = f"{hours_left}h {minutes_left}m"

        lines.append(
            f"| {region_name} | {local_time_str} | {peak_hour:02d}:{peak_minute:02d} | {remain_msg} |"
        )

    lines.append("")
    lines.append("### 💡 说明")
    lines.append(f"- 以上高峰时间参考当地晚高峰时段（`{', '.join(reminders)}` 已进入提醒窗口）")
    lines.append("- 请在上述高亮地区的高峰时段前1小时完成关键资源准备")
    lines.append("- ⏰ 以上时间均已按各地区真实时区（含夏令时）自动校正")

    return "\n".join(lines)


# ==================== 主函数 ====================
def main():
    # 从 GitHub Secrets 读取敏感信息
    access_token = os.getenv("DINGTALK_ACCESS_TOKEN")
    secret = os.getenv("DINGTALK_SECRET")

    if not access_token or not secret:
        print("❌ 错误：请设置环境变量 DINGTALK_ACCESS_TOKEN 和 DINGTALK_SECRET")
        return

    # 生成带签名的完整 webhook 地址（加签安全机制）
    webhook_url = generate_signed_url(access_token, secret)

    # 生成要推送的提醒消息
    content = get_reminder_message()

    # 发送到钉钉群
    send_dingtalk_message(webhook_url, content)


if __name__ == "__main__":
    main()