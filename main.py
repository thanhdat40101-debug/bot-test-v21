import os
import time
import threading
import requests
import telebot
import math
from flask import Flask

# -------------------------------------------------------------
# CẤU HÌNH BOT TELEGRAM
# -------------------------------------------------------------
BOT_TOKEN = "8463492839:AAGgzUV1a7O_8pzt6ZQ8wFLpTG_GrXFF4qI"
CHAT_ID = "6285849261"
API_MD5 = "https://bottele-production-4be9.up.railway.app/api/history/md5"

# -------------------------------------------------------------
# SYSTEM ENGINE: HYBRID ULTRA ENGINE (4 TẦNG PHÂN TÍCH)
# -------------------------------------------------------------
class HybridUltraEngine:
    def __init__(self):
        self.mu = 10.5  # Điểm trung bình lý thuyết của 3 xúc xắc (3-18)

    def _shannon_entropy(self, string):
        """Tầng 1.1: Tính độ hỗn loạn Entropy của chuỗi MD5 Hex"""
        if not string: return 0.0
        prob = [float(string.count(c)) / len(string) for c in set(string)]
        return -sum([p * math.log(p, 2) for p in prob])

    def parse_md5_deep(self, md5_str):
        """Tầng 1.2: Bóc táchBitwise 128-bit, XOR Checksum & Modulo"""
        if not md5_str or len(md5_str) < 32 or md5_str == 'N/A':
            return 50, 50, "Mã MD5 không hợp lệ - Dùng điểm mặc định"

        try:
            # 1. Hamming Weight (Mật độ Bit 1 trong 128-bit)
            full_int = int(md5_str, 16)
            binary_128 = bin(full_int)[2:].zfill(128)
            ones_count = binary_128.count('1')

            # 2. XOR Checksum 4 khối DWORD (mỗi khối 8 char Hex)
            d1 = int(md5_str[0:8], 16)
            d2 = int(md5_str[8:16], 16)
            d3 = int(md5_str[16:24], 16)
            d4 = int(md5_str[24:32], 16)
            xor_sum = d1 ^ d2 ^ d3 ^ d4

            # 3. Entropy
            entropy = self._shannon_entropy(md5_str)

            # Tính toán tổng hợp lực chọn MD5 Hex
            hex_mod = (full_int % 100)
            bit_density = (ones_count / 128.0) * 100
            
            score_tai = (hex_mod * 0.4) + (bit_density * 0.4) + ((xor_sum % 100) * 0.2)
            
            # Cân bằng với chỉ số Entropy
            if entropy > 3.8:
                score_tai = 100 - score_tai  # Đảo chiều nếu chuỗi quá hỗn loạn

            p_tai = round(max(15, min(85, score_tai)))
            p_xiu = 100 - p_tai
            ly_do = f"Bitwise: {ones_count}/128 Bit 1 | Entropy: {entropy:.2f} | XOR Mod: {xor_sum % 100}"
            return p_tai, p_xiu, ly_do
        except Exception:
            return 50, 50, "MD5 Parser Fallback"

    def markov_2nd_order(self, data):
        """Tầng 2: Chuỗi Markov Bậc 2 (Phân tích theo cặp 2 phiên liên tiếp)"""
        if len(data) < 15:
            return 0.5, 0.5, "Không đủ dữ liệu Markov"

        transitions = {}
        # Xây ma trận trạng thái cặp: (t-2, t-1) -> t
        for i in range(len(data) - 2):
            prev2 = "T" if data[i+2]['is_tai'] else "X"
            prev1 = "T" if data[i+1]['is_tai'] else "X"
            curr = "T" if data[i]['is_tai'] else "X"
            
            state_pair = prev2 + prev1
            if state_pair not in transitions:
                transitions[state_pair] = {'T': 0, 'X': 0}
            transitions[state_pair][curr] += 1

        curr_pair = ("T" if data[1]['is_tai'] else "X") + ("T" if data[0]['is_tai'] else "X")
        if curr_pair in transitions:
            total = transitions[curr_pair]['T'] + transitions[curr_pair]['X']
            if total > 0:
                p_t = transitions[curr_pair]['T'] / total
                p_x = transitions[curr_pair]['X'] / total
                return p_t, p_x, f"Markov Bậc 2 trạng thái [{curr_pair}]"

        return 0.5, 0.5, "Markov Bậc 2 trung tính"

    def calculate_z_score(self, data):
        """Tầng 3: Độ lệch chuẩn Z-Score & Mean Reversion"""
        scores = [d['tong'] for d in data[:7] if d['tong'] > 0]
        if len(scores) < 3: return 0.0, "Z-Score không đủ mẫu"

        mean_val = sum(scores) / len(scores)
        variance = sum((x - mean_val) ** 2 for x in scores) / len(scores)
        std_dev = math.sqrt(variance) if variance > 0 else 1.0

        z_score = (scores[0] - self.mu) / std_dev
        return z_score, f"Z-Score điểm số: {z_score:.2f}"

    def calculate_kelly_percentage(self, confidence_pct):
        """Tầng 4: Công thức Kelly Quản lý tỷ lệ vào vốn"""
        p = confidence_pct / 100.0
        q = 1.0 - p
        b = 0.95  # Tỷ lệ thưởng giả định 1:0.95
        kelly = (b * p - q) / b
        if kelly <= 0:
            return 1  # Vốn tối thiểu 1%
        return round(min(15, kelly * 100 * 0.25)) # Cắt giảm 1/4 Kelly để an toàn vốn

    def analyze(self, history):
        data = []
        for p in history:
            if not isinstance(p, dict): continue
            tong = p.get('Tong') or p.get('tong') or 0
            ma_md5 = p.get('Ma_hash') or p.get('md5') or p.get('hash') or p.get('MD5') or ''
            if tong > 0:
                is_tai = 1 if tong >= 11 else 0
            else:
                kq = str(p.get('Ket_qua', '')).lower()
                is_tai = 1 if 'tai' in kq or 't' in kq else 0
                tong = 11 if is_tai else 8
            data.append({'is_tai': is_tai, 'tong': tong, 'md5': ma_md5})

        if not data:
            return "Tài", "🔴", 50, 50, 50, 1, "⚪", ["Chờ dữ liệu"]

        # 1. Chạy MD5 Deep Parsing (40% trọng số)
        latest_md5 = data[0]['md5']
        p_tai_md5, p_xiu_md5, ly_do_md5 = self.parse_md5_deep(latest_md5)

        # 2. Chạy Markov Bậc 2 (30% trọng số)
        m_tai, m_xiu, ly_do_markov = self.markov_2nd_order(data)
        p_tai_markov, p_xiu_markov = m_tai * 100, m_xiu * 100

        # 3. Chạy Z-Score Động lượng (30% trọng số)
        z_val, ly_do_z = self.calculate_z_score(data)
        p_tai_z, p_xiu_z = 50, 50
        if z_val > 1.4:
            p_xiu_z += 25
            p_tai_z -= 25
        elif z_val < -1.4:
            p_tai_z += 25
            p_xiu_z -= 25

        # TỔNG HỢP TRỌNG SỐ (ENSEMBLE VOTING)
        final_tai = (p_tai_md5 * 0.40) + (p_tai_markov * 0.30) + (p_tai_z * 0.30)
        final_xiu = (p_xiu_md5 * 0.40) + (p_xiu_markov * 0.30) + (p_xiu_z * 0.30)

        total_score = final_tai + final_xiu
        if total_score == 0: total_score = 1

        p_tai = round(max(10, min(90, (final_tai / total_score) * 100)))
        p_xiu = 100 - p_tai

        confidence = max(p_tai, p_xiu)
        du_doan = "Tài" if p_tai > p_xiu else "Xỉu"
        dot = "🔴" if du_doan == "Tài" else "🔵"

        # Tính toán phân bổ vốn Kelly
        kelly_bet = self.calculate_kelly_percentage(confidence)

        cau_list = ["🔴" if d['is_tai'] == 1 else "🔵" for d in data[:7]]
        cau_str = "".join(reversed(cau_list))

        reasons = [ly_do_md5, ly_do_markov, ly_do_z]
        return du_doan, dot, p_tai, p_xiu, confidence, kelly_bet, cau_str, reasons

