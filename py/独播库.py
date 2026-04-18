# coding=utf-8
import sys

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
