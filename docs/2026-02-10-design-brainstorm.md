# 设计文档补充 - 头脑风暴与细节完善

> 基于 2026-02-07 设计文档的深度审查，结合对目标网站的实际调研和行业最佳实践。
> 补充于 2026-02-10

---

## 0. 核心发现摘要（必读）

经过对 7 个目标网站的逐一调研，发现**原设计文档存在几个根本性问题**：

| # | 问题 | 严重度 | 影响 |
|---|------|--------|------|
| 1 | 大多数网站有公开 API/RSS，根本不需要 HTML 爬取 | **致命** | 架构方向错误，80% 的反爬代码无用 |
| 2 | 关键词匹配逻辑有 bug：要求同时包含所有关键词 | **致命** | 几乎匹配不到任何岗位 |
| 3 | 去重策略过于简单，无法处理跨站重复 | **重要** | 数据质量差 |
| 4 | 缺少异步架构，7 个站串行爬取太慢 | **重要** | 用户体验差 |
| 5 | 缺少通知系统、部署方案、监控告警 | **重要** | 无法生产使用 |

---

## 1. 【致命】网站策略全部需要修正

### 1.1 调研结果：各网站真实技术特征

| 网站 | 爬取难度 | 最佳方式 | 原设计方案 | 是否需要登录 |
|------|----------|----------|-----------|-------------|
| **RemoteOK** | ⭐ 最简单 | **公开 API** `/api` 返回 JSON | ~~Playwright~~ | 否 |
| **电鸭社区** | ⭐ 简单 | **公开 API** `svc.eleduck.com/api/v1/posts?category=5` | ~~requests+BS4+登录~~ | **否（API 无需登录）** |
| **WeWorkRemotely** | ⭐ 简单 | **RSS 订阅** `*.rss` | requests+BS4（可行但多余） | 否 |
| **V2EX** | ⭐⭐ 中等 | **混合**：HTML 列表页 + API 详情 | requests+BS4（部分正确） | 否（只读 API 无需认证） |
| **远程.work** | ⭐⭐ 中等 | **HTML 爬取**（WordPress 站） | requests+BS4 ✅ | 否 |
| **Arc.dev** | ⭐⭐⭐ 最难 | **Playwright**（Next.js SPA） | Playwright ✅ | 否 |
| **OfferShow** | ❓ 待确认 | 需进一步调研 | 待定 | 待定 |

### 1.2 各网站具体 API/数据源

#### RemoteOK — 直接调 API，零反爬

```
GET https://remoteok.com/api
返回: JSON 数组，包含所有岗位
robots.txt: Crawl-delay: 1（仅 1 秒）
```

**建议**: 完全移除 Playwright 方案，直接 `httpx.get("https://remoteok.com/api")` 即可。

#### 电鸭社区 — 直接调 API，无需登录

```
GET https://svc.eleduck.com/api/v1/posts?category=5&page=1
返回: { "posts": [ { "id", "title", "summary", "user", "tags", "published_at" } ] }
详情: GET https://svc.eleduck.com/api/v1/posts/{id}
分类 ID: 5 = 招聘
robots.txt: 仅 Disallow /profile/*
```

**建议**: 完全移除 Cookie/登录逻辑，直接调 API。原设计中的 "需要登录" 是错误的。

#### WeWorkRemotely — RSS 订阅

```
https://weworkremotely.com/categories/remote-programming-jobs.rss
https://weworkremotely.com/categories/remote-data-science-jobs.rss
robots.txt: 几乎无限制
```

**建议**: 用 `feedparser` 库解析 RSS，比 HTML 爬取简单 10 倍。

#### V2EX — 混合方案

```
列表页: https://www.v2ex.com/go/jobs?p=1（需 HTML 解析获取 topic ID）
详情 API: https://www.v2ex.com/api/topics/show.json?id={topic_id}
robots.txt: bingbot Crawl-delay 120s，其他无限制
```

**建议**: 先爬列表页提取 ID，再批量调 API 获取详情。不需要登录。

#### 远程.work — WordPress HTML 爬取

```
分类页: /remote-development-jobs, /remote-design-jobs 等
结构: div.list-group > div.job > a.job-title
robots.txt: 仅 Disallow wp-admin
```

