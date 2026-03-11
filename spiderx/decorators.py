"""SpiderX 装饰器模块 - 数据提取注解系统"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Callable, Dict, Type
from enum import Enum
from functools import wraps
import re
from bs4 import BeautifulSoup
from lxml import etree
import json


class ExtractorType(Enum):
    """提取器类型"""
    CSS = "css"
    XPATH = "xpath"
    REGEX = "regex"
    JSON = "json"
    ATTR = "attr"


@dataclass
class FieldExtractor:
    """字段提取器"""
    name: str
    extractor_type: ExtractorType
    selector: str
    attr: Optional[str] = None
    default: Any = None
    multiple: bool = False
    processor: Optional[Callable] = None
    

@dataclass
class PageVO:
    """页面数据对象基类"""
    _extractors: Dict[str, FieldExtractor] = field(default_factory=dict, repr=False)
    _url: str = ""
    _raw_html: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"_url": self._url}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                result[key] = value
        return result


def extract_field(extractor: FieldExtractor):
    """字段提取装饰器工厂"""
    def decorator(func_or_class):
        if callable(func_or_class):
            if not hasattr(func_or_class, "_extractors"):
                func_or_class._extractors = {}
            func_or_class._extractors[extractor.name] = extractor
            return func_or_class
        else:
            if not hasattr(func_or_class, "_extractors"):
                func_or_class._extractors = {}
            func_or_class._extractors[extractor.name] = extractor
            return func_or_class
    return decorator


def css(selector: str, 
        attr: Optional[str] = None, 
        default: Any = None, 
        multiple: bool = False,
        processor: Optional[Callable] = None):
    """
    CSS选择器提取装饰器
    
    Args:
        selector: CSS选择器
        attr: 属性名，None表示提取文本
        default: 默认值
        multiple: 是否提取多个
        processor: 后处理函数
    
    Example:
        @css("h1.title")
        def title(self, value):
            return value.strip()
    """
    def decorator(func):
        extractor = FieldExtractor(
            name=func.__name__,
            extractor_type=ExtractorType.CSS,
            selector=selector,
            attr=attr,
            default=default,
            multiple=multiple,
            processor=processor or func
        )
        func._extractor = extractor
        return func
    return decorator


def xpath(selector: str,
          attr: Optional[str] = None,
          default: Any = None,
          multiple: bool = False,
          processor: Optional[Callable] = None):
    """
    XPath选择器提取装饰器
    
    Args:
        selector: XPath表达式
        attr: 属性名
        default: 默认值
        multiple: 是否提取多个
        processor: 后处理函数
    """
    def decorator(func):
        extractor = FieldExtractor(
            name=func.__name__,
            extractor_type=ExtractorType.XPATH,
            selector=selector,
            attr=attr,
            default=default,
            multiple=multiple,
            processor=processor or func
        )
        func._extractor = extractor
        return func
    return decorator


def regex(pattern: str,
          group: int = 0,
          default: Any = None,
          multiple: bool = False,
          processor: Optional[Callable] = None):
    """
    正则表达式提取装饰器
    
    Args:
        pattern: 正则表达式
        group: 捕获组索引
        default: 默认值
        multiple: 是否提取多个
        processor: 后处理函数
    """
    def decorator(func):
        extractor = FieldExtractor(
            name=func.__name__,
            extractor_type=ExtractorType.REGEX,
            selector=pattern,
            attr=str(group),
            default=default,
            multiple=multiple,
            processor=processor or func
        )
        func._extractor = extractor
        return func
    return decorator


def json_field(path: str,
               default: Any = None,
               processor: Optional[Callable] = None):
    """
    JSON字段提取装饰器
    
    Args:
        path: JSON路径，如 "data.items[0].name"
        default: 默认值
        processor: 后处理函数
    """
    def decorator(func):
        extractor = FieldExtractor(
            name=func.__name__,
            extractor_type=ExtractorType.JSON,
            selector=path,
            default=default,
            multiple=False,
            processor=processor or func
        )
        func._extractor = extractor
        return func
    return decorator


def attr(attr_name: str,
         default: Any = None,
         processor: Optional[Callable] = None):
    """
    属性提取装饰器
    
    Args:
        attr_name: 属性名
        default: 默认值
        processor: 后处理函数
    """
    def decorator(func):
        extractor = FieldExtractor(
            name=func.__name__,
            extractor_type=ExtractorType.ATTR,
            selector=attr_name,
            default=default,
            multiple=False,
            processor=processor or func
        )
        func._extractor = extractor
        return func
    return decorator


class DataExtractor:
    """数据提取器 - 从页面提取数据到PageVO"""
    
    def __init__(self, html: str, url: str = ""):
        self.html = html
        self.url = url
        self._soup = None
        self._tree = None
    
    @property
    def soup(self) -> BeautifulSoup:
        """BeautifulSoup对象"""
        if self._soup is None:
            self._soup = BeautifulSoup(self.html, "lxml")
        return self._soup
    
    @property
    def tree(self) -> etree._Element:
        """lxml树对象"""
        if self._tree is None:
            self._tree = etree.HTML(self.html)
        return self._tree
    
    def extract(self, page_vo_class: Type[PageVO]) -> PageVO:
        """提取数据到PageVO对象"""
        instance = page_vo_class()
        instance._url = self.url
        instance._raw_html = self.html
        
        for name in dir(page_vo_class):
            method = getattr(page_vo_class, name)
            if hasattr(method, "_extractor"):
                extractor = method._extractor
                value = self._extract_value(extractor)
                if extractor.processor:
                    try:
                        value = extractor.processor(instance, value)
                    except TypeError:
                        value = extractor.processor(value)
                setattr(instance, name, value)
        
        return instance
    
    def _extract_value(self, extractor: FieldExtractor) -> Any:
        """根据提取器类型提取值"""
        try:
            if extractor.extractor_type == ExtractorType.CSS:
                return self._extract_css(extractor)
            elif extractor.extractor_type == ExtractorType.XPATH:
                return self._extract_xpath(extractor)
            elif extractor.extractor_type == ExtractorType.REGEX:
                return self._extract_regex(extractor)
            elif extractor.extractor_type == ExtractorType.JSON:
                return self._extract_json(extractor)
            elif extractor.extractor_type == ExtractorType.ATTR:
                return self._extract_attr(extractor)
        except Exception:
            return extractor.default
        return extractor.default
    
    def _extract_css(self, extractor: FieldExtractor) -> Any:
        """CSS选择器提取"""
        elements = self.soup.select(extractor.selector)
        if not elements:
            return extractor.default
        
        if extractor.multiple:
            results = []
            for el in elements:
                if extractor.attr:
                    results.append(el.get(extractor.attr, extractor.default))
                else:
                    results.append(el.get_text(strip=True))
            return results
        else:
            el = elements[0]
            if extractor.attr:
                return el.get(extractor.attr, extractor.default)
            return el.get_text(strip=True)
    
    def _extract_xpath(self, extractor: FieldExtractor) -> Any:
        """XPath提取"""
        elements = self.tree.xpath(extractor.selector)
        if not elements:
            return extractor.default
        
        if extractor.multiple:
            results = []
            for el in elements:
                if isinstance(el, str):
                    results.append(el.strip())
                elif extractor.attr:
                    results.append(el.get(extractor.attr, extractor.default))
                else:
                    results.append(el.text_content().strip() if hasattr(el, "text_content") else str(el))
            return results
        else:
            el = elements[0]
            if isinstance(el, str):
                return el.strip()
            if extractor.attr:
                return el.get(extractor.attr, extractor.default)
            return el.text_content().strip() if hasattr(el, "text_content") else str(el)
    
    def _extract_regex(self, extractor: FieldExtractor) -> Any:
        """正则表达式提取"""
        pattern = re.compile(extractor.selector, re.DOTALL)
        group = int(extractor.attr) if extractor.attr else 0
        
        if extractor.multiple:
            matches = pattern.findall(self.html)
            return [m[group] if isinstance(m, tuple) else m for m in matches]
        else:
            match = pattern.search(self.html)
            if match:
                groups = match.groups()
                if groups:
                    return groups[group] if group < len(groups) else groups[0]
                return match.group(0)
            return extractor.default
    
    def _extract_json(self, extractor: FieldExtractor) -> Any:
        """JSON路径提取"""
        try:
            data = json.loads(self.html)
        except json.JSONDecodeError:
            data = self._extract_json_from_html()
            if data is None:
                return extractor.default
        
        path_parts = extractor.selector.split(".")
        current = data
        
        for part in path_parts:
            if current is None:
                return extractor.default
            
            if "[" in part:
                key = part.split("[")[0]
                index = int(part.split("[")[1].rstrip("]"))
                if key:
                    current = current.get(key, {})
                if isinstance(current, list) and 0 <= index < len(current):
                    current = current[index]
                else:
                    return extractor.default
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return extractor.default
        
        return current if current is not None else extractor.default
    
    def _extract_json_from_html(self) -> Any:
        """从HTML中提取JSON数据"""
        scripts = self.soup.find_all("script")
        for script in scripts:
            if script.string:
                try:
                    return json.loads(script.string)
                except json.JSONDecodeError:
                    continue
        return None
    
    def _extract_attr(self, extractor: FieldExtractor) -> Any:
        """从根元素提取属性"""
        root = self.soup.find()
        if root:
            return root.get(extractor.selector, extractor.default)
        return extractor.default


def page_vo(cls):
    """
    PageVO类装饰器
    
    自动收集所有带有提取装饰器的方法
    
    Example:
        @page_vo
        class ArticlePage(PageVO):
            @css("h1.title")
            def title(self, value):
                return value.strip()
            
            @css("div.content p::text", multiple=True)
            def content(self, values):
                return "\\n".join(values)
    """
    extractors = {}
    for name in dir(cls):
        method = getattr(cls, name)
        if hasattr(method, "_extractor"):
            extractors[name] = method._extractor
    
    cls._extractors = extractors
    return cls