# Khởi tạo Engine
engine = HybridUltraEngine()

# -------------------------------------------------------------
# FLASK & TELEGRAM BOT AUTOMATION
# -------------------------------------------------------------
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

last_phien = None
last_predict = None
stats = {"thang": 0, "thua": 0}

@app.route('/')
def home():
    return "Bot MD5 Hybrid Ultra Engine đang hoạt động 24/7!"

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
                    ma_md5 = curr.get('Ma_hash') or curr.get('md5') or curr.get('hash') or curr.get('MD5') or 'Chưa cập nhật'

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

                        tong_p = stats["thang"] + stats["thua"]
                        rate_win = round((stats["thang"] / tong_p) * 100, 1) if tong_p > 0 else 0

                        # Gọi hệ thống Hybrid Ultra Engine
                        du_doan, dot, r_tai, r_xiu, do_tin_cay, kelly_bet, cau_str, ly_do = engine.analyze(history)
                        phien_next = phien + 1 if isinstance(phien, int) else "N/A"

                        str_ly_do = "\n".join(f"• {ld}" for ld in ly_do)

                        msg = (
                            f"╭━━━ KẾT QUẢ SẢNH MD5 ━━━╮\n"
                            f" 📌 Phiên: {phien}\n"
                            f" 🎲 Xúc xắc: {xx1} · {xx2} · {xx3} → Tổng {tong}\n"
                            f" 🔑 Mã MD5: `{ma_md5}`\n"
                            f" 🎯 Kết quả: {kq}{status_eval}\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                            f"╭━━━ ⚡ HYBRID ULTRA ENGINE ⚡ ━━━╮\n"
                            f" 1️⃣2️⃣ Phiên kế tiếp: {phien_next}\n\n"
                            f" 🎯 Dự đoán: {du_doan} {dot}\n"
                            f" 📊 Độ tin cậy: {do_tin_cay}%\n"
                            f" 💰 Khuyên dùng vốn (Kelly): {kelly_bet}%\n"
                            f" ⚖️ Trọng số: Tài {r_tai}% · Xỉu {r_xiu}%\n"
                            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n"
                            f"💡 **Cơ sở phân tích đa tầng:**\n{str_ly_do}\n\n"
                            f"🌐 Cầu: {cau_str}\n"
                            f"📊 Thành tích: {stats['thang']} Thắng · {stats['thua']} Thua ({rate_win}%)\n"
                            f"🎮 Hybrid Ultra System Active"
                        )

                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        last_predict = du_doan
                        last_phien = phien
        except Exception as e:
            print(f"Lỗi Auto Loop MD5: {e}", flush=True)

        time.sleep(7)

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.reply_to(message, "Bot MD5 Hybrid Ultra Engine đã sẵn sàng!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    threading.Thread(target=auto_process, daemon=True).start()
    print("Khởi chạy Hybrid Ultra Engine thành công...", flush=True)
    bot.infinity_polling(skip_pending=True)