**建议**: 保持 requests+BS4 方案，注意 WordPress 分页规律。

#### Arc.dev — Next.js SPA 需 Playwright

```
页面: https://arc.dev/remote-jobs
技术栈: Next.js（_next/image URL 可见）
robots.txt: 极少限制
```

**建议**: 唯一真正需要 Playwright 的站点。使用 `playwright-stealth` 增强隐匿性。

### 1.3 修正后的架构分层

```
数据源适配器（替代原来统一的 BaseScraper）
├── ApiAdapter        — RemoteOK, 电鸭（直接调 JSON API）
├── RssAdapter        — WeWorkRemotely（解析 RSS/Atom）
├── HybridAdapter     — V2EX（HTML 列表 + API 详情）
├── HtmlAdapter       — 远程.work（传统 HTML 爬取）
└── BrowserAdapter    — Arc.dev（Playwright 渲染）
```

每种适配器需要的反爬策略完全不同：

| 适配器 | UA轮换 | 延迟 | Cookie | 代理 | 行为模拟 |
|--------|--------|------|--------|------|----------|
| ApiAdapter | ✅ 基础即可 | ✅ 1-2s | ❌ | ❌ | ❌ |
| RssAdapter | ❌ | ✅ 1s | ❌ | ❌ | ❌ |
| HybridAdapter | ✅ | ✅ 2-3s | ❌ | ❌ | ❌ |
| HtmlAdapter | ✅ | ✅ 2-5s | 可选 | 可选 | ❌ |
| BrowserAdapter | ✅ stealth | ✅ 3-8s | ✅ | 可选 | ✅ |

---

## 2. 【致命】关键词匹配逻辑重设计

### 2.1 问题分析

当前逻辑要求**同时包含所有关键词**：

```python
keywords = ["remote", "远程工作", "AI agent", "AI应用开发"]
# 一篇文章必须同时包含 "remote" 和 "远程工作" 和 "AI agent" 和 "AI应用开发"
# 现实中：中文站不会写 "remote"，英文站不会写 "远程工作"
# 结果：几乎 0 命中
```

### 2.2 修正方案：关键词分组 + OR/AND 组合

```yaml
# keywords.yaml — 修正版
keyword_groups:
  # 地点组：任意命中一个即可（内部 OR）
  location:
    - "remote"
    - "远程"
    - "远程工作"
    - "远程办公"
    - "在家办公"
    - "work from home"
    - "wfh"
    - "fully remote"
    - "location independent"

  # 技术组：任意命中一个即可（内部 OR）
  technology:
    - "AI"
    - "artificial intelligence"
    - "AI agent"
    - "AI 应用"
    - "AI应用开发"
    - "LLM"
    - "大模型"
    - "大语言模型"
    - "机器学习"
    - "machine learning"
    - "deep learning"
    - "深度学习"
    - "NLP"
    - "自然语言处理"
    - "GPT"
    - "Claude"
    - "RAG"
    - "langchain"
    - "prompt engineer"

# 组间逻辑：AND（必须同时满足地点+技术）
# 特殊规则：某些源站本身就是远程岗位平台（RemoteOK, WWR, 远程.work），
#           可以跳过 location 组匹配，只匹配 technology 组
match_rules:
  default: "location AND technology"
  skip_location_for:
    - "remoteok"       # 全站都是远程岗位
    - "weworkremotely"  # 全站都是远程岗位
    - "yuancheng"       # 全站都是远程岗位
```

### 2.3 修正后的匹配器

```python
class KeywordMatcher:
    def __init__(self, config):
        self.groups = config['keyword_groups']
        self.skip_location = config['match_rules'].get('skip_location_for', [])

    def match_group(self, text: str, group_name: str) -> bool:
        """组内 OR 匹配：任意一个关键词命中即可"""
        text_lower = text.lower()
        for keyword in self.groups.get(group_name, []):
            if keyword.lower() in text_lower:
                return True
        return False

    def match_job(self, job: dict, source: str) -> bool:
        """组间 AND 匹配"""
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('tags', '')}"

        # 技术组必须命中
        if not self.match_group(text, 'technology'):
            return False

        # 某些全远程平台跳过地点匹配
        if source in self.skip_location:
            return True

        # 其他平台需要地点+技术都命中
        return self.match_group(text, 'location')
```

