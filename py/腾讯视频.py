# coding=utf-8
import re
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "腾讯视频"
        self.base_host = "https://v.qq.com"
        self.header = {"User-Agent": "PC_UA"}
        self.classes = [
            {"type_id": "choice", "type_name": "精选"},
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "tv", "type_name": "电视剧"},
            {"type_id": "variety", "type_name": "综艺"},
            {"type_id": "cartoon", "type_name": "动漫"},
            {"type_id": "child", "type_name": "少儿"},
            {"type_id": "doco", "type_name": "纪录片"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _headers(self):
        return dict(self.header)

    def _parse_list_items(self, html, with_channel=False, channel_id=""):
        videos = []
        list_items = re.findall(
            r'<div[^>]*class=["\']?list_item["\']?[^>]*>([\s\S]*?)</div>',
            str(html or ""),
            re.I,
        )
        for item in list_items:
            title_match = re.search(r'<img[^>]*alt=["\']?([^"\']*)["\']?', item, re.I)
            pic_match = re.search(r'<img[^>]*src=["\']?([^"\'\s>]+)["\']?', item, re.I)
            desc_values = [
                re.sub(r"<[^>]*>", "", value).strip()
                for value in re.findall(r'<a[^>]*>([\s\S]*?)</a>', item, re.I)
            ]
            url_match = re.search(r'<a[^>]*data-float=["\']?([^"\'\s>]+)["\']?', item, re.I)
            if not title_match or not pic_match:
                continue
            source_id = url_match.group(1) if url_match else ""
            vod_id = f"{channel_id}${source_id}" if with_channel else source_id
            videos.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title_match.group(1) or "",
                    "vod_pic": pic_match.group(1) or "",
                    "vod_remarks": next((value for value in reversed(desc_values) if value), ""),
                }
            )
        return videos

    def homeContent(self, filter):
        url = (
            f"{self.base_host}/x/bu/pagesheet/list?_all=1&append=1&channel=cartoon"
            "&listpage=1&offset=0&pagesize=21&iarea=-1&sort=18"
        )
        response = self.fetch(url, headers=self._headers())
        videos = self._parse_list_items(getattr(response, "text", ""), with_channel=False)
        return {"class": self.classes, "list": videos[:20]}

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 1, "jx": 1, "url": id, "header": self._headers()}
