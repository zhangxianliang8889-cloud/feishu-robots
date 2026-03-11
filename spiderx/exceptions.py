"""SpiderX 异常定义"""


class SpiderException(Exception):
    """爬虫基础异常"""
    pass


class DownloadException(SpiderException):
    """下载异常"""
    pass


class ParseException(SpiderException):
    """解析异常"""
    pass


class ProxyException(SpiderException):
    """代理异常"""
    pass


class RetryException(SpiderException):
    """重试耗尽异常"""
    pass


class UrlPoolException(SpiderException):
    """URL池异常"""
    pass


class ConfigException(SpiderException):
    """配置异常"""
    pass


class TimeoutException(SpiderException):
    """超时异常"""
    pass


class BlockedException(SpiderException):
    """被拦截异常"""
    pass
