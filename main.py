import os
import time
import threading
import requests
import telebot
from flask import Flask

# -------------------------------------------------------------
# CẤU HÌNH BOT MD5 
# -------------------------------------------------------------
BOT_TOKEN = "8463492839:AAGgzUV1a7O_8pzt6ZQ8wFLpTG_GrXFF4qI"
CHAT_ID = "6285849261"
API_MD5 = "https://bottele-production-4be9.up.railway.app/api/history/md5"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

last_phien = None
last_predict = None
stats = {"thang": 0, "thua": 0}

@app.route('/')
def home():
    return "Bot MD5 đang chạy 24/7!"

def soi_cau(history):
    danh_sach = []
    cau_icon = []
    
    for p in history:
        if not isinstance(p, dict):
            continue

        # Lấy tổng điểm hoặc kết quả từ API
        tong = p.get('Tong') or p.get('tong')
        kq = str(p.get('Ket_qua') or p.get('ketqua') or p.get('result') or '').lower()

        is_tai = False
        is_xiu = False

        # Nhận diện chuẩn bằng Tổng điểm xúc xắc (11-18: Tài, 3-10: Xỉu)
        if isinstance(tong, (int, float)) and tong > 0:
            if tong >= 11:
                is_tai = True
            elif tong <= 10:
                is_xiu = True
        else:
            if 'tai' in kq or 'tài' in kq or kq == 't':
                is_tai = True
            elif 'xiu' in kq or 'xỉu' in kq or kq == 'x':
                is_xiu = True

        if is_tai:
            danh_sach.append('tai')
            cau_icon.append('🔴')
        elif is_xiu:
            danh_sach.append('xiu')
            cau_icon.append('🔵')

    if not danh_sach:
        return "Tài", "🔴", 50, 50, "⚪"

    c_tai = danh_sach.count('tai')
    c_xiu = danh_sach.count('xiu')
    total = len(danh_sach)

    r_tai = round((c_tai / total) * 100)
    r_xiu = round((c_xiu / total) * 100)

    # Thuật toán phân tích xu hướng (Tránh bị kẹt 1 bên)
    latest_kq = danh_sach[0]
    
    # 1. Nếu bệt 3 phiên liên tiếp -> Dự đoán BẺ cầu
    if len(danh_sach) >= 3 and danh_sach[0] == danh_sach[1] == danh_sach[2]:
        du_doan = "Xỉu" if latest_kq == "tai" else "Tài"
    # 2. Nếu không bệt -> So sánh tỷ lệ %
    elif r_tai > r_xiu:
        du_doan = "Xỉu"
    elif r_xiu > r_tai:
        du_doan = "Tài"
    else:
        # Nếu % bằng nhau -> Dự đoán ĐẢO phiên trước
        du_doan = "Xỉu" if latest_kq == "tai" else "Tài"

    dot = "🔴" if du_doan == "Tài" else "🔵"
    cau_str = "".join(reversed(cau_icon[:7]))
    return du_doan, dot, r_tai, r_xiu, cau_str

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
                    
                    # Lấy mã MD5 từ API
                    ma_md5 = curr.get('Ma_hash') or curr.get('md5') or curr.get('hash') or curr.get('MD5') or 'Chưa cập nhật'

                    if phien and phien != last_phien:
                        status_eval = ""
                        if last_predict:
                            # Đánh giá Thắng/Thua chính xác
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

                        tong_p = stats["thang"] + stats["thua"]
                        rate_win = round((stats["thang"] / tong_p) * 100, 1) if tong_p > 0 else 0

                        du_doan, dot, r_tai, r_xiu, cau_str = soi_cau(history[:10])
                        phien_next = phien + 1 if isinstance(phien, int) else "N/A"

                        msg = (
                            f"╭━━━ KẾT QUẢ SẢNH MD5 ━━━╮\n"
                            f" 📌 Phiên: {phien}\n"
                            f" 🎲 Xúc xắc: {xx1} · {xx2} · {xx3} → Tổng {tong}\n"
                            f" 🔑 Mã MD5: `{ma_md5}`\n"
                            f" 🎯 Kết quả: {kq}{status_eval}\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                            f"╭━━━ 🤖 DỰ ĐOÁN MD5 🤖 ━━━╮\n"
                            f" 1️⃣2️⃣ Phiên kế tiếp: {phien_next}\n\n"
                            f" 🎯 Dự đoán: {du_doan} {dot}\n\n"
                            f" ⚖️ Tỷ lệ: Tài {r_tai}% · Xỉu {r_xiu}%\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n"
                            f"🌐 Cầu: {cau_str}\n"
                            f"📊 Thành tích: {stats['thang']} Thắng · {stats['thua']} Thua ({rate_win}%)\n"
                            f"🎮 bot_md5_service"
                        )

                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        last_predict = du_doan
                        last_phien = phien
        except Exception as e:
            print(f"Lỗi Auto Loop MD5: {e}", flush=True)

        time.sleep(7)

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.reply_to(message, "Bot MD5 đã sẵn sàng và đang chạy tự động!")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    threading.Thread(target=auto_process, daemon=True).start()
    print("Bot MD5 mới đang khởi chạy...", flush=True)
    bot.infinity_polling(skip_pending=True)