### 2.4 额外考虑

- **模糊匹配**: "AI应用" 应该能匹配 "AI 应用"（中文空格问题），建议预处理时去除中文间空格
- **词边界**: "AI" 不应误匹配 "email"、"wait" 等，需要做词边界检查（英文用 `\bAI\b` 正则）
- **否定词过滤**: 排除明显不相关的匹配，如 "AI-powered HR tool"（是 HR 岗不是 AI 岗）
- **匹配分数**: 不只是 True/False，给出匹配分数（命中越多关键词分越高），方便排序

---

## 3. 【重要】数据去重策略增强

### 3.1 当前问题

`MD5(url + title)` 只能处理完全相同的岗位。现实中：
- 同一公司在 RemoteOK 和 电鸭 同时发布（不同 URL）
- 标题略有差异："Senior AI Engineer" vs "Sr. AI Engineer" vs "高级AI工程师"

### 3.2 多层去重方案

```python
class DeduplicationManager:
    """三层去重策略"""

    def layer1_exact(self, job: dict) -> str:
        """第一层：精确去重 — 同 URL"""
        return hashlib.md5(job['url'].lower().encode()).hexdigest()

    def layer2_same_site(self, job: dict) -> str:
        """第二层：同站去重 — 同来源+标题标准化"""
        normalized_title = self._normalize_title(job['title'])
        content = f"{job['source']}|{normalized_title}"
        return hashlib.md5(content.encode()).hexdigest()

    def layer3_cross_site(self, job: dict, existing_jobs: list) -> Optional[str]:
        """第三层：跨站去重 — 公司名+标题相似度"""
        for existing in existing_jobs:
            # 公司名必须匹配（模糊）
            if not self._company_similar(job.get('company', ''), existing.get('company', '')):
                continue
            # 标题相似度 > 85%
            title_sim = SequenceMatcher(None,
                self._normalize_title(job['title']),
                self._normalize_title(existing['title'])
            ).ratio()
            if title_sim > 0.85:
                return existing['id']  # 返回已存在岗位的 ID
        return None

    def _normalize_title(self, title: str) -> str:
        """标题标准化"""
        title = title.lower().strip()
        # Sr. -> Senior, Jr. -> Junior 等
        replacements = {
            'sr.': 'senior', 'sr ': 'senior ',
            'jr.': 'junior', 'jr ': 'junior ',
            'eng.': 'engineer', 'dev ': 'developer ',
        }
        for old, new in replacements.items():
            title = title.replace(old, new)
        return title

    def _company_similar(self, a: str, b: str) -> bool:
        """公司名模糊匹配"""
        if not a or not b:
            return False
        return SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.8
```

### 3.3 数据结构增强

```python
{
    # === 原有字段 ===
    "id": "hash...",
    "title": "职位标题",
    "company": "公司名称",
    "url": "岗位链接",
    "source": "来源网站",
    # ...

    # === 新增字段 ===
    "source_urls": [                   # 跨站聚合：所有来源的 URL
        {"source": "remoteok", "url": "https://..."},
        {"source": "eleduck", "url": "https://..."}
    ],
    "normalized_title": "senior ai engineer",  # 标准化标题（用于去重）
    "match_score": 0.85,              # 关键词匹配分数
    "matched_keywords": ["AI", "remote"],  # 命中的关键词列表
    "is_active": true,                # 岗位是否仍然活跃
    "last_seen": "2026-02-10T...",    # 最后一次爬到此岗位的时间
    "stale_days": 0,                  # 距离上次爬到的天数
    "raw_data": {}                    # 原始数据保留（便于调试）
}
```

---

## 4. 【重要】异步架构设计

### 4.1 问题

7 个站串行爬取，每站 2-5 秒延迟 + 多页分页 = 总耗时可能 5-10 分钟。

### 4.2 方案：asyncio + httpx

