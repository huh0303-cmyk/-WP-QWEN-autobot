#!/usr/bin/env python3
"""GSC 서비스 계정 이메일만 출력 (Search Console에 사용자로 추가할 때 필요)."""
import json
import os

d = json.loads(os.environ["GSC_SERVICE_ACCOUNT_JSON"])
print(d["client_email"])
