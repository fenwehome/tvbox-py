# coding=utf-8
import sys
from urllib.parse import quote

from lxml import etree

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "独播库"
        self.host = "https://www.dbku.tv"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        self.categories = [
            {"type_name": "连续剧", "type_id": "index"},
            {"type_name": "电影", "type_id": "movie"},
            {"type_name": "综艺", "type_id": "variety"},
            {"type_name": "动漫", "type_id": "anime"},
            {"type_name": "港剧", "type_id": "hk"},
            {"type_name": "陆剧", "type_id": "luju"},
        ]
        self.category_paths = {
            "index": "/vodtype/2--------{pg}---.html",
            "movie": "/vodtype/1--------{pg}---.html",
            "variety": "/vodtype/3--------{pg}---.html",
            "anime": "/vodtype/4--------{pg}---.html",
            "hk": "/vodtype/20--------{pg}---.html",
            "luju": "/vodtype/13--------{pg}---.html",
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        return {"list": []}

    def _build_url(self, href):
        raw = str(href or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/" + raw

    def _parse_list_cards(self, html):
        root = self.html(html)
        results = []
        if root is None:
            return results

        cards = root.xpath("//*[contains(@class,'myui-vodlist__box')]")
        seen = set()
        for card in cards:
            href = ""
            title = ""
            pic = ""
            for anchor in card.xpath(".//a[@href]"):
                raw_href = (anchor.xpath("./@href") or [""])[0].strip()
                if "/voddetail/" in raw_href:
                    href = self._build_url(raw_href)
                    title = (
                        (anchor.xpath("./@title") or [""])[0].strip()
                        or "".join(anchor.xpath(".//text()")).strip()
                    )
                    pic = (
                        (anchor.xpath("./@data-original") or [""])[0].strip()
                        or (anchor.xpath("./@src") or [""])[0].strip()
                    )
                    break
            if not href or href in seen or not title:
                continue

            remarks = "".join(card.xpath(".//*[contains(@class,'pic-text')][1]//text()")).strip()
            seen.add(href)
            results.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return results

    def _request_html(self, path_or_url, expect_xpath=None, referer=None):
        target = path_or_url if path_or_url.startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.host
        headers["Origin"] = self.host
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        html = response.text or ""
        if expect_xpath:
            root = self.html(html)
            if root is None or not root.xpath(expect_xpath):
                return ""
        return html

    def _parse_cards_from_nodes(self, nodes):
        results = []
        seen = set()
        for card in nodes:
            snippet = self._parse_list_cards(etree.tostring(card, encoding="unicode"))
            for item in snippet:
                if item["vod_id"] in seen:
                    continue
                seen.add(item["vod_id"])
                results.append(item)
        return results

    def _parse_search_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        search_list = root.xpath("//*[@id='searchList']")
        if search_list:
            cards = search_list[0].xpath(".//*[contains(@class,'myui-vodlist__box')]")
            parsed = self._parse_cards_from_nodes(cards)
            if parsed:
                return parsed
        return self._parse_list_cards(html)

    def _page_result(self, items, pg):
        page = int(pg)
        pagecount = page + 1 if items else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": len(items),
            "total": pagecount * max(len(items), 1),
        }

    def categoryContent(self, tid, pg, filter, extend):
        path = self.category_paths.get(tid, self.category_paths["index"]).format(pg=pg)
        html = self._request_html(path, expect_xpath="//*[contains(@class,'myui-vodlist__box')]")
        return self._page_result(self._parse_list_cards(html), pg)

    def searchContent(self, key, quick, pg="1"):
        path = "/vodsearch/-------------.html?wd={0}&submit=".format(quote(key))
        html = self._request_html(path, expect_xpath="//*[@id='searchList']|//*[contains(@class,'myui-vodlist__box')]")
        return self._page_result(self._parse_search_cards(html), pg)
