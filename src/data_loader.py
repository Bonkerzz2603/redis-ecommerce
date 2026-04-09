"""
Module kết nối và tải dữ liệu từ Redis Server.

Đọc dữ liệu Retailrocket đã được import vào Redis bởi import.py.
Cấu trúc Redis:
  - user:{visitorid}:events   → LIST of JSON {itemid, event, timestamp}
  - item:{itemid}:users       → SET of visitor IDs
  - item:{itemid}:props        → HASH {categoryid, available}
  - category:{categoryid}     → HASH {parent}
"""

import redis
import pandas as pd
import json


class RedisDataLoader:
    #Kết nối Redis và tải dữ liệu thành DataFrame.

    def __init__(self, host="localhost", port=6379, db=0, password=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client = None

    def connect(self):
        #Tạo kết nối đến Redis Server.
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=5,
        )
        self.client.ping()  # kiểm tra kết nối
        return True

    def disconnect(self):
        #Đóng kết nối.
        if self.client:
            self.client.close()
            self.client = None

    def is_connected(self):
        #Kiểm tra kết nối Redis còn sống không.
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            return False

    def get_redis_info(self):
        #Lấy thông tin Redis Server.
        if not self.is_connected():
            return {}
        info = self.client.info()
        return {
            "redis_version": info.get("redis_version", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "total_keys": self.client.dbsize(),
        }

    def count_keys(self, pattern):
        #Đếm số key theo pattern (dùng SCAN, không block).
        count = 0
        for _ in self.client.scan_iter(match=pattern, count=500):
            count += 1
        return count

    def get_stats(self):
        #Lấy thống kê nhanh về dữ liệu trong Redis.
        stats = {}
        stats["total_keys"] = self.client.dbsize()
        stats["user_keys"] = self.count_keys("user:*:events")
        stats["item_user_keys"] = self.count_keys("item:*:users")
        stats["item_prop_keys"] = self.count_keys("item:*:props")
        stats["category_keys"] = self.count_keys("category:*")
        return stats

    # ------------------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------------------
    def load_events(self, max_users=None, max_events_per_user=None):
        """
        Tải events từ Redis thành DataFrame.

        Parameters
        ----------
        max_users : int, optional
            Giới hạn số user đọc (để preview nhanh).
        max_events_per_user : int, optional
            Giới hạn số event/user.

        Returns
        -------
        pd.DataFrame
            Columns: visitorid, itemid, event, timestamp
        """
        rows = []
        user_count = 0

        for key in self.client.scan_iter(match="user:*:events", count=500):
            # key = "user:12345:events"
            parts = key.split(":")
            if len(parts) != 3:
                continue
            visitor_id = int(parts[1])

            if max_events_per_user:
                events_json = self.client.lrange(key, 0, max_events_per_user - 1)
            else:
                events_json = self.client.lrange(key, 0, -1)

            for ej in events_json:
                try:
                    ev = json.loads(ej)
                    rows.append({
                        "visitorid": visitor_id,
                        "itemid": ev.get("itemid"),
                        "event": ev.get("event"),
                        "timestamp": ev.get("timestamp"),
                    })
                except (json.JSONDecodeError, TypeError):
                    continue

            user_count += 1
            if max_users and user_count >= max_users:
                break

        df = pd.DataFrame(rows, columns=["visitorid", "itemid", "event", "timestamp"])
        return df

    # ------------------------------------------------------------------
    # ITEM PROPERTIES
    # ------------------------------------------------------------------
    def load_item_properties(self, max_items=None):
        """
        Tải item properties từ Redis thành DataFrame.

        Parameters
        ----------
        max_items : int, optional
            Giới hạn số item đọc.

        Returns
        -------
        pd.DataFrame
            Columns: itemid, categoryid, available
        """
        rows = []
        item_count = 0

        for key in self.client.scan_iter(match="item:*:props", count=500):
            parts = key.split(":")
            if len(parts) != 3:
                continue
            item_id = int(parts[1])

            props = self.client.hgetall(key)
            row = {"itemid": item_id}
            row.update(props)
            rows.append(row)

            item_count += 1
            if max_items and item_count >= max_items:
                break

        df = pd.DataFrame(rows)
        if "itemid" not in df.columns and len(df) == 0:
            df = pd.DataFrame(columns=["itemid", "categoryid", "available"])
        return df

    # ------------------------------------------------------------------
    # CATEGORY TREE
    # ------------------------------------------------------------------
    def load_category_tree(self, max_categories=None):
        """
        Tải category tree từ Redis thành DataFrame.

        Parameters
        ----------
        max_categories : int, optional
            Giới hạn số category đọc.

        Returns
        -------
        pd.DataFrame
            Columns: categoryid, parentid
        """
        rows = []
        cat_count = 0

        for key in self.client.scan_iter(match="category:*", count=500):
            parts = key.split(":")
            if len(parts) != 2:
                continue
            cat_id = int(parts[1])

            data = self.client.hgetall(key)
            parent = data.get("parent", -1)
            parent = int(parent) if parent != "-1" else None

            rows.append({
                "categoryid": cat_id,
                "parentid": parent,
            })

            cat_count += 1
            if max_categories and cat_count >= max_categories:
                break

        df = pd.DataFrame(rows, columns=["categoryid", "parentid"])
        return df

    # ------------------------------------------------------------------
    # ITEM-USERS (recommendation)
    # ------------------------------------------------------------------
    def load_item_users(self, max_items=None):
        """
        Tải mapping item → users từ Redis.

        Parameters
        ----------
        max_items : int, optional
            Giới hạn số item đọc.

        Returns
        -------
        pd.DataFrame
            Columns: itemid, user_count, users (list)
        """
        rows = []
        item_count = 0

        for key in self.client.scan_iter(match="item:*:users", count=500):
            parts = key.split(":")
            if len(parts) != 3:
                continue
            item_id = int(parts[1])

            user_count = self.client.scard(key)
            rows.append({
                "itemid": item_id,
                "user_count": user_count,
            })

            item_count += 1
            if max_items and item_count >= max_items:
                break

        df = pd.DataFrame(rows, columns=["itemid", "user_count"])
        if len(df) > 0:
            df = df.sort_values("user_count", ascending=False).reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # LOAD ALL
    # ------------------------------------------------------------------
    def load_all(self, max_users=500, max_items=1000, max_categories=None):
        """
        Tải tất cả dữ liệu từ Redis.

        Returns
        -------
        dict of DataFrames
        """
        data = {}
        data["events"] = self.load_events(max_users=max_users)
        data["item_properties"] = self.load_item_properties(max_items=max_items)
        data["category_tree"] = self.load_category_tree(max_categories=max_categories)
        data["item_users"] = self.load_item_users(max_items=max_items)
        return data
