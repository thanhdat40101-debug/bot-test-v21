import os
import time
import threading
import requests
import telebot
from flask import Flask

# -------------------------------------------------------------
# CẤU HÌNH BOT MD5 ĐỘC LẬP MỚI
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
    return "Bot MD5 Doc Lap Dang Chay 24/7!"

def soi_cau(history):
    danh_sach = []
    cau_icon = []
    for p in history:
        kq = str(p.get('Ket_qua') or p.get('ketqua') or p.get('result') or '').lower() if isinstance(p, dict) else str(p).lower()
        if 'tai' in kq or 'tài' in kq:
            danh_sach.append('tai')
            cau_icon.append('🔴')
        elif 'xiu' in kq or 'xỉu' in kq:
            danh_sach.append('xiu')
            cau_icon.append('🔵')

    c_tai = danh_sach.count('tai')
    c_xiu = danh_sach.count('xiu')
    total = len(danh_sach) or 1

    r_tai = round((c_tai / total) * 100)
    r_xiu = round((c_xiu / total) * 100)

    if c_tai >= 6:
        du_doan, dot = "Xỉu", "🔵"
    elif c_xiu >= 6:
        du_doan, dot = "Tài", "🔴"
    else:
        du_doan, dot = ("Tài", "🔴") if r_tai <= r_xiu else ("Xỉu", "🔵")

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

                    if phien and phien != last_phien:
                        status_eval = ""
                        if last_predict:
                            win = last_predict.lower() in kq.lower()
                            if win:
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
                            f" Phiên: {phien}\n"
                            f" Xúc xắc: {xx1} · {xx2} · {xx3} → Tổng {tong}\n"
                            f" Kết quả: {kq}{status_eval}\n"
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

                        bot.send_message(CHAT_ID, msg)
                        last_predict = du_doan
                        last_phien = phien
        except Exception as e:
            print(f"Error MD5: {e}", flush=True)

        time.sleep(7)

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.reply_to(message, "Bot MD5 mới đang chạy tự động 24/7!")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    threading.Thread(target=auto_process, daemon=True).start()
    print("Bot MD5 doc lap khoi chay...", flush=True)
    bot.infinity_polling(skip_pending=True)
