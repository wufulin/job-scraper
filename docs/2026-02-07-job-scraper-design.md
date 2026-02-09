# 远程AI岗位爬虫系统 - 设计文档

## 1. 项目概述

### 1.1 产品定位
一个智能化的 Python 爬虫系统，用于从多个招聘网站爬取符合关键词的远程AI岗位信息，支持命令行和定时任务两种运行模式。

### 1.2 技术栈
- **语言**: Python 3.8+
- **核心库**: 
  - `requests` + `BeautifulSoup4` - 静态页面爬取
  - `playwright` - 动态页面和浏览器自动化
  - `fake-useragent` - 随机 User-Agent
  - `schedule` / `APScheduler` - 定时任务
- **数据处理**: `json` (标准库)
- **日志**: `logging` (标准库)

### 1.3 目标网站
1. 电鸭社区 - https://eleduck.com
2. V2EX - https://v2ex.com/go/jobs
3. RemoteOK - https://remoteok.com
4. We Work Remotely - https://weworkremotely.com
5. Arc.dev - https://arc.dev
6. OfferShow - https://offershow.com
7. 远程.work - https://yuancheng.work

### 1.4 核心功能
1. 多网站岗位爬取（支持静态和动态页面）
2. 关键词严格匹配过滤（remote/远程工作 + AI agent + AI应用开发）
3. 智能数据合并与去重
4. JSON 格式数据存储
5. 完整的反爬策略（UA、延迟、Cookie、代理、行为模拟）
6. 命令行和定时任务双模式运行
7. 完善的错误处理和日志系统

---

## 2. 项目架构

### 2.1 目录结构

```
job-scraper/
├── scraper/              # 核心爬虫模块
│   ├── __init__.py
│   ├── base.py          # 基础爬虫抽象类
│   ├── strategies/       # 不同网站的爬取策略
│   │   ├── __init__.py
│   │   ├── eleduck.py
│   │   ├── v2ex.py
│   │   ├── remoteok.py
│   │   ├── weworkremotely.py
│   │   ├── arc.py
│   │   ├── offershow.py
│   │   └── yuancheng.py
│   └── utils/            # 工具函数
│       ├── __init__.py
│       ├── anti_crawl.py # 反爬策略
│       ├── matcher.py    # 关键词匹配
│       └── storage.py    # 数据存储与去重
├── config/               # 配置文件
│   ├── __init__.py
│   ├── sites.yaml        # 网站配置
│   └── keywords.yaml     # 关键词配置
├── data/                 # 数据目录
│   └── jobs.json         # 岗位数据（gitignore）
├── logs/                 # 日志目录（gitignore）
│   └── scraper_YYYY-MM-DD.log
├── cookies/              # Cookie 存储（gitignore）
│   └── {site}_cookies.json
├── requirements.txt      # Python依赖
├── main.py              # 命令行入口
├── scheduler.py         # 定时任务入口
├── README.md            # 项目说明
└── .gitignore
```

### 2.2 核心架构设计

**策略模式 + 模板方法模式**

- **BaseScraper**: 抽象基类，定义爬取流程模板
  - `fetch()` - 获取页面（支持 requests/playwright）
  - `parse()` - 解析页面（子类实现）
  - `extract_jobs()` - 提取岗位列表（子类实现）
  - `run()` - 执行完整爬取流程

- **SiteStrategy**: 每个网站实现独立的爬取策略
  - 继承 `BaseScraper`
  - 实现网站特定的解析逻辑
  - 配置网站特定的反爬参数

- **AntiCrawlManager**: 统一的反爬策略管理器
  - User-Agent 轮换
  - 请求延迟控制
  - Cookie 管理
  - 代理池管理（可选）
  - 行为模拟

- **StorageManager**: 数据存储与合并
  - JSON 文件读写
  - 智能去重（基于 URL + 标题哈希）
  - 数据合并（保留最新信息）

---

## 3. 反爬策略实现

### 3.1 User-Agent 管理

```python
from fake_useragent import UserAgent

class UserAgentManager:
    def __init__(self):
        self.ua = UserAgent()
        self.cache = {}  # 缓存已生成的 UA
    
    def get_random_ua(self, browser_type='chrome'):
        """获取随机 User-Agent"""
        # 支持 chrome, firefox, safari
        # 缓存机制避免频繁生成
        pass
    
    def rotate_ua(self):
        """轮换 User-Agent"""
        pass
```

**策略**:
- 每个请求随机选择 UA
- 支持按浏览器类型选择
- 缓存机制减少生成开销
- 检测到封禁时自动轮换

### 3.2 请求延迟策略

