# PPnix Spider Design

## Goal

Implement a new Python spider at `py/PPnix.py` for PPnix based on the provided Node reference, adapted to this repository's existing `Spider` interface and testing conventions.

Scope for this iteration:

- Support two categories: movie and tv
- Expose stable filters only: type/class and sort/by
- Parse homepage recommendations
- Parse category listings
- Parse keyword search
- Parse detail pages and playlist data
- Return direct playback URLs from PPnix m3u8 endpoints

Explicitly out of scope for this iteration:

- Dynamic filter discovery and caching
- TVBox-specific `data:m3u8` rewriting
- Subtitle aggregation in `playerContent`
- JavaScript server route parity with the Node plugin

## Target API Shape

The spider will implement the standard methods used in this repo:

- `homeContent(filter)`
- `homeVideoContent()`
- `categoryContent(tid, pg, filter, extend)`
- `searchContent(key, quick, pg="1")`
- `detailContent(ids)`
- `playerContent(flag, id, vipFlags)`

The spider will follow current repo conventions:

- Single-file site adapter
- Deterministic parsing helpers
- Short site-local IDs rather than full URLs
- No `pagecount` field in list/search responses

## Data Model

### Categories

Use stable repo-style numeric category IDs instead of the Node plugin's string IDs:

- `1` => movie
- `2` => tv

Display names:

- `1` => `电影`
- `2` => `电视剧`

### Filters

Only expose stable filters:

- `class`
- `by`

For both category IDs, `homeContent` will return:

- `class`: values extracted from the Node reference and hard-coded per category
- `by`: `time`, `hits`, `score`

Sort mapping for request URLs:

- `time` => `newstime`
- `hits` => `onclick`
- `score` => `rating`

Default sort:

- `time`

`filter_def` caching is unnecessary because filters are static.

### IDs

To match repository guidance, the spider will keep IDs short.

- List/detail `vod_id`: relative detail path such as `movie/123.html` or `tv/456.html`
- Play IDs: compact encoded payload containing only `infoId` and `param`

Recommended play ID format:

- `infoId|urlencoded(param)`

This is sufficient because the final playback URL is deterministic:

- `https://www.ppnix.com/info/m3u8/{infoId}/{encoded_param}.m3u8`

No referer or display name needs to be stored in the ID for this scope.

## Architecture

`PPnix.py` will keep logic in a single class with focused helpers.

### Core helpers

- `_build_url(path)`
  - Normalizes relative paths against `https://www.ppnix.com`
  - Supports raw absolute URLs and root-relative paths

- `_request_html(path_or_url, referer=None, extra_headers=None)`
  - Performs GET requests through `fetch`
  - Applies browser-like headers
  - Returns response text or empty string on non-200

- `_clean_text(value)`
  - Strips HTML whitespace noise and entities used in visible text

- `_fix_image(url)`
  - Converts relative poster URLs to absolute URLs

### List/category/search helpers

- `_map_type_slug(tid)`
  - `1 -> movie`, `2 -> tv`

- `_build_category_url(tid, pg, extend)`
  - Converts repo category/filter input into PPnix path format
  - First page omits the page index segment
  - Path format:
    - `/cn/{type_slug}/{genre}---{page_index}-{sort}.html`
  - For this scope, unsupported filters are ignored

- `_build_search_url(keyword, pg)`
  - Uses the Node reference pattern:
    - `/cn/search/{encoded_keyword}--.html`
    - page > 1 appends `-page-{pg}`

- `_parse_cards(html, type_hint="")`
  - Parses list cards from homepage/category/search HTML
  - Extracts:
    - `vod_id`
    - `vod_name`
    - `vod_pic`
    - `vod_remarks`
  - Filters out malformed entries
  - Deduplicates by `vod_id`

### Detail/play helpers

- `_extract_m3u8_items(html)`
  - Reads:
    - `infoid = 123`
    - `m3u8 = [...]`
  - Returns `infoId` plus ordered episode/item labels

