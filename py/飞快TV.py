# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "飞快TV"
        self.host = "https://feikuai.tv"
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": self.host + "/",
            "Origin": self.host,
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return {"list": []}

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw)

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _request_html(self, path_or_url):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        response = self.fetch(target, headers=self.headers, timeout=10)
        if response.status_code != 200:
            return ""
        return str(response.text or "")

    def _parse_category_cards(self, html):
        root = self.html(html or "")
        if root is None:
            return []
        items = []
        for node in root.xpath("//a[contains(@class,'module-poster-item')]"):
            vod_id = self._clean_text("".join(node.xpath("./@href")))
            vod_name = self._clean_text("".join(node.xpath("./@title"))) or self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-poster-item-title')][1]//text()"))
            )
            vod_pic = self._clean_text(
                "".join(node.xpath(".//img[contains(@class,'lazy')][1]/@data-original"))
            )
            vod_remarks = self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-item-note')][1]//text()"))
            )
            if vod_id and vod_name:
                items.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": self._build_url(vod_pic),
                        "vod_remarks": vod_remarks,
                    }
                )
        return items

    def _parse_search_cards(self, html):
        root = self.html(html or "")
        if root is None:
            return []
        items = []
        for node in root.xpath(
            "//*[contains(@class,'module-card-item') and contains(@class,'module-item')]"
        ):
            vod_id = self._clean_text(
                "".join(node.xpath(".//a[contains(@class,'module-card-item-poster')][1]/@href"))
            )
            vod_name = self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-card-item-title')][1]//strong/text()"))
            )
            vod_pic = self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@data-original"))
            )
            vod_remarks = self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-item-note')][1]//text()"))
            )
            if vod_id and vod_name:
                items.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": self._build_url(vod_pic),
                        "vod_remarks": vod_remarks,
                    }
                )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg))
        url = self.host + f"/vodshow/{tid}--------{page}---.html"
        items = self._parse_category_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg))
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "limit": 0, "total": 0, "list": []}
        url = self.host + "/label/search_ajax.html?wd=" + quote(keyword) + f"&by=time&order=desc&page={page}"
        items = self._parse_search_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}