```python
import asyncio
import httpx
from typing import List, Dict

class ScraperOrchestrator:
    """异步编排器：并行爬取所有站点"""

    def __init__(self, config):
        self.adapters = self._create_adapters(config)
        self.storage = StorageManager()
        self.matcher = KeywordMatcher(config)

    async def run_all(self):
        """并行执行所有站点爬取"""
        async with httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            http2=True  # 启用 HTTP/2
        ) as client:
            tasks = [
                self._run_adapter(adapter, client)
                for adapter in self.adapters
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        total_jobs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"{self.adapters[i].name} 失败: {result}")
            else:
                total_jobs.extend(result)

        # 过滤 + 去重 + 存储
        matched = [j for j in total_jobs if self.matcher.match_job(j, j['source'])]
        self.storage.merge_all(matched)
        self.storage.save()

        return {
            "total_scraped": len(total_jobs),
            "matched": len(matched),
            "new": self.storage.new_count,
            "updated": self.storage.updated_count
        }

    async def _run_adapter(self, adapter, client):
        """单个适配器执行（含熔断）"""
        try:
            return await adapter.fetch_jobs(client)
        except CircuitBreakerOpenError:
            logger.warning(f"{adapter.name}: 熔断器开启，跳过")
            return []
```

### 4.3 Playwright 异步集成

```python
class BrowserAdapter:
    """Arc.dev 等需要浏览器的站点"""

    async def fetch_jobs(self, http_client):
        """Playwright 也有 async API"""
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth

        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            page = await context.new_page()

            await page.goto(self.url, wait_until='networkidle')
            # ... 解析逻辑
            await browser.close()
```

---

## 5. 【重要】技术栈升级建议

### 5.1 HTTP 客户端：httpx 替代 requests

| 特性 | requests | httpx |
|------|----------|-------|
| 异步支持 | ❌ 需 aiohttp | ✅ 原生 async |
| HTTP/2 | ❌ | ✅ |
| 连接池 | 手动 Session | ✅ 内置 Limits |
| 超时控制 | 粗粒度 | ✅ 分离 connect/read/write/pool |
| 类型注解 | ❌ | ✅ 100% 类型覆盖 |
| API 兼容 | 原版 | ✅ 几乎 100% 兼容 requests |

```python
# 迁移成本极低
# requests:
response = requests.get(url, headers=headers, timeout=10)

# httpx（同步模式，drop-in 替换）:
response = httpx.get(url, headers=headers, timeout=10)

# httpx（异步模式）:
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers, timeout=10)
```

### 5.2 日志：loguru 替代 logging

```python
from loguru import logger

# 一行配置替代 20 行 logging 样板
logger.add(
    "logs/scraper_{time:YYYY-MM-DD}.log",
    rotation="1 day",         # 每日轮转
    retention="30 days",      # 保留 30 天
    compression="zip",        # 自动压缩
    serialize=True,           # JSON 格式（便于分析）
    encoding="utf-8",
    level="DEBUG"
)

# 使用方式完全一样
logger.info("爬取完成", site="remoteok", jobs_found=42)
logger.warning("触发频率限制", site="v2ex", retry_after=60)
```

### 5.3 新增依赖建议

```txt
# === 核心（替换） ===
httpx[http2]>=0.27.0          # 替代 requests
beautifulsoup4>=4.12.0        # 保留
playwright>=1.40.0            # 保留
playwright-stealth>=1.0.0     # 新增：反检测

# === 数据源 ===
feedparser>=6.0.0             # 新增：RSS 解析（WeWorkRemotely）

# === 工具 ===
loguru>=0.7.0                 # 替代 logging
pyyaml>=6.0.1                 # 保留
pydantic>=2.0                 # 新增：数据校验与序列化

# === 反爬（按需） ===
fake-useragent>=1.4.0         # 保留
cloudscraper>=1.2.71          # 新增：Cloudflare 绕过（如需）

# === 调度 ===
APScheduler>=3.10.4           # 保留

# === 通知（可选） ===
python-telegram-bot>=21.0     # 新增
# 或者直接用 httpx 调 webhook，不需要额外库

# === 测试 ===
pytest>=8.0                   # 新增
pytest-asyncio>=0.23          # 新增：异步测试
```

---

## 6. 【重要】熔断器（Circuit Breaker）

### 6.1 为什么需要

没有熔断器时：某站宕机 → 爬虫持续重试 → 消耗时间 + 可能被误判为攻击。