```python
import random
import time

class DelayManager:
    def __init__(self, base_delay=(2, 5)):
        self.base_delay = base_delay  # (min, max) 秒
        self.failure_count = 0
    
    def wait(self):
        """基础延迟"""
        delay = random.uniform(*self.base_delay)
        time.sleep(delay)
    
    def exponential_backoff(self):
        """指数退避"""
        delay = 2 ** self.failure_count
        time.sleep(min(delay, 60))  # 最大 60 秒
        self.failure_count += 1
    
    def reset(self):
        """重置失败计数"""
        self.failure_count = 0
```

**策略**:
- 基础延迟：2-5 秒随机
- 检测到 429/503 时延长延迟
- 连续失败时指数退避（2s → 4s → 8s → ...）
- 成功请求后重置失败计数

### 3.3 Cookie 与会话管理

```python
import json
import os
from requests import Session

class CookieManager:
    def __init__(self, site_name):
        self.site_name = site_name
        self.cookie_file = f"cookies/{site_name}_cookies.json"
        self.session = Session()
        self.load_cookies()
    
    def load_cookies(self):
        """从文件加载 Cookie"""
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
                self.session.cookies.update(cookies)
    
    def save_cookies(self):
        """保存 Cookie 到文件"""
        os.makedirs('cookies', exist_ok=True)
        with open(self.cookie_file, 'w') as f:
            json.dump(dict(self.session.cookies), f)
    
    def is_logged_in(self):
        """检测登录状态（子类实现）"""
        pass
```

**策略**:
- 使用 `requests.Session()` 保持会话
- Cookie 持久化到文件
- 跨运行恢复会话
- 检测登录状态，失效时提示

### 3.4 代理 IP 池（可选）

```python
class ProxyPool:
    def __init__(self, proxy_list=None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
    
    def get_proxy(self):
        """获取下一个可用代理"""
        if not self.proxies:
            return None
        
        # 轮换代理
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        # 跳过失败的代理
        if proxy in self.failed_proxies:
            return self.get_proxy()
        
        return proxy
    
    def mark_failed(self, proxy):
        """标记代理失败"""
        self.failed_proxies.add(proxy)
    
    def test_proxy(self, proxy):
        """测试代理可用性"""
        # 发送测试请求
        pass
```

**策略**:
- 配置文件指定代理列表
- 自动轮换使用
- 失败自动切换
- 代理可用性检测

### 3.5 行为模拟（Playwright）

```python
from playwright.sync_api import Page
import random

class BehaviorSimulator:
    @staticmethod
    def simulate_human(page: Page):
        """模拟人类行为"""
        # 随机鼠标移动
        page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600)
        )
        
        # 随机滚动
        scroll_amount = random.randint(200, 800)
        page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        
        # 模拟阅读时间
        time.sleep(random.uniform(3, 8))
```

**策略**:
- 随机鼠标移动轨迹
- 随机页面滚动
- 模拟阅读时间（3-8 秒）
- 随机点击（如需要）

### 3.6 Robots.txt 尊重

```python
from urllib.robotparser import RobotFileParser

class RobotsChecker:
    def __init__(self, base_url):
        self.rp = RobotFileParser()
        self.rp.set_url(f"{base_url}/robots.txt")
        self.rp.read()
    
    def can_fetch(self, user_agent, url):
        """检查是否允许爬取"""
        return self.rp.can_fetch(user_agent, url)
```

**策略**:
- 自动解析 robots.txt
- 可配置是否遵守（默认遵守）
- 记录违反 robots.txt 的警告

---

## 4. 数据存储与智能合并

### 4.1 数据结构

```python
{
    "id": "hash(url + title)",  # 唯一标识
    "title": "职位标题",
    "company": "公司名称",
    "url": "岗位链接",
    "source": "来源网站（eleduck/v2ex/...）",
    "published_at": "2026-02-07T10:30:00Z",  # ISO 8601
    "salary": "薪资范围（如有）",
    "location": "工作地点",
    "description": "职位描述（完整文本）",
    "requirements": "任职要求",
    "tags": ["tag1", "tag2"],  # 标签数组
    "apply_method": "申请方式/链接",
    "first_seen": "2026-02-07T10:30:00Z",  # 首次发现时间
    "last_updated": "2026-02-07T10:30:00Z",  # 最后更新时间
    "update_count": 1  # 更新次数
}
```

### 4.2 智能合并策略

