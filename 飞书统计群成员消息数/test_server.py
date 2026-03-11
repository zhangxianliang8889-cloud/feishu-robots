#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta

APP_ID = "cli_a9233dfe18389bde"
APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"
NO_PROXY = {}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token") if resp.get("code") == 0 else None

def get_messages(token, group_id):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"container_id_type": "chat", "container_id": group_id, "page_size": "50"}
    resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
    if resp.get("code") == 0:
        return len(resp.get("data", {}).get("items", []))
    return 0

def main():
    print("Testing server API...")
    token = get_token()
    if token:
        count = get_messages(token, "oc_48e2db5c69667ddfe1a50331939f98e1")
        print(f"Message count: {count}")
    else:
        print("Token failed")

if __name__ == "__main__":
    main()