### 6.2 实现

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"        # 正常运行
    OPEN = "open"            # 熔断中，不发请求
    HALF_OPEN = "half_open"  # 试探性恢复

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=900):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # 15 分钟
        self.last_failure_time = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN: 允许一次试探
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"熔断器开启，暂停 {self.recovery_timeout}s")
```

每个站点独立拥有一个 CircuitBreaker 实例。

---

## 7. 【重要】通知系统设计

### 7.1 统一通知接口

```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    async def send(self, title: str, body: str, level: str = "info"):
        """发送通知"""
        pass

class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str):
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id

    async def send(self, title: str, body: str, level: str = "info"):
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "success": "✅"}
        text = f"{emoji.get(level, '')} *{title}*\n{body}"
        async with httpx.AsyncClient() as client:
            await client.post(self.api_url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            })

class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, title: str, body: str, level: str = "info"):
        color = {"info": 3447003, "warning": 16776960, "error": 15158332, "success": 3066993}
        async with httpx.AsyncClient() as client:
            await client.post(self.webhook_url, json={
                "embeds": [{
                    "title": title,
                    "description": body,
                    "color": color.get(level, 3447003)
                }]
            })

class ServerChanNotifier(Notifier):
    """Server酱 — 国内开发者常用"""
    def __init__(self, send_key: str):
        self.api_url = f"https://sctapi.ftqq.com/{send_key}.send"

    async def send(self, title: str, body: str, level: str = "info"):
        async with httpx.AsyncClient() as client:
            await client.post(self.api_url, data={
                "title": title,
                "desp": body
            })

class CompositeNotifier(Notifier):
    """组合通知器：同时发送到多个渠道"""
    def __init__(self, notifiers: list[Notifier]):
        self.notifiers = notifiers

    async def send(self, title: str, body: str, level: str = "info"):
        await asyncio.gather(*[n.send(title, body, level) for n in self.notifiers])
```

### 7.2 通知触发场景

```yaml
# notifications.yaml
notifications:
  on_complete:
    enabled: true
    template: "爬取完成：共 {total} 条，新增 {new} 条，更新 {updated} 条"

  on_new_jobs:
    enabled: true
    min_count: 1  # 至少有 1 条新岗位才通知
    template: "发现 {count} 条新岗位！\n{job_list}"

  on_error:
    enabled: true
    template: "爬取出错：{site} - {error}"

  on_circuit_break:
    enabled: true
    template: "⚠️ {site} 熔断器触发，暂停 {timeout}s"

  on_site_structure_change:
    enabled: true
    template: "🚨 {site} 页面结构可能发生变化，请检查选择器"
