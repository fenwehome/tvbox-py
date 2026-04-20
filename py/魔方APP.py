# coding=utf-8
import base64
import json
import sys
from datetime import datetime

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ModuleNotFoundError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "魔方APP"
        self.host = "http://www.613mf4k12.top"
        self.api_path = "/api.php/getappapi"
        self.user_agent = "okhttp/3.10.0"
        self.aes_key = "1234567887654321"
        self.aes_iv = "1234567887654321"
        self.category_config = {
            "blockedNames": ["全部"],
            "renameMap": {},
            "forceOrder": ["电影", "连续剧", "综艺", "动漫", "短剧", "直播"],
        }
        self.area_merge_config = {
            "enabled": True,
            "displayName": "大陆",
            "mergeList": ["中国大陆", "大陆", "内地"],
        }
        self.ocr_api = "http://154.222.22.188:9898/ocr/b64/text"

    def init(self, extend=""):
        self.init_api = "initV119"
        self.search_api = "searchList"
        self.search_verify = False
        return None

    def getName(self):
        return self.name

    def homeVideoContent(self):
        return {"list": []}

    def _build_api_url(self, endpoint):
        path = str(endpoint or "").lstrip("/")
        return f"{self.host}{self.api_path}.index/{path}"

    def _headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip",
        }

    def _aes_encrypt(self, text):
        cipher = AES.new(self.aes_key.encode("utf-8"), AES.MODE_CBC, self.aes_iv.encode("utf-8"))
        return base64.b64encode(cipher.encrypt(pad(str(text).encode("utf-8"), AES.block_size))).decode("utf-8")

    def _aes_decrypt(self, text):
        cipher = AES.new(self.aes_key.encode("utf-8"), AES.MODE_CBC, self.aes_iv.encode("utf-8"))
        return unpad(cipher.decrypt(base64.b64decode(str(text or ""))), AES.block_size).decode("utf-8")

    def _replace_code(self, text):
        replacements = {
            "y": "9",
            "口": "0",
            "q": "0",
            "u": "0",
            "o": "0",
            ">": "1",
            "d": "0",
            "b": "8",
            "已": "2",
            "D": "0",
            "五": "5",
        }
        return "".join(replacements.get(char, char) for char in str(text or ""))

    def _api_post(self, endpoint, payload=None):
        data = {} if payload is None else dict(payload)
        response = self.post(
            self._build_api_url(endpoint),
            data=data,
            headers=self._headers(),
            timeout=10,
            verify=False,
        )
        body = json.loads(response.text or "{}")
        if not body.get("data"):
            return None
        return json.loads(self._aes_decrypt(body["data"]))

    def _process_classes(self, type_list):
        blocked = set(self.category_config.get("blockedNames", []))
        rename_map = self.category_config.get("renameMap", {})
        order_map = {name: index for index, name in enumerate(self.category_config.get("forceOrder", []))}
        classes = [
            {
                "type_id": item.get("type_id", ""),
                "type_name": rename_map.get(item.get("type_name", ""), item.get("type_name", "")),
            }
            for item in type_list
            if item.get("type_name") not in blocked
        ]
        classes.sort(key=lambda item: order_map.get(item["type_name"], 999))
        return classes

    def _merge_area_filter(self, values):
        merge_values = set(self.area_merge_config.get("mergeList", []))
        raw_values = list(values)
        if not self.area_merge_config.get("enabled") or not any(value in merge_values for value in raw_values):
            return raw_values
        result = [value for value in raw_values if value not in merge_values]
        index = result.index("全部") + 1 if "全部" in result else 0
        result.insert(index, self.area_merge_config.get("displayName", "大陆"))
        return result

    def _convert_filters(self, type_list):
        name_map = {"class": "类型", "area": "地区", "lang": "语言", "year": "年份", "sort": "排序"}
        current_year = str(datetime.now().year)
        filters = {}
        for item in type_list:
            entries = []
            for config in item.get("filter_type_list", []):
                raw_name = config.get("name", "")
                values = list(config.get("list", []))
                if raw_name == "area":
                    values = self._merge_area_filter(values)
                if raw_name == "year" and current_year not in values:
                    index = values.index("全部") + 1 if "全部" in values else 0
                    values.insert(index, current_year)
                entries.append(
                    {
                        "key": "by" if raw_name == "sort" else raw_name,
                        "name": name_map.get(raw_name, raw_name),
                        "value": [{"n": value, "v": value} for value in values],
                    }
                )
            filters[item.get("type_id", "")] = entries
        return filters

    def homeContent(self, filter):
        init_data = self._api_post(self.init_api) or {"type_list": [], "config": {}}
        self.search_verify = bool(init_data.get("config", {}).get("system_search_verify_status"))
        return {
            "class": self._process_classes(init_data.get("type_list", [])),
            "filters": self._convert_filters(init_data.get("type_list", [])),
            "list": [vod for item in init_data.get("type_list", []) for vod in item.get("recommend_list", [])],
        }

    def _page_result(self, items, pg, limit=90, total=None):
        page = int(pg)
        return {
            "page": page,
            "limit": limit,
            "total": len(items) if total is None else total,
            "list": items,
        }

    def _merge_area_search(self, tid, pg, extend):
        seen = set()
        merged = []
        for area in self.area_merge_config.get("mergeList", []):
            payload = {
                "type_id": str(tid),
                "page": str(pg),
                "area": area,
                "year": extend.get("year", "全部"),
                "sort": extend.get("by", "最新"),
                "lang": extend.get("lang", "全部"),
                "class": extend.get("class", "全部"),
            }
            result = self._api_post("typeFilterVodList", payload) or {}
            for item in result.get("recommend_list", []):
                vod_id = item.get("vod_id")
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                merged.append(item)
        return merged

    def categoryContent(self, tid, pg, filter, extend):
        options = dict(extend or {})
        if options.get("area") == self.area_merge_config.get("displayName"):
            return self._page_result(self._merge_area_search(tid, pg, options), pg)
        payload = {
            "type_id": str(tid),
            "page": str(pg),
            "area": options.get("area", "全部"),
            "year": options.get("year", "全部"),
            "sort": options.get("by", "最新"),
            "lang": options.get("lang", "全部"),
            "class": options.get("class", "全部"),
        }
        result = self._api_post("typeFilterVodList", payload) or {}
        return self._page_result(result.get("recommend_list", []), pg)

    def _get_verification_code(self):
        return None

    def searchContent(self, key, quick, pg="1"):
        if self.search_verify:
            verify = self._get_verification_code()
            if not verify:
                return {
                    "page": int(pg),
                    "limit": 90,
                    "total": 0,
                    "list": [],
                    "msg": "验证码获取失败",
                }
        result = self._api_post(
            self.search_api,
            {"keywords": str(key or ""), "type_id": "0", "page": str(pg)},
        ) or {}
        keyword = str(key or "").strip().lower()
        items = []
        for item in result.get("search_list", []):
            vod_class = str(item.get("vod_class", ""))
            text = " ".join(
                [str(item.get("vod_name", "")), str(item.get("vod_remarks", "")), vod_class]
            ).lower()
            if "屏蔽预留" in vod_class:
                continue
            if keyword and keyword not in text:
                continue
            items.append(
                {
                    "vod_id": item.get("vod_id", ""),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": " ".join(
                        value for value in [str(item.get("vod_year", "")), vod_class] if value
                    ).strip(),
                }
            )
        return self._page_result(items, pg)
