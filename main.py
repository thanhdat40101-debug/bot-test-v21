import os
import time
import threading
import requests
import telebot
from flask import Flask

# -------------------------------------------------------------
# CẤU HÌNH BOT TELEGRAM & API
# -------------------------------------------------------------
BOT_TOKEN = "8463492839:AAHXxkyqQpGVHuCz9-vyQg4g6_2wMUv9LKw"
CHAT_ID = "6285849261"
API_MD5 = "https://bottele-production-4be9.up.railway.app/api/history/md5"

# -------------------------------------------------------------
# BỘ NHẬN DIỆN MÃ MD5 ĐỘNG (BẮT TẤT CẢ CHUỖI HEX 32 KÝ TỰ)
# -------------------------------------------------------------
def extract_md5_auto(item):
    """Tự động tìm mã MD5 trong dict bất kể API đặt tên key là gì"""
    if not isinstance(item, dict):
        return "Chưa cập nhật"
    
    # 1. Kiểm tra các key phổ biến
    for key in ['Ma_hash', 'md5', 'hash', 'MD5', 'Ma_md5', 'hash_code', 'code_md5', 'key_md5', 'MD5_hash']:
        val = item.get(key)
        if val and isinstance(val, str) and len(val.strip()) == 32:
            return val.strip()

    # 2. Quét toàn bộ các giá trị trong JSON, hễ là chuỗi Hex 32 ký tự thì lấy
    for k, v in item.items():
        if isinstance(v, str):
            clean_v = v.strip()
            if len(clean_v) == 32 and all(c in '0123456789abcdefABCDEF' for c in clean_v):
                return clean_v

    return "Chưa cập nhật"

# -------------------------------------------------------------
# ENGINE PHÂN TÍCH CHUỖI HEX MD5 & TÍNH XÁC SUẤT
# -------------------------------------------------------------
class SmartMD5Engine:
    def parse_md5_deep(self, md5_str):
        """Bóc tách Bitwise 128-bit & Checksum từ mã MD5"""
        if not md5_str or len(md5_str) != 32 or md5_str == 'Chưa cập nhật':
            return 50, 50, "Mã MD5 chưa cập nhật từ API - Dùng xác suất mặc định"

        try:
            full_int = int(md5_str, 16)
            binary_128 = bin(full_int)[2:].zfill(128)
            ones_count = binary_128.count('1')

            d1 = int(md5_str[0:8], 16)
            d2 = int(md5_str[8:16], 16)
            d3 = int(md5_str[16:24], 16)
            d4 = int(md5_str[24:32], 16)
            xor_sum = d1 ^ d2 ^ d3 ^ d4

            hex_mod = full_int % 100
            score_tai = (hex_mod * 0.4) + ((ones_count / 128.0) * 100 * 0.4) + ((xor_sum % 100) * 0.2)

            p_tai = round(max(15, min(85, score_tai)))
            p_xiu = 100 - p_tai
            ly_do = f"MD5 Bitwise: {ones_count}/128 Bit 1 | Checksum XOR: {xor_sum % 100}"
            return p_tai, p_xiu, ly_do
        except Exception:
            return 50, 50, "Lỗi giải mã chuỗi Hex MD5"

    def analyze(self, history):
        data = []
        for p in history:
            if not isinstance(p, dict): continue
            tong = p.get('Tong') or p.get('tong') or 0
            ma_md5 = extract_md5_auto(p)
            if tong > 0:
                is_tai = 1 if tong >= 11 else 0
            else:
                kq = str(p.get('Ket_qua', '')).lower()
                is_tai = 1 if 'tai' in kq or 't' in kq else 0
                tong = 11 if is_tai else 8
            data.append({'is_tai': is_tai, 'tong': tong, 'md5': ma_md5})

        if not data:
            return "Tài", "🔴", 50, 50, 50, "⚪", ["Chờ dữ liệu"]

        latest_md5 = data[0]['md5']
        p_tai_md5, p_xiu_md5, ly_do_md5 = self.parse_md5_deep(latest_md5)

        short_trend = (sum(d['is_tai'] for d in data[:3]) / 3.0) * 100

        final_tai = (p_tai_md5 * 0.7) + (short_trend * 0.3)
        final_xiu = 100 - final_tai

        p_tai = round(max(10, min(90, final_tai)))
        p_xiu = 100 - p_tai

        confidence = max(p_tai, p_xiu)
        du_doan = "Tài" if p_tai > p_xiu else "Xỉu"
        dot = "🔴" if du_doan == "Tài" else "🔵"

        cau_list = ["🔴" if d['is_tai'] == 1 else "🔵" for d in data[:7]]
        cau_str = "".join(reversed(cau_list))

        return du_doan, dot, p_tai, p_xiu, confidence, cau_str, [ly_do_md5]

engine = SmartMD5Engine()

# -------------------------------------------------------------
# BỘ LƯU TRỮ LỊCH SỬ DỰ ĐOÁN (PHỤC VỤ LỆNH /thongke)
# -------------------------------------------------------------
history_logs = []

def record_game_result(phien, dice_str, tong, kq_str, du_doan, is_win):
    global history_logs
    history_logs.insert(0, {
        'phien': phien,
        'dice': dice_str,
        'tong': tong,
        'kq': kq_str,
        'du_doan': du_doan,
        'is_win': is_win
    })
    if len(history_logs) > 50:
        history_logs = history_logs[:50]

# -------------------------------------------------------------
# BOT TELEGRAM & SERVER FLASK
# -------------------------------------------------------------
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

