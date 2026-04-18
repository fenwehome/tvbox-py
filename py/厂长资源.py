# coding=utf-8
import sys
from urllib.parse import urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "厂长资源"
        self.hosts = [
            "https://www.cz01.org",
            "https://www.czzy89.com",
        ]
        self.current_host = self.hosts[0]
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        self.categories = [
            {"type_name": "电影", "type_id": "movie"},
            {"type_name": "电视剧", "type_id": "tv"},
            {"type_name": "动漫", "type_id": "anime"},
            {"type_name": "华语电影", "type_id": "cn_movie"},
            {"type_name": "印度电影", "type_id": "in_movie"},
            {"type_name": "俄罗斯电影", "type_id": "ru_movie"},
            {"type_name": "加拿大电影", "type_id": "ca_movie"},
            {"type_name": "日本电影", "type_id": "jp_movie"},
            {"type_name": "韩国电影", "type_id": "kr_movie"},
            {"type_name": "欧美电影", "type_id": "western_movie"},
            {"type_name": "国产剧", "type_id": "cn_drama"},
            {"type_name": "日剧", "type_id": "jp_drama"},
            {"type_name": "美剧", "type_id": "us_drama"},
            {"type_name": "韩剧", "type_id": "kr_drama"},
            {"type_name": "海外剧", "type_id": "intl_drama"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        return {"list": []}

    def _parse_media_cards(self, html, host):
        root = self.html(html)
        results = []
        if root is None:
            return results

        for item in root.xpath("//li[.//a[@href]]"):
            href = (item.xpath(".//a[@href][1]/@href") or [""])[0].strip()
            if not href:
                continue

            title = (
                (item.xpath(".//img[@alt][1]/@alt") or [""])[0].strip()
                or (item.xpath(".//a[@title][1]/@title") or [""])[0].strip()
                or "".join(item.xpath(".//a[1]//text()")).strip()
            )

            pic = ""
            for expr in [
                ".//img[@data-original][1]/@data-original",
                ".//img[@data-src][1]/@data-src",
                ".//img[@src][1]/@src",
            ]:
                pic = (item.xpath(expr) or [""])[0].strip()
                if pic:
                    break

            remarks = (
                (item.xpath(".//*[contains(@class,'jidi')][1]/text()") or [""])[0].strip()
                or (item.xpath(".//*[contains(@class,'hdinfo')][1]/text()") or [""])[0].strip()
            )

            results.append(
                {
                    "vod_id": href,
                    "vod_name": title or "未命名",
                    "vod_pic": urljoin(host, pic) if pic.startswith("/") else pic,
                    "vod_remarks": remarks,
                }
            )

        return results