- `_build_play_id(info_id, param)`
  - Returns compact playback ID

- `_parse_play_id(play_id)`
  - Safely reverses the compact playback ID

- `_parse_detail_page(html, vod_id)`
  - Extracts title, poster, year, director, actor, content
  - Determines `type_name` from `vod_id`
  - Builds a single `PPnix` play group using the extracted m3u8 items

## Request and Parsing Flow

### homeContent

Returns static categories and static filters only.

### homeVideoContent

Requests `/cn/`, parses homepage blocks, merges movie and tv cards, and caps to 20-24 items. The implementation should prefer deterministic extraction over mirroring every homepage section.

### categoryContent

1. Build category URL from `tid`, `pg`, and `extend`
2. Fetch category page
3. Parse cards
4. Filter cards so returned `vod_id` matches the requested type slug
5. Return:
   - `page`
   - `limit`
   - `total`
   - `list`

`total` can follow the repo’s common approximate pattern:

- `page * limit + len(list)`

This is acceptable because the site does not expose a clean total count in the provided reference.

### searchContent

1. Build search URL
2. Parse cards from search result page
3. Keep only IDs matching `movie/<id>.html` or `tv/<id>.html`
4. Return `page`, `limit`, `total`, `list`

### detailContent

1. Normalize incoming ID into a relative detail path
2. Fetch detail page
3. Parse metadata
4. Parse `infoid` and `m3u8` item names from inline JS
5. Build:
   - `vod_play_from = "PPnix"` if episodes exist
   - `vod_play_url = "名称$playId#名称$playId..."`

### playerContent

1. Decode `play_id` into `infoId` and `param`
2. If either is missing, fall back to parse-required response
3. Build direct source URL:
   - `https://www.ppnix.com/info/m3u8/{infoId}/{encoded_param}.m3u8`
4. Return direct-play payload with headers:
   - `Referer: https://www.ppnix.com/cn/`
   - `Origin: https://www.ppnix.com`
   - `User-Agent: browser UA`

No m3u8 text rewriting will be attempted.

## Error Handling

- Request helpers return empty string on non-200 to keep parser code simple
- Parser helpers should tolerate missing nodes and return empty/default fields
- `detailContent` returns `{"list": []}` on fetch/parse failure
- `playerContent` returns parse-required fallback when `play_id` is malformed

This matches the current repo’s defensive style better than raising exceptions.

## Testing Strategy

Tests will be added at `py/tests/test_PPnix.py` using `unittest` and `unittest.mock`.

### Red tests to write first

1. `homeContent` returns categories `1` and `2`, and only stable filter keys
2. `_build_category_url` maps default and selected sort/class values correctly
3. `_parse_cards` extracts short IDs, names, posters, and remarks
4. `homeVideoContent` merges homepage movie/tv sections and truncates result size
5. `categoryContent` requests the expected PPnix listing URL and returns repo-style page payload without `pagecount`
6. `searchContent` requests the expected PPnix search URL and filters valid movie/tv IDs
7. `_extract_m3u8_items` reads `infoid` and ordered item names from inline JS
8. `detailContent` builds metadata and `PPnix` play group from fixture HTML
9. `playerContent` returns direct m3u8 URL for a valid compact play ID
10. `playerContent` falls back to parse-required response when play ID is malformed

### Fixture design

Use embedded HTML snippets rather than live requests. Fixtures should cover:

- Homepage lists
- Category/search cards
- Detail metadata block
- Inline script with `infoid` and `m3u8`

No network access will be used in tests.

## Implementation Notes

- Prefer `BeautifulSoup` because the project already depends on it and many spiders use HTML-string parsing without heavy DOM abstractions
- Keep helper methods small and deterministic so test failures identify one parser responsibility at a time
- Avoid introducing caching or feature flags until they are required by a failing test
