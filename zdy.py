#!/usr/bin/env python
# coding: utf-8
# zdy.py
"""
Squid+站大爷搭建代理IP池
Author: xNathan
Blog: https://xnathan.com
Github: https://github.com/xNathan
"""
from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip

import logging
import os
import time

import requests
from gevent.pool import Pool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s: - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# 使用StreamHandler输出到屏幕
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

logger.addHandler(ch)

# Squid的配置文件语法
# 将请求转发到父代理
# PEER_CONF = "cache_peer %s parent %s 0 no-query weighted-round-robin weight=1 connect-fail-limit=2 allow-miss max-conn=5\n"
PEER_CONF = "cache_peer %s parent %s 0 proxy-only no-query no-digest round-robin connect-fail-limit=10 connect-timeout=15 max-conn=10 name=proxyip-%s\n"

# 可用代理
GOOD_PROXIES = []

pool = Pool(50)


def check_proxy(proxy):
    """验证代理是否可用
    :param proxy list:[ip, port]"""
    global GOOD_PROXIES
    ip, port = proxy
    _proxies = {"http": "{}:{}".format(ip, port)}
    try:
        ip_url = "http://httpbin.org/ip"
        res = requests.get(ip_url, proxies=_proxies, timeout=10)
        assert ip in res.content
        logger.info("[GOOD] - {}:{}".format(ip, port))
        GOOD_PROXIES.append(proxy)
    except Exception as e:
        logger.error("[BAD] - {}:{}, {}".format(ip, port, e))


def update_conf():
    with open("/etc/squid/squid.conf.original", "r") as F:
        squid_conf = F.readlines()
    squid_conf.append("\n# Cache peer config\n")
    i = 0
    for proxy in GOOD_PROXIES:
        i = i + 1
        squid_conf.append(PEER_CONF % (proxy[0], proxy[1], i))
    with open("/etc/squid/squid.conf", "w") as F:
        F.writelines(squid_conf)


def get_proxy():
    global GOOD_PROXIES
    GOOD_PROXIES = []
    # 1. 获取代理IP资源
    api_url = "http://www.zdopen.com/PrivateProxy/GetIP/?api=201910131255595961&akey=8b831758f29758d6&count=1000&fitter=2&order=2&type=1"
    res = requests.get(api_url).content
    if len(res) == 0:
        logger.error("no data")
    elif "bad" in res:
        logger.error("bad request")
    else:
        logger.info("get all proxies")
        proxies = []
        for line in res.split():
            proxies.append(line.strip().split(":"))
            GOOD_PROXIES.append(line.strip().split(":"))
        # pool.map(check_proxy, proxies)
        # pool.join()
        # 2. 写入Squid配置文件
        update_conf()
        # 3. 重新加载配置文件
        os.system("squid -k reconfigure")
        logger.info(">>>> DONE! <<<<")


def main():
    start = time.time()
    while True:
        # 每30秒获取一批新IP
        if time.time() - start >= 90:
            get_proxy()
            start = time.time()
        time.sleep(5)


if __name__ == "__main__":
    main()
