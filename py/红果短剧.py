# coding=utf-8
import json
import re
import sys
from urllib.parse import quote

from base.spider import Spider as BaseSpider

sys.path.append("..")


CLASS_LIST = [
    {"type_id": "逆袭", "type_name": "🎬逆袭"},
    {"type_id": "霸总", "type_name": "🎬霸总"},
    {"type_id": "现代言情", "type_name": "🎬现代言情"},
    {"type_id": "打脸虐渣", "type_name": "🎬打脸虐渣"},
    {"type_id": "豪门恩怨", "type_name": "🎬豪门恩怨"},
    {"type_id": "神豪", "type_name": "🎬神豪"},
    {"type_id": "马甲", "type_name": "🎬马甲"},
    {"type_id": "都市日常", "type_name": "🎬都市日常"},
    {"type_id": "战神归来", "type_name": "🎬战神归来"},
    {"type_id": "小人物", "type_name": "🎬小人物"},
    {"type_id": "女性成长", "type_name": "🎬女性成长"},
    {"type_id": "大女主", "type_name": "🎬大女主"},
    {"type_id": "穿越", "type_name": "🎬穿越"},
    {"type_id": "都市修仙", "type_name": "🎬都市修仙"},
    {"type_id": "强者回归", "type_name": "🎬强者回归"},
    {"type_id": "亲情", "type_name": "🎬亲情"},
    {"type_id": "古装", "type_name": "🎬古装"},
    {"type_id": "重生", "type_name": "🎬重生"},
    {"type_id": "闪婚", "type_name": "🎬闪婚"},
    {"type_id": "赘婿逆袭", "type_name": "🎬赘婿逆袭"},
    {"type_id": "虐恋", "type_name": "🎬虐恋"},
    {"type_id": "追妻", "type_name": "🎬追妻"},
    {"type_id": "天下无敌", "type_name": "🎬天下无敌"},
    {"type_id": "家庭伦理", "type_name": "🎬家庭伦理"},
    {"type_id": "萌宝", "type_name": "🎬萌宝"},
    {"type_id": "古风权谋", "type_name": "🎬古风权谋"},
    {"type_id": "职场", "type_name": "🎬职场"},
    {"type_id": "奇幻脑洞", "type_name": "🎬奇幻脑洞"},
    {"type_id": "异能", "type_name": "🎬异能"},
    {"type_id": "无敌神医", "type_name": "🎬无敌神医"},
    {"type_id": "古风言情", "type_name": "🎬古风言情"},
    {"type_id": "传承觉醒", "type_name": "🎬传承觉醒"},
    {"type_id": "现言甜宠", "type_name": "🎬现言甜宠"},
    {"type_id": "奇幻爱情", "type_name": "🎬奇幻爱情"},
    {"type_id": "乡村", "type_name": "🎬乡村"},
    {"type_id": "历史古代", "type_name": "🎬历史古代"},
    {"type_id": "王妃", "type_name": "🎬王妃"},
    {"type_id": "高手下山", "type_name": "🎬高手下山"},
    {"type_id": "娱乐圈", "type_name": "🎬娱乐圈"},
    {"type_id": "强强联合", "type_name": "🎬强强联合"},
    {"type_id": "破镜重圆", "type_name": "🎬破镜重圆"},
    {"type_id": "暗恋成真", "type_name": "🎬暗恋成真"},
    {"type_id": "民国", "type_name": "🎬民国"},
    {"type_id": "欢喜冤家", "type_name": "🎬欢喜冤家"},
    {"type_id": "系统", "type_name": "🎬系统"},
    {"type_id": "真假千金", "type_name": "🎬真假千金"},
    {"type_id": "龙王", "type_name": "🎬龙王"},
    {"type_id": "校园", "type_name": "🎬校园"},
    {"type_id": "穿书", "type_name": "🎬穿书"},
    {"type_id": "女帝", "type_name": "🎬女帝"},
    {"type_id": "团宠", "type_name": "🎬团宠"},
    {"type_id": "年代爱情", "type_name": "🎬年代爱情"},
    {"type_id": "玄幻仙侠", "type_name": "🎬玄幻仙侠"},
    {"type_id": "青梅竹马", "type_name": "🎬青梅竹马"},
    {"type_id": "悬疑推理", "type_name": "🎬悬疑推理"},
    {"type_id": "皇后", "type_name": "🎬皇后"},
    {"type_id": "替身", "type_name": "🎬替身"},
    {"type_id": "大叔", "type_name": "🎬大叔"},
    {"type_id": "喜剧", "type_name": "🎬喜剧"},
    {"type_id": "剧情", "type_name": "🎬剧情"},
]


