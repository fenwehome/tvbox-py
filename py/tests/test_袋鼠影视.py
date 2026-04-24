import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from requests.exceptions import ConnectionError
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("daishu_spider", str(ROOT / "袋鼠影视.py")).load_module()
Spider = MODULE.Spider


class TestDaishuSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_name(self):
        self.assertEqual(self.spider.getName(), "袋鼠影视")

    def test_home_content_exposes_categories_and_filters(self):
        content = self.spider.homeContent(True)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "2", "3", "4"],
        )
        self.assertIn("filters", content)
        self.assertIn("1", content["filters"])
        self.assertEqual(content["filters"]["1"][0]["key"], "tid")

    def test_home_content_without_filter(self):
        content = self.spider.homeContent(False)
        self.assertNotIn("filters", content)

    def test_build_url(self):
        self.assertEqual(self.spider._build_url("/movie/123.html"), "https://daishuys.com/movie/123.html")
        self.assertEqual(self.spider._build_url("https://other.com/x"), "https://other.com/x")
        self.assertEqual(self.spider._build_url("//cdn.example.com/img.jpg"), "https://cdn.example.com/img.jpg")
        self.assertEqual(self.spider._build_url(""), "")

    def test_encode_and_decode_detail_and_play_ids(self):
        self.assertEqual(self.spider._encode_vod_id("/movie/index123.html"), "movie/index123")
        self.assertEqual(self.spider._decode_vod_id("movie/index123"), "https://daishuys.com/movie/index123.html")
        self.assertEqual(self.spider._encode_play_id("/play/123-1-2.html"), "play/123-1-2")
        self.assertEqual(self.spider._decode_play_id("play/123-1-2"), "https://daishuys.com/play/123-1-2.html")

    def test_clean_text(self):
        self.assertEqual(self.spider._clean_text("  hello   world  "), "hello world")
        self.assertEqual(self.spider._clean_text("\xa0test"), "test")
        self.assertEqual(self.spider._clean_text(None), "")

    def test_build_category_url(self):
        url = self.spider._build_category_url("1", 1, {})
        self.assertIn("searchtype=5", url)
        self.assertIn("tid=1", url)
        self.assertIn("page=1", url)

    def test_build_category_url_with_filters(self):
        url = self.spider._build_category_url("1", 2, {"tid": "5", "area": "大陆", "year": "2024"})
        self.assertIn("tid=5", url)
        self.assertIn("area=", url)
        self.assertIn("year=2024", url)
        self.assertIn("page=2", url)

    def test_parse_category_cards_simple(self):
        html = """
        <div class="hy-video-list">
          <div class="item">
            <a class="videopic" href="/movie/123.html" title="测试影片">
              <img src="/pic.jpg" />
              <span class="note">HD</span>
            </a>
          </div>
        </div>
        """
        items, pagecount = self.spider._parse_category_cards(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["vod_id"], "movie/123")
        self.assertEqual(items[0]["vod_name"], "测试影片")
        self.assertEqual(items[0]["vod_pic"], "https://daishuys.com/pic.jpg")
        self.assertEqual(items[0]["vod_remarks"], "HD")
        self.assertEqual(pagecount, 1)

    def test_parse_category_cards_with_detail(self):
        html = """
        <div class="hy-video-details">
          <div class="item">
            <dl class="content">
              <dt><a class="videopic" href="/movie/456.html"></a></dt>
              <dd>
                <div class="head"><h3>详情影片</h3></div>
                <ul>
                  <li>主演：张三</li>
                  <li>导演：李四</li>
                  <li>地区：大陆</li>
                  <li>年份：2024</li>
                </ul>
              </dd>
            </dl>
          </div>
        </div>
        """
        items, _ = self.spider._parse_category_cards(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["vod_name"], "详情影片")
        self.assertEqual(items[0]["vod_actor"], "张三")
        self.assertEqual(items[0]["vod_director"], "李四")
        self.assertEqual(items[0]["vod_area"], "大陆")
        self.assertEqual(items[0]["vod_year"], "2024")

    def test_parse_page_count(self):
        html = """
        <div class="hy-page">
          <a href="/search.php?page=1">1</a>
          <a href="/search.php?page=5">5</a>
          <a href="/search.php?page=10">10</a>
        </div>
        """
        root = self.spider.html(html)
        self.assertEqual(self.spider._parse_page_count(root), 10)

    def test_parse_detail(self):
        html = """
        <h1 class="h4">详情标题</h1>
        <div class="hy-video-details">
          <div class="content">
            <dt>
              <a class="videopic">
                <img src="/poster.jpg" />
                <span class="note">更新至10集</span>
              </a>
            </dt>
            <li>主演：演员甲 演员乙</li>
            <li>导演：导演甲</li>
            <li>年份：2024</li>
            <li>地区：大陆</li>
            <li>类型：电影</li>
            <li>语言：国语</li>
            <li>又名：Another Name</li>
            <li>豆瓣：8.5</li>
          </div>
        </div>
        <div id="list3"><div class="plot">这是一段剧情简介</div></div>
        <div id="playlist">
          <div class="panel">
            <a class="option" title="线路1"></a>
            <div class="playlist">
              <a href="/play/123-1-1.html" title="第1集">第1集</a>
              <a href="/play/123-1-2.html" title="第2集">第2集</a>
            </div>
          </div>
          <div class="panel">
            <a class="option" title="线路2"></a>
            <div class="playlist">
              <a href="/play/123-2-1.html" title="正片">正片</a>
            </div>
          </div>
        </div>
        """
        result = self.spider._parse_detail(html, "https://daishuys.com/movie/123.html")
        vod = result
        self.assertEqual(vod["vod_name"], "详情标题")
        self.assertEqual(vod["vod_pic"], "https://daishuys.com/poster.jpg")
        self.assertEqual(vod["vod_remarks"], "更新至10集")
        self.assertEqual(vod["vod_actor"], "演员甲 演员乙")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_year"], "2024")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["type_name"], "电影")
        self.assertEqual(vod["vod_lang"], "国语")
        self.assertEqual(vod["vod_content"], "这是一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "线路1$$$线路2")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$play/123-1-1#第2集$play/123-1-2$$$"
            "正片$play/123-2-1",
        )

    @patch.object(Spider, "_request_html")
    def test_detail_content_resolves_relative_id(self, mock_request_html):
        mock_request_html.return_value = "<h1>测试</h1>"
        self.spider.detailContent(["/movie/123.html"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://daishuys.com/movie/123.html")

    @patch.object(Spider, "_request_html")
    def test_detail_content_passes_absolute_url(self, mock_request_html):
        mock_request_html.return_value = "<h1>测试</h1>"
        self.spider.detailContent(["https://daishuys.com/movie/456.html"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://daishuys.com/movie/456.html")

    @patch.object(Spider, "_request_html")
    def test_detail_content_decodes_short_vod_id(self, mock_request_html):
        mock_request_html.return_value = "<h1>测试</h1>"
        self.spider.detailContent(["movie/index456"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://daishuys.com/movie/index456.html")

    def test_extract_play_url_double_quotes(self):
        html = 'var now="https://video.example/stream.m3u8";'
        self.assertEqual(self.spider._extract_play_url(html), "https://video.example/stream.m3u8")

    def test_extract_play_url_single_quotes(self):
        html = "var now='https://video.example/stream.m3u8';"
        self.assertEqual(self.spider._extract_play_url(html), "https://video.example/stream.m3u8")

    def test_extract_play_url_protocol_relative(self):
        html = "var now='//video.example/stream.m3u8';"
        self.assertEqual(self.spider._extract_play_url(html), "https://video.example/stream.m3u8")

    def test_extract_play_url_no_quotes(self):
        html = 'var now=https://video.example/stream.m3u8;'
        self.assertEqual(self.spider._extract_play_url(html), "https://video.example/stream.m3u8")

    def test_extract_play_url_m3u8_fallback(self):
        html = 'some text https://video.example/path/stream.m3u8 other text'
        self.assertEqual(self.spider._extract_play_url(html), "https://video.example/path/stream.m3u8")

    def test_extract_play_url_empty(self):
        self.assertEqual(self.spider._extract_play_url(""), "")
        self.assertEqual(self.spider._extract_play_url("<html></html>"), "")

    @patch.object(Spider, "fetch")
    def test_player_content_extracts_now_var(self, mock_fetch):
        mock_response = type("R", (), {"status_code": 200, "text": 'var now="https://video.example/stream.m3u8";'})()
        mock_fetch.return_value = mock_response
        result = self.spider.playerContent("", "play/123-1-1", [])
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["playUrl"], "")
        self.assertEqual(result["url"], "https://video.example/stream.m3u8")
        self.assertIn("Referer", result["header"])
        self.assertEqual(result["header"]["Referer"], "https://daishuys.com/play/123-1-1.html")
        self.assertEqual(mock_fetch.call_args.args[0], "https://daishuys.com/play/123-1-1.html")

    @patch.object(Spider, "fetch")
    def test_player_content_falls_back_to_parse(self, mock_fetch):
        mock_response = type("R", (), {"status_code": 200, "text": "<html>no video</html>"})()
        mock_fetch.return_value = mock_response
        result = self.spider.playerContent("", "play/123-1-1", [])
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["playUrl"], "")
        self.assertEqual(result["header"]["Referer"], "https://daishuys.com/play/123-1-1.html")
        self.assertEqual(result["url"], "https://daishuys.com/play/123-1-1.html")

    @patch.object(Spider, "fetch")
    def test_player_content_handles_non_200(self, mock_fetch):
        mock_response = type("R", (), {"status_code": 403, "text": ""})()
        mock_fetch.return_value = mock_response
        result = self.spider.playerContent("", "play/123-1-1", [])
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["playUrl"], "")

    @patch.object(Spider, "_curl_request")
    @patch.object(Spider, "fetch")
    def test_player_content_falls_back_to_curl_request_on_fetch_error(self, mock_fetch, mock_curl_request):
        mock_fetch.side_effect = ConnectionError("dns failed")
        mock_curl_request.return_value = {"body": 'var now="https://video.example/fallback.m3u8";', "status_code": 200}
        result = self.spider.playerContent("", "play/123-1-1", [])
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/fallback.m3u8")

    def test_player_content_empty_id(self):
        result = self.spider.playerContent("", "", [])
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["url"], "")

    @patch.object(Spider, "_request_html")
    def test_category_content(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="hy-video-list">
          <div class="item">
            <a class="videopic" href="/movie/789.html" title="分类片">
              <img src="/cat.jpg" />
              <span class="note">TC</span>
            </a>
          </div>
        </div>
        <div class="hy-page">
          <a href="/search.php?page=5">5</a>
        </div>
        """
        result = self.spider.categoryContent("1", "2", True, {})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["pagecount"], 5)
        self.assertEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["vod_name"], "分类片")


if __name__ == "__main__":
    unittest.main()