```python
import hashlib
import json
from datetime import datetime

class StorageManager:
    def __init__(self, data_file="data/jobs.json"):
        self.data_file = data_file
        self.jobs = self.load_jobs()
    
    def generate_id(self, url, title):
        """生成唯一 ID"""
        content = f"{url}|{title}".lower()
        return hashlib.md5(content.encode()).hexdigest()
    
    def merge_job(self, new_job):
        """智能合并岗位"""
        job_id = self.generate_id(new_job['url'], new_job['title'])
        
        if job_id in self.jobs:
            # 合并逻辑
            old_job = self.jobs[job_id]
            
            # 保留首次发现时间
            new_job['first_seen'] = old_job.get('first_seen', new_job['published_at'])
            
            # 更新最后更新时间
            new_job['last_updated'] = datetime.now().isoformat()
            
            # 更新计数
            new_job['update_count'] = old_job.get('update_count', 0) + 1
            
            # 字段合并：新数据覆盖，缺失字段保留旧值
            merged = {**old_job, **new_job}
            self.jobs[job_id] = merged
        else:
            # 新岗位
            new_job['id'] = job_id
            new_job['first_seen'] = new_job['published_at']
            new_job['last_updated'] = new_job['published_at']
            new_job['update_count'] = 1
            self.jobs[job_id] = new_job
    
    def save_jobs(self):
        """保存到文件"""
        os.makedirs('data', exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.jobs, f, ensure_ascii=False, indent=2)
```

**合并规则**:
- 基于 URL + 标题的 MD5 哈希去重
- 相同岗位：保留最新信息
- `first_seen` 保持不变
- `last_updated` 和 `update_count` 更新
- 字段合并：新数据覆盖，缺失字段保留旧值

### 4.3 关键词匹配

```python
class KeywordMatcher:
    def __init__(self, keywords=None):
        self.keywords = keywords or [
            "remote", "远程工作",
            "AI agent", "AI应用开发"
        ]
    
    def match(self, text):
        """严格匹配：必须包含所有关键词"""
        text_lower = text.lower()
        
        # 检查每个关键词
        for keyword in self.keywords:
            if keyword.lower() not in text_lower:
                return False
        
        return True
    
    def match_job(self, job):
        """匹配岗位"""
        # 检查标题和描述
        title = job.get('title', '')
        description = job.get('description', '')
        
        combined_text = f"{title} {description}"
        return self.match(combined_text)
```

**匹配策略**:
- 严格匹配：标题或描述必须同时包含所有关键词
- 不区分大小写
- 支持中英文关键词
- 关键词可配置

---

## 5. 运行模式与错误处理

### 5.1 命令行模式

```python
# main.py
import argparse
from scraper import ScraperFactory

def main():
    parser = argparse.ArgumentParser(description='远程AI岗位爬虫')
    parser.add_argument('--site', help='指定网站（不指定则爬取全部）')
    parser.add_argument('--keywords', nargs='+', help='自定义关键词')
    parser.add_argument('--output', default='data/jobs.json', help='输出文件')
    parser.add_argument('--proxy', action='store_true', help='启用代理池')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    scraper = ScraperFactory.create(args.site, args)
    scraper.run()

if __name__ == '__main__':
    main()
```

**使用示例**:
```bash
# 爬取所有网站
python main.py --verbose

# 爬取指定网站
python main.py --site remoteok --verbose

# 自定义关键词
python main.py --keywords "remote" "AI" --verbose
```

### 5.2 定时任务模式

```python
# scheduler.py
import schedule
import time
from scraper import ScraperFactory

def run_scraper():
    """执行爬取任务"""
    scraper = ScraperFactory.create_all()
    scraper.run()

# 配置定时任务（每天 9:00）
schedule.every().day.at("09:00").do(run_scraper)

# 或者使用 APScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(run_scraper, 'cron', hour=9, minute=0)
scheduler.start()
```

**配置**:
- 支持配置文件指定运行时间
- 后台运行，日志记录到文件
- 可选邮件/通知功能

### 5.3 错误处理策略

```python
class ScraperError(Exception):
    """爬虫异常基类"""
    pass

class CaptchaDetectedError(ScraperError):
    """验证码检测异常"""
    pass

class RateLimitError(ScraperError):
    """频率限制异常"""
    pass

class ScraperBase:
    def run(self):
        try:
            # 爬取逻辑
            pass
        except CaptchaDetectedError:
            logger.warning("检测到验证码，暂停爬取")
            # 暂停并提示手动处理
        except RateLimitError:
            logger.warning("触发频率限制，延长延迟")
            # 延长延迟或切换代理
        except Exception as e:
            logger.error(f"爬取失败: {e}")
            # 记录错误，继续下一个网站
```

