import json
filename = "user.json"
with open(filename) as f:
    name = json.load(f)  # 从文件里读出"小明"
print(f"你好，{name}！")  # 输出：你好，小明！