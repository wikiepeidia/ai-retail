import sqlite3
import random
from src.core.config import Config

class SaasAPI:
    """
    Simulates the backend API of KiotViet/Sapo.
    The Agent calls this to get 'Real' business data.
    """
    def __init__(self):
        self.config = Config()
        
    def _get_conn(self):
        return sqlite3.connect(self.config.DB_PATH, check_same_thread=False)

    def get_sales_report(self, store_id, period="today"):
        """Returns sales data for the given period."""
        # In a real app, this queries PostgreSQL or an External API
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Mock logic for different periods
        if period == "today":
            date_str = "date('now', 'localtime')" # SQLite syntax
        else:
            return {"error": "Only 'today' is supported in this prototype."}
            
        cursor.execute(f"SELECT SUM(amount), COUNT(*) FROM sales WHERE store_id = ? AND date = {date_str}", (store_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res and res[0]:
            return {"revenue": res[0], "orders": res[1], "period": period}
        return {"revenue": 0, "orders": 0, "period": period}

    def check_inventory(self, product_name):
        """Fuzzy searches for a product and returns stock level."""
        # Mocking inventory data since we didn't create a table for it yet
        mock_inventory = {
            "bỉm": {"name": "Bỉm Bobby Size M", "stock": 45, "status": "High"},
            "sữa": {"name": "Sữa Meiji Số 9", "stock": 12, "status": "Low"},
            "quần": {"name": "Quần Chục Cotton", "stock": 100, "status": "High"},
            "áo":  {"name": "Áo Khoác Gió", "stock": 5, "status": "Critical"}
        }
        
        for key, data in mock_inventory.items():
            if key in product_name.lower():
                return data
        
        return {"error": "Product not found in inventory."}

    def get_customer_info(self, phone_or_name):
        """Simulates a CRM lookup."""
        # Mock CRM
        if "09" in phone_or_name:
            return {"name": "Chị Lan", "rank": "VIP", "last_purchase": "2 days ago"}
        return {"error": "Customer not found."}