class Spider(BaseSpider):
    def __init__(self):
        self.name = "红果短剧"
        self.host = "https://api-v2.cenguigui.cn"
        self.api = self.host + "/api/duanju/api.php"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.classes = CLASS_LIST
        self.filters = {
            "分类": [
                {
                    "key": "area",
                    "name": "分类",
                    "value": CLASS_LIST,
                }
            ]
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        return {"list": self._list_items("热播", 1)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        items = self._list_category_items(tid, page)
        return {"page": page, "limit": len(items), "total": page * 30 + len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = str(key or "").strip()
        if not keyword:
            return {"page": page, "limit": 0, "total": 0, "list": []}
        items = self._list_items(keyword, page)
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def detailContent(self, ids):
        result = {"list": []}
        for raw_id in ids:
            vod_id = str(raw_id or "").strip()
            if not vod_id:
                continue
            payload = self._get_json(f"{self.api}?book_id={quote(vod_id)}")
            data = payload.get("data", []) if isinstance(payload, dict) else []
            if not data:
                continue
            episodes = []
            for index, item in enumerate(data, start=1):
                play_id = str(item.get("video_id", "")).strip()
                if not play_id:
                    continue
                episode_name = self._clean_title(
                    str(item.get("title") or item.get("volume_name") or f"第{index}集")
                )
                episodes.append(f"{episode_name}${play_id}")
            tags = payload.get("category_names") or []
            result["list"].append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_title(payload.get("book_name", "")),
                    "vod_pic": str(payload.get("book_pic", "")),
                    "vod_area": ",".join(tags) if isinstance(tags, list) else str(tags or ""),
                    "vod_remarks": str(payload.get("duration", "")).strip() or f"更新至{len(episodes)}集",
                    "vod_year": f"更新时间:{payload.get('time', '')}" if payload.get("time") else "",
                    "vod_actor": str(payload.get("author", "")),
                    "vod_content": str(payload.get("desc", "")),
                    "vod_play_from": "红果短剧",
                    "vod_play_url": "#".join(episodes),
                }
            )
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            payload = self._get_json(
                f"{self.api}?video_id={quote(str(id or '').strip())}"
            )
            return {
                "parse": 0,
                "jx": 0,
                "url": str((payload or {}).get("url", "")).strip(),
                "header": {},
            }
        except Exception:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}

    def _list_items(self, name, page):
        payload = self._get_json(f"{self.api}?name={quote(str(name))}&page={int(page)}")
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return [self._map_vod(item) for item in data]

    def _list_category_items(self, classname, page):
        offset = self._category_offset(page)
        url = (
            f"{self.api}?classname={quote(str(classname))}"
            f"&offset={offset}&showRawParams=false"
        )
        payload = self._get_json(url)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return [self._map_vod(item) for item in data]

    def _category_offset(self, page):
        page_num = max(1, int(page))
        if page_num <= 1:
            return 1
        return (page_num - 1) * 20

    def _map_vod(self, item):
        total = item.get("totalChapterNum")
        remarks = str(item.get("sub_title", "")).strip()
        return {
            "vod_id": str(item.get("book_id") or item.get("id", "")),
            "vod_name": self._clean_title(item.get("title", "")),
            "vod_pic": str(item.get("cover", "")),
            "vod_remarks": remarks or (f"更新至{total}集" if total else ""),
        }

    def _clean_title(self, text):
        value = str(text or "")
        value = re.sub(r"[【\[]热播(?:好剧|短剧)?[】\]]", "", value)
        value = re.sub(r"[【\[]新剧(?:热播)?[】\]]", "", value)
        return re.sub(r"\s+", " ", value).strip()

    def _sort_qualities(self, items):
        priority = {"1080p": 3, "sc": 2, "sd": 1}
        return sorted(
            items or [],
            key=lambda item: priority.get(str(item.get("quality", "")), 0),
            reverse=True,
        )

    def _get_json(self, url):
        response = self.fetch(url, headers=dict(self.headers), timeout=10, verify=False)
        if response.status_code != 200:
            return {}
        try:
            return json.loads(response.text or "{}")
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