```

---

## 8. 【重要】站点结构变更检测

如果目标网站改版，CSS 选择器失效，爬虫会静默返回空结果。需要主动检测。

```python
class StructureMonitor:
    """检测目标网站 HTML 结构是否变化"""

    def __init__(self, hash_file="data/structure_hashes.json"):
        self.hash_file = hash_file
        self.hashes = self._load_hashes()

    def check(self, site_name: str, html: str, selectors: dict) -> list[str]:
        """
        返回失效的选择器列表。
        selectors: {"job_list": "div.job-item", "title": "h2.job-title", ...}
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        broken = []

        for name, selector in selectors.items():
            elements = soup.select(selector)
            if not elements:
                broken.append(name)

        # 同时检测整体 DOM 结构哈希
        structure = ' '.join(tag.name for tag in soup.find_all()[:100])
        new_hash = hashlib.md5(structure.encode()).hexdigest()
        old_hash = self.hashes.get(site_name)

        if old_hash and new_hash != old_hash:
            logger.warning(f"{site_name} DOM 结构变化！旧={old_hash[:8]} 新={new_hash[:8]}")
        self.hashes[site_name] = new_hash
        self._save_hashes()

        return broken
```

---

## 9. 【重要】数据存储升级

### 9.1 JSON → SQLite

JSON 文件在数据量大时（1000+ 条）有明显问题：
- 每次保存需要全量写入
- 无法高效查询/过滤
- 并发写入不安全

```python
import sqlite3
from contextlib import contextmanager

class SQLiteStorage:
    def __init__(self, db_path="data/jobs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    normalized_title TEXT,
                    company TEXT,
                    url TEXT UNIQUE,
                    source TEXT NOT NULL,
                    published_at TEXT,
                    salary TEXT,
                    location TEXT,
                    description TEXT,
                    requirements TEXT,
                    tags TEXT,  -- JSON array
                    apply_method TEXT,
                    match_score REAL,
                    matched_keywords TEXT,  -- JSON array
                    is_active BOOLEAN DEFAULT 1,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    update_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 索引加速查询
            conn.execute('CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_is_active ON jobs(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen)')

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_job(self, job: dict):
        with self._connect() as conn:
            conn.execute('''
                INSERT INTO jobs (id, title, url, source, first_seen, last_seen, last_updated)
                VALUES (:id, :title, :url, :source, :now, :now, :now)
                ON CONFLICT(id) DO UPDATE SET
                    title = :title,
                    last_seen = :now,
                    last_updated = :now,
                    update_count = update_count + 1
            ''', {**job, 'now': datetime.now().isoformat()})

    def export_json(self, filepath="data/jobs.json"):
        """保留 JSON 导出能力"""
        with self._connect() as conn:
            jobs = conn.execute('SELECT * FROM jobs WHERE is_active = 1').fetchall()
            # ... 导出为 JSON

    def export_csv(self, filepath="data/jobs.csv"):
        """CSV 导出"""
        # ...

    def mark_stale(self, days=30):
        """标记超过 N 天未见的岗位为不活跃"""
        with self._connect() as conn:
            conn.execute('''
                UPDATE jobs SET is_active = 0
                WHERE julianday('now') - julianday(last_seen) > ?
            ''', (days,))
```

### 9.2 保留 JSON 导出

SQLite 为主存储，但仍支持 `--export json` / `--export csv` 导出。

---

## 10. 部署方案

### 10.1 Docker 部署

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖（Playwright 需要）
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .

# 数据持久化
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "main.py", "--schedule"]
```

```yaml
# docker-compose.yml
services:
  scraper:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    env_file: .env
    restart: unless-stopped
```

### 10.2 健康检查

```python
# 简单的文件级健康检查（无需 web 框架）
import json, time

def write_health_status(status: dict):
    status['timestamp'] = time.time()
    with open('data/health.json', 'w') as f:
        json.dump(status, f)

# Docker HEALTHCHECK 检查此文件的时间戳是否在 1 小时内
```

---

## 11. 配置文件增强

### 11.1 sites.yaml 修正版

```yaml
sites:
  remoteok:
    name: "RemoteOK"
    adapter: "api"                    # api / rss / html / hybrid / browser
    url: "https://remoteok.com/api"
    delay: [1, 2]
    skip_location_match: true         # 全远程平台
    pagination:
      type: "none"                    # 单次返回所有数据
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 900

  eleduck:
    name: "电鸭社区"
    adapter: "api"
    url: "https://svc.eleduck.com/api/v1/posts"
    params:
      category: 5                     # 5 = 招聘
    delay: [1, 3]
    pagination:
      type: "page_param"
      param_name: "page"
      max_pages: 5

  weworkremotely:
    name: "We Work Remotely"
    adapter: "rss"
    feeds:
      - "https://weworkremotely.com/categories/remote-programming-jobs.rss"
      - "https://weworkremotely.com/categories/remote-data-science-jobs.rss"
    skip_location_match: true

  v2ex:
    name: "V2EX"
    adapter: "hybrid"
    list_url: "https://www.v2ex.com/go/jobs"
    detail_api: "https://www.v2ex.com/api/topics/show.json"
    delay: [2, 4]
    pagination:
      type: "page_param"
      param_name: "p"
      max_pages: 3

  yuancheng:
    name: "远程.work"
    adapter: "html"
    url: "https://yuancheng.work"
    categories:
      - "/remote-development-jobs"
      - "/remote-design-jobs"
      - "/remote-product-jobs"
    delay: [2, 5]
    skip_location_match: true
    selectors:
      job_list: "div.list-group div.job"
      title: "a.job-title"
      meta: "div.job-meta span.job-meta-value"

  arc:
    name: "Arc.dev"
    adapter: "browser"
    url: "https://arc.dev/remote-jobs"
    delay: [3, 8]
    wait_for: "networkidle"
    use_stealth: true
    selectors:
      # 需要实际调研确认
      job_list: "TBD"
      title: "TBD"

  offershow:
    name: "OfferShow"
    adapter: "TBD"                    # 需进一步调研
    url: "https://offershow.com"
    enabled: false                    # 暂时禁用，待调研
```

---

## 12. 数据校验（Pydantic）

使用 Pydantic 替代字典，保证数据一致性：

```python
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
from datetime import datetime

class JobPosting(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    url: HttpUrl
    source: str
    published_at: Optional[datetime] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    tags: list[str] = []
    apply_method: Optional[str] = None
    match_score: float = 0.0
    matched_keywords: list[str] = []
    is_active: bool = True
    first_seen: datetime
    last_seen: datetime
    last_updated: datetime
    update_count: int = 1

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError('标题不能为空')
        return v.strip()

    @field_validator('source')
    @classmethod
    def valid_source(cls, v):
        valid = {'remoteok', 'eleduck', 'weworkremotely', 'v2ex', 'yuancheng', 'arc', 'offershow'}
        if v not in valid:
            raise ValueError(f'未知来源: {v}')
        return v
```

---

## 13. 修正后的目录结构

```
job-scraper/
├── scraper/
│   ├── __init__.py
│   ├── orchestrator.py      # 异步编排器（替代原 main 里的串行逻辑）
│   ├── models.py            # Pydantic 数据模型
│   ├── adapters/            # 替代原 strategies/（名称更准确）
│   │   ├── __init__.py
│   │   ├── base.py          # 适配器基类
│   │   ├── api.py           # ApiAdapter（RemoteOK, 电鸭）
│   │   ├── rss.py           # RssAdapter（WWR）
│   │   ├── hybrid.py        # HybridAdapter（V2EX）
│   │   ├── html.py          # HtmlAdapter（远程.work）
│   │   └── browser.py       # BrowserAdapter（Arc.dev）
│   └── utils/
│       ├── __init__.py
│       ├── anti_crawl.py    # 反爬策略（精简版，大部分站不需要）
│       ├── circuit_breaker.py  # 新增：熔断器
│       ├── matcher.py       # 关键词匹配（重写）
│       ├── dedup.py         # 新增：多层去重
│       ├── storage.py       # SQLite 存储
│       ├── notifier.py      # 新增：通知系统
│       └── monitor.py       # 新增：结构变更检测
├── config/
│   ├── __init__.py
│   ├── sites.yaml           # 网站配置（重写）
│   ├── keywords.yaml        # 关键词配置（重写，分组）
│   └── notifications.yaml   # 新增：通知配置
├── data/                    # gitignore
│   ├── jobs.db              # SQLite 主存储（替代 jobs.json）
│   ├── structure_hashes.json
│   └── exports/             # 导出目录
│       ├── jobs.json
│       └── jobs.csv
├── logs/                    # gitignore
├── tests/                   # 新增
│   ├── test_matcher.py
│   ├── test_dedup.py
│   ├── test_storage.py
│   └── test_adapters/
│       ├── test_api_adapter.py
│       └── ...
├── main.py                  # CLI 入口
├── Dockerfile               # 新增
├── docker-compose.yml       # 新增
├── pyproject.toml           # 替代 requirements.txt
├── README.md
└── .env.example             # 新增：环境变量模板
```

---

## 14. 修正后的命令行

```python
# main.py
import argparse
import asyncio

def main():
    parser = argparse.ArgumentParser(description='远程AI岗位爬虫')
    subparsers = parser.add_subparsers(dest='command')

    # 爬取
    scrape = subparsers.add_parser('scrape', help='执行爬取')
    scrape.add_argument('--site', help='指定网站（不指定则全部）')
    scrape.add_argument('--dry-run', action='store_true', help='试运行（不保存）')
    scrape.add_argument('--verbose', action='store_true')

    # 导出
    export = subparsers.add_parser('export', help='导出数据')
    export.add_argument('--format', choices=['json', 'csv'], default='json')
    export.add_argument('--output', default='data/exports/')
    export.add_argument('--active-only', action='store_true', default=True)

    # 定时任务
    schedule = subparsers.add_parser('schedule', help='启动定时任务')
    schedule.add_argument('--cron', default='0 9 * * *', help='Cron 表达式')

    # 统计
    stats = subparsers.add_parser('stats', help='查看统计')

    args = parser.parse_args()

    if args.command == 'scrape':
        asyncio.run(run_scrape(args))
    elif args.command == 'export':
        run_export(args)
    elif args.command == 'schedule':
        run_scheduler(args)
    elif args.command == 'stats':
        show_stats()
```

**使用示例**:
```bash
# 爬取所有站点
python main.py scrape --verbose

# 只爬 RemoteOK
python main.py scrape --site remoteok

# 导出 CSV
python main.py export --format csv

# 启动每日 9 点定时
python main.py schedule --cron "0 9 * * *"

# 查看统计
python main.py stats
```

---

## 15. 修正后的实施优先级

### Phase 1: MVP（能跑起来）
1. 项目骨架 + pyproject.toml + 基础配置
2. Pydantic 数据模型
3. 关键词分组匹配器（修正版）
4. SQLite 存储 + 基础去重
5. **ApiAdapter** 实现（RemoteOK + 电鸭）— 两个 API 站最简单
6. **RssAdapter** 实现（WeWorkRemotely）
7. CLI 入口（scrape 命令）
8. 基础日志（loguru）

> MVP 产出：能从 3 个站获取数据，匹配关键词，存入 SQLite。无需任何反爬。

### Phase 2: 完善数据源
1. **HybridAdapter**（V2EX）
2. **HtmlAdapter**（远程.work）
3. **BrowserAdapter** + playwright-stealth（Arc.dev）
4. 异步编排器（asyncio 并行爬取）
5. 多层去重（跨站去重）
6. 分页支持
7. OfferShow 调研与实现

### Phase 3: 生产化
1. 熔断器
2. 通知系统（Telegram / Discord / Server酱）
3. 站点结构变更检测
4. 定时任务模式
5. Docker 部署
6. JSON/CSV 导出
7. 健康检查

### Phase 4: 增强
1. 匹配分数排序
2. 岗位过期/下架检测
3. Notion / Google Sheets 集成
4. 统计报表（stats 命令）
5. 测试覆盖
6. 文档

---

## 16. 其他遗漏补充

### 16.1 岗位生命周期管理

```
新岗位被爬到 → is_active=True, first_seen=now
每次爬到 → last_seen=now, update_count++
连续 N 天未爬到 → is_active=False（可能已下架）
用户可手动标记已申请/已忽略
```

### 16.2 robots.txt 合规

调研结果汇总：

| 网站 | robots.txt 限制 | 建议 |
|------|-----------------|------|
| RemoteOK | Crawl-delay: 1, 屏蔽 SEO bot | 遵守 1s 延迟 |
| 电鸭 | 仅 Disallow /profile/* | 安全 |
| WWR | 仅 Disallow /admin/ | 安全 |
| V2EX | bingbot Crawl-delay 120s | 用普通 UA，遵守基本延迟 |
| 远程.work | 仅 Disallow wp-admin | 安全 |
| Arc.dev | 极少限制 | 安全 |

**结论**: 所有目标网站的 robots.txt 对正常爬虫都很友好。核心约束是延迟而非禁止。

### 16.3 数据隐私

- 爬取的是**公开招聘信息**，不涉及个人隐私数据
- 不爬取求职者简历、联系方式等 PII
- 建议在 User-Agent 中注明爬虫身份和联系方式：`JobScraper/1.0 (+https://github.com/xxx; contact@xxx.com)`

### 16.4 错误恢复与幂等性

- 每次爬取应该是幂等的：重复运行不会产生重复数据
- `Ctrl+C` 优雅退出：注册 signal handler，保存已爬取数据后退出
- 使用 SQLite 事务保证数据一致性

### 16.5 性能估算

| 网站 | 数据获取方式 | 预计耗时（异步） |
|------|-------------|-----------------|
| RemoteOK | 1 次 API 调用 | ~2s |
| 电鸭 | 5 页 API 调用 | ~10s |
| WWR | 2 个 RSS 订阅 | ~3s |
| V2EX | 3 页 HTML + N 次 API | ~15s |
| 远程.work | 6 个分类页 HTML | ~20s |
| Arc.dev | Playwright 渲染 | ~30s |
| **总计（并行）** | — | **~30-40s**（受最慢的 Playwright 站限制） |

对比原方案串行：可能需要 5-10 分钟。异步并行提速 **10 倍以上**。

---

*补充完成于 2026-02-10*
