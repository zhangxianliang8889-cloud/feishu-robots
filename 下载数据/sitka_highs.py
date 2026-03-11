import csv
from datetime import datetime
import matplotlib.pyplot as plt

filename = '下载数据/sitka_weather_07-2018_simple.csv'
with open(filename) as f:
    reader = csv.reader(f)
    header_row = next(reader)

    # 从文件中获取日期和最高温度。
    dates, highs = [], []
    for row in reader:
        if row[2] and row[5]:
            current_date = datetime.strptime(row[2], '%Y-%m-%d')
            dates.append(current_date)
            high = int(row[5])
            highs.append(high)

print("日期列表:", dates)
print("最高温度:", highs)

# 根据最高温度绘制图形。
plt.style.use('seaborn-v0_8')
fig, ax = plt.subplots()
ax.plot(dates, highs, c='red')

# 设置图形的格式。
ax.set_title("Daily High Temperatures, July 2018", fontsize=24)
ax.set_xlabel('', fontsize=16)
fig.autofmt_xdate()
ax.set_ylabel("Temperature (F)", fontsize=16)
ax.tick_params(axis='both', which='major', labelsize=16)

plt.show()
