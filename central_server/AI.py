import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from database.database import Database

class AIPredictor:
    def __init__(self):
        self.db = Database()
        print("[AI] ✅ Đã kết nối tới CSDL.")

    def fetch_data(self, mac_address: int, limit: int = 20) -> pd.DataFrame | None:
        query = """
            SELECT timestamp, cpu_usage, memory_percent, swap_percent
            FROM dynamic_info
            WHERE mac_address = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        try:
            self.db.mycursor.execute(query, (mac_address, limit))
            rows = self.db.mycursor.fetchall()
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=["timestamp", "cpu", "ram", "swap"])
            df = df.sort_values(by="timestamp").reset_index(drop=True)
            return df
        except Exception as e:
            print(f"[❌ DB ERROR] Lỗi khi truy vấn: {e}")
            return None

    def predict_next(self, df: pd.DataFrame, feature: str, step: int = 2):
        df = df.copy()
        df["step"] = range(len(df))
        df = df.dropna(subset=[feature, "step"])
        X = df[["step"]].astype(float)
        y = df[feature].astype(float)

        if len(X) < 5:
            raise ValueError("Không đủ dữ liệu để huấn luyện.")

        model = DecisionTreeRegressor()
        model.fit(X, y)

        future_steps = [[len(df) + i] for i in range(step)]
        preds = model.predict(future_steps)
        return preds.tolist()

    def predict_all(self, mac_address: int, step: int = 2):
        df = self.fetch_data(mac_address)
        if df is None or len(df) < 5:
            return None

        try:
            predictions = {
                "cpu": self.predict_next(df, "cpu", step),
                "ram": self.predict_next(df, "ram", step),
                "swap": self.predict_next(df, "swap", step),
            }
            return predictions
        except Exception as e:
            print(f"[❌ AI ERROR] {e}")
            return None

def admin_predict_interface():
    predictor = AIPredictor()
    while True:
        mac = input("\n[ADMIN] Nhập MAC address client cần dự đoán (hoặc 'exit'): ").strip()
        if mac.lower() == "exit":
            break

        try:
            mac_int = int(mac)
        except ValueError:
            print("❌ Vui lòng nhập MAC address dạng số nguyên (BIGINT)")
            continue

        df = predictor.fetch_data(mac_int)
        if df is None:
            print("❌ Không tìm thấy dữ liệu nào.")
            continue

        print(f"[DEBUG] Tổng số dòng dữ liệu: {len(df)}")
        print(df.tail())

        results = predictor.predict_all(mac_address=mac_int, step=2)
        if results is None:
            print("❌ Không đủ dữ liệu hoặc lỗi khi dự đoán.")
        else:
            print(f"\n📈 Dự đoán cho 2 phút tới (client {mac}):")
            print(f" - CPU:  {results['cpu'][0]:.2f}%, {results['cpu'][1]:.2f}%")
            print(f" - RAM:  {results['ram'][0]:.2f}%, {results['ram'][1]:.2f}%")
            print(f" - SWAP: {results['swap'][0]:.2f}%, {results['swap'][1]:.2f}%")

if __name__ == "__main__":
    admin_predict_interface()
