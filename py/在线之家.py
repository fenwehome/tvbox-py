# coding=utf-8
import json
import re
import sys
from urllib.parse import quote

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "在线之家"
        self.host = "https://www.zxzjhd.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "美剧"},
            {"type_id": "3", "type_name": "韩剧"},
            {"type_id": "4", "type_name": "日剧"},
            {"type_id": "5", "type_name": "泰剧"},
            {"type_id": "6", "type_name": "动漫"},
        ]
        sort_values = [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]
        self.filter_def = {key: {"cateId": key} for key in ["1", "2", "3", "4", "5", "6"]}
        self.filters = {
            "1": [
                {
                    "key": "class",
                    "name": "剧情",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "喜剧", "v": "喜剧"}],
                },
                {
                    "key": "area",
                    "name": "地区",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "欧美", "v": "欧美"}],
                },
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "2": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "3": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "4": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "5": [
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "6": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {"key": "area", "name": "地区", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        return {"list": []}

    def _normalize_ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if not extend:
            return {}
        try:
            return json.loads(str(extend))
        except Exception:
            return {}

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/" + raw

    def _build_category_url(self, tid, pg, extend):
        values = dict(self.filter_def.get(str(tid), {"cateId": str(tid)}))
        values.update(self._normalize_ext(extend))
        path = (
            f"{values.get('cateId', tid)}-"
            f"{values.get('area', '')}-"
            f"{values.get('by', '')}-"
            f"{values.get('class', '')}"
            f"-----{int(pg)}---"
            f"{values.get('year', '')}"
        )
        return self._build_url(f"/vodshow/{path}.html")

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _fix_json_wrapped_html(self, html):
        value = str(html or "").strip()
        if value.startswith("<"):
            return value
        if value.startswith('"') and value.endswith('"'):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, str) and parsed.startswith("<"):
                    return parsed.strip()
            except Exception:
                return value
        return value

    def _request_html(self, path_or_url, referer=None):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        return self._fix_json_wrapped_html(response.text or "")

    def _extract_vod_id(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"/?(voddetail/\d+\.html)", raw)
        return matched.group(1) if matched else ""

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        seen = set()
        for node in root.xpath("//ul[contains(@class,'stui-vodlist')]//li"):
            href = ((node.xpath(".//a[@href][1]/@href") or [""])[0]).strip()
            vod_id = self._extract_vod_id(href)
            title = ((node.xpath(".//a[@title][1]/@title") or [""])[0]).strip()
            pic = (
                ((node.xpath(".//a[@data-original][1]/@data-original") or [""])[0]).strip()
                or ((node.xpath(".//img[@data-original][1]/@data-original") or [""])[0]).strip()
                or ((node.xpath(".//img[@src][1]/@src") or [""])[0]).strip()
            )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'pic-text')][1]//text()")))
            if not vod_id or not title or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        items = self._parse_cards(self._request_html(self._build_category_url(tid, pg, extend)))
        return {"list": items, "page": page, "limit": 24, "total": page * 30 + len(items)}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        url = self._build_url("/vodsearch/{0}-------------.html".format(quote(str(key or "").strip())))
        items = self._parse_cards(self._request_html(url))
        return {"list": items, "page": page, "limit": len(items), "total": len(items)}
