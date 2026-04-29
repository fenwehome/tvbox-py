# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    BASE_URL = "https://1.star2.cn"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    )
    CATEGORIES = [
        ("ju", "国剧"),
        ("zy", "综艺"),
        ("mv", "电影"),
        ("rh", "日韩"),
        ("ym", "英美"),
        ("wj", "外剧"),
        ("dm", "动漫"),
    ]
    PAN_TITLES = {
        "quark": "夸克资源",
        "ali": "阿里资源",
        "115": "115资源",
        "tianyi": "天翼资源",
        "uc": "UC资源",
        "baidu": "百度资源",
        "xunlei": "迅雷资源",
        "123pan": "123资源",
        "yd": "移动云盘资源",
    }
    PAN_ORDER = ["quark", "ali", "115", "tianyi", "uc", "baidu", "xunlei", "123pan", "yd"]

    def __init__(self):
        self.name = "双星"
        self.cookie = ""

    def init(self, extend=""):
        response = self.fetch(
            self.BASE_URL,
            headers={"User-Agent": self.UA, "Referer": self.BASE_URL},
            allow_redirects=False,
            timeout=15,
        )
        if response.status_code != 200:
            return None
        self.cookie = "; ".join([f"{name}={value}" for name, value in dict(response.cookies).items()])
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": [{"type_id": type_id, "type_name": type_name} for type_id, type_name in self.CATEGORIES]}

    def homeVideoContent(self):
        return {"list": []}

    def _headers(self):
        headers = {"User-Agent": self.UA, "Referer": self.BASE_URL}
        if self.cookie:
            headers["cookie"] = self.cookie
        return headers

    def _detect_pan_type(self, link):
        text = str(link or "").strip().lower()
        if "quark" in text:
            return "quark"
        if "115.com" in text:
            return "115"
        if "cloud.189.cn" in text:
            return "tianyi"
        if "drive.uc.cn" in text or "uc.cn" in text:
            return "uc"
        if "pan.baidu.com" in text:
            return "baidu"
        if "xunlei" in text:
            return "xunlei"
        if "123pan" in text:
            return "123pan"
        if "caiyun" in text or "139.com" in text:
            return "yd"
        if "aliyundrive" in text or "alipan" in text:
            return "ali"
        return ""

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _get_html(self, url):
        response = self.fetch(url, headers=self._headers(), timeout=15)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("/html/body/div/div/main/div/ul/li"):
            href = "".join(node.xpath(".//div[contains(@class,'a')]//a[1]/@href")).strip()
            title = self._clean_text("".join(node.xpath(".//div[contains(@class,'a')]//a[1]//text()")))
            if not href or not title:
                continue
            items.append({"vod_id": href, "vod_name": title, "vod_pic": "", "vod_remarks": ""})
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        items = self._parse_cards(self._get_html(f"{self.BASE_URL}/{str(tid).strip()}_{page}/"))
        return {"page": page, "limit": 15, "total": (page - 1) * 15 + len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        items = self._parse_cards(self._get_html(f"{self.BASE_URL}/search/?keyword={quote(keyword)}&page={page}"))
        return {"page": page, "total": len(items), "list": items}

    def _build_pan_lines(self, share_links):
        groups = {}
        seen = set()
        for link in share_links:
            raw = str(link or "").strip()
            pan_type = self._detect_pan_type(raw)
            if not raw or not pan_type or raw in seen:
                continue
            seen.add(raw)
            groups.setdefault(pan_type, []).append(f"{self.PAN_TITLES[pan_type]}${raw}")
        if not groups:
            return {"vod_play_from": "", "vod_play_url": ""}
        names = [name for name in self.PAN_ORDER if name in groups]
        return {
            "vod_play_from": "$$$".join(names),
            "vod_play_url": "$$$".join("#".join(groups[name]) for name in names),
        }

    def detailContent(self, ids):
        vod_id = str((ids or [""])[0] or "").strip()
        if not vod_id:
            return {"list": []}
        html = self._get_html(urljoin(self.BASE_URL, vod_id))
        root = self.html(html)
        if root is None:
            return {"list": []}
        title = self._clean_text(
            "".join(
                root.xpath(
                    "/html/body/div/div[contains(@class,'s20erx') and contains(@class,'erx-content')]/main/article/h1//text()"
                )
            )
        )
        share_links = [
            str(value).strip()
            for value in root.xpath("//*[@id='maximg']//div[contains(@class,'dlipp-cont-bd')]//a[@href]/@href")
        ]
        play = self._build_pan_lines(share_links)
        return {
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_remarks": "",
                    "vod_content": "",
                    "vod_director": "",
                    "vod_actor": "",
                    "vod_play_from": play["vod_play_from"],
                    "vod_play_url": play["vod_play_url"],
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags):
        target = str(id or "").strip()
        if self._detect_pan_type(target):
            return {"parse": 0, "playUrl": "", "url": target}
        return {"parse": 0, "playUrl": "", "url": ""}
