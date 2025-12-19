import math
import datetime
from lunardate import LunarDate

class RetailTools:
    @staticmethod
    def calculate(expression: str):
        try:
            allowed = set("0123456789.+-*/() ")
            if not all(c in allowed for c in expression): return "Error"
            return str(eval(expression, {"__builtins__": None}, {}))
        except: return "Error"

    @staticmethod
    def get_lunar_date():
        today = datetime.date.today()
        lunar = LunarDate.fromSolarDate(today.year, today.month, today.day)
        return f"{lunar.day}/{lunar.month}/{lunar.year} (Lunar)"

    @staticmethod
    def health_check(saas_api, store_id):
        """
        Runs a quick scan of the store's vitals.
        Returns a list of alerts (if any).
        """
        alerts = []
        
        # 1. Check Sales
        sales = saas_api.get_sales_report(store_id, "today")
        if sales['revenue'] == 0:
            alerts.append("⚠️ Chưa có doanh thu hôm nay.")
        
        # 2. Check Inventory (Mock check for 'Critical' items)
        # In real app, this would query DB for stock < threshold
        critical_items = ["Áo Khoác Gió"] # Mock result
        if critical_items:
            alerts.append(f"📦 Sắp hết hàng: {', '.join(critical_items)}")
            
        return alerts