"""SpiderX 页面加载器模块"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import time
import logging

from .config import SpiderConfig, LoadMode
from .exceptions import DownloadException, TimeoutException, BlockedException

logger = logging.getLogger(__name__)


@dataclass
class Response:
    """响应对象"""
    url: str
    html: str
    status_code: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    elapsed: float
    redirect_url: Optional[str] = None
    
    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class PageLoader(ABC):
    """页面加载器基类"""
    
    def __init__(self, config: SpiderConfig):
        self.config = config
    
    @abstractmethod
    def load(self, url: str, **kwargs) -> Response:
        """加载页面"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭加载器"""
        pass


class RequestsLoader(PageLoader):
    """
    Requests加载器 - 非JS渲染，速度快
    
    依赖: requests, lxml, beautifulsoup4
    """
    
    def __init__(self, config: SpiderConfig):
        super().__init__(config)
        self._session = None
        self._init_session()
    
    def _init_session(self):
        """初始化Session"""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            self._session = requests.Session()
            
            retry_strategy = Retry(
                total=self.config.retry_times,
                backoff_factor=self.config.retry_backoff,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            self._session.headers.update(self.config.get_headers())
            if self.config.cookies:
                self._session.cookies.update(self.config.cookies)
                
        except ImportError:
            raise ImportError("请安装requests: pip install requests")
    
    def load(self, url: str, 
             method: str = "GET",
             params: Optional[Dict] = None,
             data: Optional[Dict] = None,
             json_data: Optional[Dict] = None,
             headers: Optional[Dict] = None,
             cookies: Optional[Dict] = None,
             proxy: Optional[str] = None,
             **kwargs) -> Response:
        """加载页面"""
        import requests
        
        request_headers = self.config.get_headers()
        if headers:
            request_headers.update(headers)
        
        request_cookies = self.config.cookies.copy()
        if cookies:
            request_cookies.update(cookies)
        
        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}
        
        start_time = time.time()
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                cookies=request_cookies,
                proxies=proxies,
                timeout=(self.config.connect_timeout, self.config.read_timeout),
                allow_redirects=self.config.follow_redirects,
                **kwargs
            )
            
            elapsed = time.time() - start_time
            
            if self._is_blocked(response):
                raise BlockedException(f"请求被拦截: {url}")
            
            return Response(
                url=str(response.url),
                html=response.text,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                elapsed=elapsed,
                redirect_url=str(response.url) if response.url != url else None
            )
            
        except requests.Timeout:
            raise TimeoutException(f"请求超时: {url}")
        except requests.RequestException as e:
            raise DownloadException(f"下载失败: {url}, 错误: {e}")
    
    def _is_blocked(self, response) -> bool:
        """检测是否被拦截"""
        blocked_indicators = [
            "验证码",
            "captcha",
            "access denied",
            "forbidden",
            "blocked",
            "请输入验证码",
            "安全验证",
        ]
        
        if response.status_code in [403, 429]:
            return True
        
        text_lower = response.text.lower()
        for indicator in blocked_indicators:
            if indicator.lower() in text_lower:
                return True
        
        return False
    
    def close(self):
        """关闭Session"""
        if self._session:
            self._session.close()
            self._session = None


class PlaywrightLoader(PageLoader):
    """
    Playwright加载器 - JS渲染，兼容性高
    
    依赖: playwright
    """
    
    def __init__(self, config: SpiderConfig):
        super().__init__(config)
        self._playwright = None
        self._browser = None
        self._context = None
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            self._context = self._browser.new_context(
                user_agent=self.config.get_user_agent(),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            
        except ImportError:
            raise ImportError("请安装playwright: pip install playwright && playwright install")
    
    def load(self, url: str,
             wait_selector: Optional[str] = None,
             wait_timeout: int = 30000,
             scroll: bool = False,
             scroll_times: int = 3,
             execute_script: Optional[str] = None,
             **kwargs) -> Response:
        """加载页面"""
        start_time = time.time()
        
        page = self._context.new_page()
        
        try:
            response = page.goto(
                url,
                timeout=self.config.download_timeout * 1000,
                wait_until="networkidle"
            )
            
            if not response:
                raise DownloadException(f"无法访问: {url}")
            
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=wait_timeout)
            
            if scroll:
                for _ in range(scroll_times):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(0.5)
            
            if execute_script:
                page.evaluate(execute_script)
            
            html = page.content()
            elapsed = time.time() - start_time
            
            return Response(
                url=url,
                html=html,
                status_code=response.status,
                headers=dict(response.headers),
                cookies={c["name"]: c["value"] for c in self._context.cookies()},
                elapsed=elapsed
            )
            
        except Exception as e:
            raise DownloadException(f"Playwright加载失败: {url}, 错误: {e}")
        finally:
            page.close()
    
    def close(self):
        """关闭浏览器"""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()


class SeleniumLoader(PageLoader):
    """
    Selenium加载器 - JS渲染，兼容性最高
    
    依赖: selenium, webdriver-manager
    """
    
    def __init__(self, config: SpiderConfig):
        super().__init__(config)
        self._driver = None
        self._init_driver()
    
    def _init_driver(self):
        """初始化WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(f"--user-agent={self.config.get_user_agent()}")
            options.add_argument("--window-size=1920,1080")
            
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
            except ImportError:
                self._driver = webdriver.Chrome(options=options)
            
            self._driver.set_page_load_timeout(self.config.download_timeout)
            
        except ImportError:
            raise ImportError("请安装selenium: pip install selenium webdriver-manager")
    
    def load(self, url: str,
             wait_selector: Optional[str] = None,
             wait_timeout: int = 30,
             scroll: bool = False,
             scroll_times: int = 3,
             execute_script: Optional[str] = None,
             **kwargs) -> Response:
        """加载页面"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        start_time = time.time()
        
        try:
            self._driver.get(url)
            
            if wait_selector:
                WebDriverWait(self._driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            
            if scroll:
                for _ in range(scroll_times):
                    self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
            
            if execute_script:
                self._driver.execute_script(execute_script)
            
            html = self._driver.page_source
            elapsed = time.time() - start_time
            
            return Response(
                url=url,
                html=html,
                status_code=200,
                headers={},
                cookies={c["name"]: c["value"] for c in self._driver.get_cookies()},
                elapsed=elapsed
            )
            
        except Exception as e:
            raise DownloadException(f"Selenium加载失败: {url}, 错误: {e}")
    
    def close(self):
        """关闭WebDriver"""
        if self._driver:
            self._driver.quit()
            self._driver = None


def create_loader(config: SpiderConfig) -> PageLoader:
    """创建页面加载器"""
    if config.load_mode == LoadMode.REQUESTS:
        return RequestsLoader(config)
    elif config.load_mode == LoadMode.PLAYWRIGHT:
        return PlaywrightLoader(config)
    elif config.load_mode == LoadMode.SELENIUM:
        return SeleniumLoader(config)
    else:
        return RequestsLoader(config)
