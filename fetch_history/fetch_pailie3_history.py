#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排列三 历史开奖数据获取脚本

功能：
1. 从 500 彩票网爬取排列三历史开奖数据
2. 自动保存为 JSON 格式
3. 包含错误处理和重试机制

使用方法：
    python3 fetch_pailie3_history.py

输出：
    lottery_data.json - 包含所有开奖数据的 JSON 文件
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import sys
import os
from datetime import datetime, timedelta


class Pailie3DataFetcher:
    """排列三数据获取器"""

    def __init__(self):
        self.base_url = "https://datachart.500.com/p3/history/history.shtml"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_page(self, url, retry=3):
        for attempt in range(retry):
            try:
                print(f"正在获取数据... (尝试 {attempt + 1}/{retry})")
                response = self.session.get(url, timeout=10)
                response.encoding = 'gb2312'
                if response.status_code == 200:
                    return BeautifulSoup(response.text, 'html.parser')
                else:
                    print(f"HTTP 状态码: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"请求失败: {e}")
                if attempt < retry - 1:
                    time.sleep(2)
        return None

    def parse_lottery_data(self, soup):
        data_list = []
        try:
            table = soup.find('tbody')
            if not table:
                table = soup.find('table')
            if not table:
                print("未找到数据表格")
                return data_list

            rows = table.find_all('tr')
            if not rows:
                print("表格中没有数据行")
                return data_list

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5:
                    continue
                try:
                    period = cols[0].text.strip()
                    # 排列三开奖号码（3位数字）
                    result = "".join(cols[1].text.strip().split())
                    # 日期
                    date = cols[-1].text.strip() if len(cols) > 3 else ""
                    if not period or not result or len(result) != 3:
                        continue
                    data_list.append({
                        "period": period,
                        "date": date,
                        "result": result
                    })
                except Exception as e:
                    print(f"解析行数据时出错: {e}")
                    continue

            print(f"成功解析 {len(data_list)} 期数据")
        except Exception as e:
            print(f"解析数据时发生错误: {e}")
        return data_list

    def merge_with_existing_data(self, new_data, existing_file):
        existing_data = []
        if os.path.exists(existing_file):
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                print(f"已加载现有数据: {len(existing_data)} 期")
            except Exception as e:
                print(f"加载现有数据时出错: {e}")

        data_dict = {}
        for item in existing_data:
            data_dict[item['period']] = item

        new_count = 0
        for item in new_data:
            if item['period'] not in data_dict:
                new_count += 1
            data_dict[item['period']] = item

        merged_data = list(data_dict.values())
        merged_data.sort(key=lambda x: x['period'], reverse=True)
        print(f"合并完成: 新增 {new_count} 期, 总计 {len(merged_data)} 期")
        return merged_data

    def backup_existing_file(self, filename):
        if os.path.exists(filename):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = filename.replace('.json', f'_backup_{timestamp}.json')
            try:
                import shutil
                shutil.copy2(filename, backup_name)
                print(f"已创建备份文件: {backup_name}")
                return backup_name
            except Exception as e:
                print(f"创建备份时出错: {e}")
                return None
        return None

    def predict_next_draw(self, latest_period, latest_date):
        try:
            period_num = int(latest_period)
            last_draw_date = datetime.strptime(latest_date, '%Y-%m-%d')

            # 排列三每天开奖（除个别节假日）
            next_date = last_draw_date + timedelta(days=1)
            next_period = str(period_num + 1).zfill(len(latest_period))
            next_date_str = next_date.strftime('%Y-%m-%d')
            next_date_display = next_date.strftime('%Y年%m月%d日')
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            weekday = weekday_names[next_date.weekday()]

            return {
                'next_period': next_period,
                'next_date': next_date_str,
                'next_date_display': next_date_display,
                'weekday': weekday,
                'draw_time': '21:30'
            }
        except Exception as e:
            print(f"预测下一期信息时出错: {e}")
            return None

    def format_for_web(self, data):
        formatted = {
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data
        }
        if data and len(data) > 0:
            latest = data[0]
            next_draw_info = self.predict_next_draw(latest['period'], latest['date'])
            if next_draw_info:
                formatted['next_draw'] = next_draw_info
        return formatted

    def save_to_json(self, data, filename="lottery_data.json", preserve_history=True):
        try:
            if preserve_history:
                self.backup_existing_file(filename)
                merged_data = self.merge_with_existing_data(data, filename)
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, ensure_ascii=False, indent=2)
                print(f"\n数据已成功保存到 {filename}")
                print(f"共保存 {len(merged_data)} 期数据")

                try:
                    web_data_path = os.path.join(os.path.dirname(filename), '..', 'data', 'pailie3_history.json')
                    formatted_data = self.format_for_web(merged_data)
                    with open(web_data_path, 'w', encoding='utf-8') as f:
                        json.dump(formatted_data, f, ensure_ascii=False, indent=2)
                    print(f"✓ 已同步到网页数据文件: {web_data_path}")
                except Exception as e:
                    print(f"⚠️  同步到网页数据失败: {e}")
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"\n数据已成功保存到 {filename}")
                print(f"共保存 {len(data)} 期数据")
        except Exception as e:
            print(f"保存文件时出错: {e}")

    def fetch_and_save(self, output_file="lottery_data.json", preserve_history=True):
        print("=" * 50)
        print("排列三历史开奖数据获取工具")
        print("=" * 50)

        soup = self.fetch_page(self.base_url)
        if not soup:
            print("获取网页失败，请检查网络连接或稍后重试")
            return False

        lottery_data = self.parse_lottery_data(soup)
        if not lottery_data:
            print("未能解析到任何数据")
            return False

        print("\n最新 5 期数据预览：")
        print("-" * 50)
        for item in lottery_data[:5]:
            print(f"期号: {item['period']} | 开奖号码: {item['result']} | 日期: {item['date']}")

        self.save_to_json(lottery_data, output_file, preserve_history)
        return True


def main():
    fetcher = Pailie3DataFetcher()
    output_file = "lottery_data.json"
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    success = fetcher.fetch_and_save(output_file)
    if success:
        print("\n✓ 数据获取完成！")
        print(f"✓ 文件位置: {output_file}")
    else:
        print("\n✗ 数据获取失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