**错误处理**:
- **验证码检测**: 识别到验证码时暂停并提示
- **封禁检测**: 403/429 时延长延迟或切换代理
- **网络异常**: 自动重试（最多 3 次），指数退避
- **解析失败**: 记录错误日志，跳过该岗位
- **优雅退出**: Ctrl+C 时保存已爬取数据

### 5.4 日志系统

```python
import logging
from datetime import datetime

def setup_logger(verbose=False):
    """配置日志系统"""
    log_file = f"logs/scraper_{datetime.now().strftime('%Y-%m-%d')}.log"
    os.makedirs('logs', exist_ok=True)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if not verbose else logging.DEBUG)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 配置根日志
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

**日志级别**:
- DEBUG: 详细调试信息
- INFO: 正常操作信息（爬取开始/结束、统计）
- WARNING: 警告（验证码、频率限制）
- ERROR: 错误（解析失败、网络异常）

---

## 6. 网站特定实现策略

### 6.1 电鸭社区 (eleduck.com)
- **策略**: requests + BeautifulSoup
- **特点**: 静态页面，需要登录（Cookie）
- **解析**: 解析岗位列表页，提取详情页链接

### 6.2 V2EX (v2ex.com/go/jobs)
- **策略**: requests + BeautifulSoup
- **特点**: 静态页面，可能需要登录
- **解析**: 解析主题列表，提取岗位信息

### 6.3 RemoteOK (remoteok.com)
- **策略**: Playwright（JS 渲染）
- **特点**: 动态加载，反爬较严格
- **解析**: 等待页面加载完成，解析岗位卡片

### 6.4 We Work Remotely (weworkremotely.com)
- **策略**: requests + BeautifulSoup
- **特点**: 静态页面，结构清晰
- **解析**: 解析岗位列表和详情页

### 6.5 Arc.dev (arc.dev)
- **策略**: Playwright（可能需要）
- **特点**: 可能需要登录，动态内容
- **解析**: 根据实际页面结构实现

### 6.6 OfferShow (offershow.com)
- **策略**: requests + BeautifulSoup
- **特点**: 静态页面
- **解析**: 解析岗位列表

### 6.7 远程.work (yuancheng.work)
- **策略**: requests + BeautifulSoup
- **特点**: 静态页面
- **解析**: 解析岗位列表和详情

---

## 7. 配置文件设计

### 7.1 sites.yaml

```yaml
sites:
  eleduck:
    name: "电鸭社区"
    url: "https://eleduck.com"
    strategy: "requests"  # requests 或 playwright
    login_required: true
    delay: [2, 5]  # 延迟范围（秒）
    headers:
      Referer: "https://eleduck.com"
  
  remoteok:
    name: "RemoteOK"
    url: "https://remoteok.com"
    strategy: "playwright"
    login_required: false
    delay: [3, 6]
    wait_for_selector: ".job-listing"  # Playwright 等待选择器
```

### 7.2 keywords.yaml

```yaml
keywords:
  - "remote"
  - "远程工作"
  - "AI agent"
  - "AI应用开发"

# 匹配模式：strict（严格）或 loose（宽松）
match_mode: "strict"
```

---

## 8. 依赖清单

```txt
requests>=2.31.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
fake-useragent>=1.4.0
pyyaml>=6.0.1
schedule>=1.2.0
APScheduler>=3.10.4  # 可选，用于更强大的定时任务
```

**安装 Playwright 浏览器**:
```bash
playwright install chromium
```

---

## 9. 实施优先级

### Phase 1: 核心功能（MVP）
1. ✅ 基础架构搭建
2. ✅ BaseScraper 抽象类
3. ✅ 反爬策略基础实现（UA、延迟、Cookie）
4. ✅ 数据存储与合并
5. ✅ 关键词匹配
6. ✅ 实现 2-3 个简单网站（requests 策略）

### Phase 2: 完善功能
1. ✅ 实现所有网站策略
2. ✅ Playwright 集成
3. ✅ 代理池支持
4. ✅ 行为模拟
5. ✅ 命令行模式完善

### Phase 3: 高级功能
1. ✅ 定时任务模式
2. ✅ 邮件/通知功能
3. ✅ 验证码检测与处理
4. ✅ 性能优化
5. ✅ 文档完善

---

## 10. 测试策略

### 10.1 单元测试
- 关键词匹配逻辑
- 数据合并逻辑
- ID 生成逻辑

### 10.2 集成测试
- 单个网站爬取流程
- 数据存储与读取
- 错误处理流程

### 10.3 端到端测试
- 完整爬取流程（所有网站）
- 定时任务执行
- 异常场景处理

---

*设计文档完成于 2026-02-07*