last_phien = None
last_predict = None
stats = {"thang": 0, "thua": 0}

@app.route('/')
def home():
    return "Bot MD5 System Online 24/7!"

# -------------------------------------------------------------
# XỬ LÝ LỆNH /thongke & /tk TRÊN TELEGRAM
# -------------------------------------------------------------
@bot.message_handler(commands=['thongke', 'tk'])
def handle_thongke(message):
    if not history_logs:
        bot.reply_to(message, "📊 Chưa đủ dữ liệu lịch sử. Vui lòng chờ bot chạy thêm vài phiên!")
        return

    recent_10 = history_logs[:10]
    wins = sum(1 for log in recent_10 if log['is_win'])
    total = len(recent_10)
    win_rate = round((wins / total) * 100, 1) if total > 0 else 0

    msg = f"📊 **THỐNG KÊ {total} TAY GẦN NHẤT** 📊\n"
    msg += "───────────────────\n"

    for idx, log in enumerate(recent_10, 1):
        status = "✅ THẮNG" if log['is_win'] else "❌ THUA"
        msg += (
            f"**{idx}. Phiên #{log['phien']}**\n"
            f" 🎲 Xúc xắc: {log['dice']} → Tổng {log['tong']} ({log['kq']})\n"
            f" 🎯 Dự đoán: **{log['du_doan']}** ➔ {status}\n"
            f"───────────────────\n"
        )

    msg += f"\n📈 **TỔNG KẾT:** {wins}/{total} Thắng (Tỷ lệ: `{win_rate}%`)"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.reply_to(message, "🤖 **Bot MD5 Smart Engine** đã chạy!\nGõ `/thongke` hoặc `/tk` để xem 10 tay gần nhất kèm thắng/thua.")

def auto_process():
    global last_phien, last_predict, stats
    while True:
        try:
            res = requests.get(API_MD5, timeout=6)
            if res.status_code == 200:
                data = res.json()
                history = data.get('history', []) if isinstance(data, dict) else data

                if history and isinstance(history, list):
                    curr = history[0]
                    phien = curr.get('Phien') or curr.get('phien')
                    xx1 = curr.get('Xuc_xac_1', 0)
                    xx2 = curr.get('Xuc_xac_2', 0)
                    xx3 = curr.get('Xuc_xac_3', 0)
                    tong = curr.get('Tong', 0)
                    kq = str(curr.get('Ket_qua') or curr.get('ketqua') or '')
                    
                    # Gọi hàm nhận diện MD5 tự động
                    ma_md5 = extract_md5_auto(curr)

                    if phien and phien != last_phien:
                        status_eval = ""
                        if last_predict:
                            is_win = False
                            if tong >= 11 and last_predict == "Tài": is_win = True
                            elif 3 <= tong <= 10 and last_predict == "Xỉu": is_win = True
                            elif last_predict.lower() in kq.lower(): is_win = True

                            if is_win:
                                stats["thang"] += 1
                                status_eval = "\n ✅ ĐÁNH GIÁ: THẮNG"
                            else:
                                stats["thua"] += 1
                                status_eval = "\n ❌ ĐÁNH GIÁ: THUA"

                            kq_text = "Tài" if tong >= 11 else "Xỉu"
                            dice_format = f"{xx1}-{xx2}-{xx3}"
                            record_game_result(phien, dice_format, tong, kq_text, last_predict, is_win)

                        tong_p = stats["thang"] + stats["thua"]
                        rate_win = round((stats["thang"] / tong_p) * 100, 1) if tong_p > 0 else 0

                        du_doan, dot, r_tai, r_xiu, do_tin_cay, cau_str, ly_do = engine.analyze(history)
                        phien_next = phien + 1 if isinstance(phien, int) else "N/A"

                        str_ly_do = "\n".join(f"• {ld}" for ld in ly_do)

                        msg = (
                            f"╭━━━ KẾT QUẢ SẢNH MD5 ━━━╮\n"
                            f" 📌 Phiên: {phien}\n"
                            f" 🎲 Xúc xắc: {xx1} · {xx2} · {xx3} → Tổng {tong}\n"
                            f" 🔑 Mã MD5: `{ma_md5}`\n"
                            f" 🎯 Kết quả: {kq}{status_eval}\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                            f"╭━━━ 🤖 DỰ ĐOÁN THÔNG MINH 🤖 ━━━╮\n"
                            f" 1️⃣2️⃣ Phiên kế tiếp: {phien_next}\n\n"
                            f" 🎯 Dự đoán: {du_doan} {dot}\n"
                            f" 📊 Độ tin cậy: {do_tin_cay}%\n"
                            f" ⚖️ Trọng số MD5: Tài {r_tai}% · Xỉu {r_xiu}%\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n"
                            f"💡 **Cơ sở phân tích:**\n{str_ly_do}\n\n"
                            f"🌐 Cầu: {cau_str}\n"
                            f"📊 Thành tích: {stats['thang']} Thắng · {stats['thua']} Thua ({rate_win}%)\n"
                            f"💬 Nhập `/thongke` để xem chi tiết 10 tay gần nhất."
                        )

                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        last_predict = du_doan
                        last_phien = phien
        except Exception as e:
            print(f"Lỗi Auto Loop MD5: {e}", flush=True)

        time.sleep(7)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    threading.Thread(target=auto_process, daemon=True).start()
    print("Khởi chạy bot MD5 thành công...", flush=True)
    bot.infinity_polling(skip_pending=True)
