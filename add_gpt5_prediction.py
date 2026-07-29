#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加 GPT5 对 25121 期的历史预测并计算命中结果
"""

import json

# GPT5 对 25121 期的预测数据
gpt5_prediction = {
    "prediction_date": "2025-10-23",
    "target_period": "25121",
    "model_id": "GPT5",
    "model_name": "GPT5",
    "predictions": [
        {
            "group_id": 1,
            "strategy": "热号追随者",
            "red_balls": ["17", "18", "23", "24", "25", "26"],
            "blue_ball": "16",
            "description": "选择最近30期频率较高的热号，排除上一期刚开出的号码。"
        },
        {
            "group_id": 2,
            "strategy": "冷号逆向者",
            "red_balls": ["06", "07", "12", "20", "21", "27"],
            "blue_ball": "05",
            "description": "选择最近30期频率最低的冷号，并确保红球奇偶比尽量接近3:3。"
        },
        {
            "group_id": 3,
            "strategy": "平衡策略师",
            "red_balls": ["05", "11", "14", "16", "22", "27"],
            "blue_ball": "14",
            "description": "满足奇偶比、大小比、总和（90-130）和连号限制等多维平衡约束的组合。"
        },
        {
            "group_id": 4,
            "strategy": "周期理论家",
            "red_balls": ["02", "03", "13", "27", "31", "33"],
            "blue_ball": "01",
            "description": "选取短期频率上穿长期频率的红球（近期变热），蓝球选遗漏期数最长者。"
        },
        {
            "group_id": 5,
            "strategy": "综合决策者",
            "red_balls": ["02", "03", "13", "17", "24", "31"],
            "blue_ball": "15",
            "description": "从热号/冷号/周期候选中取样，并以平衡策略的约束进行筛选与调整的综合组合。"
        }
    ]
}

# 25121 期实际开奖结果
actual_result = {
    "period": "25121",
    "date": "2025-10-21",
    "red_balls": ["06", "08", "10", "25", "29", "30"],
    "blue_ball": "08"
}

# 计算命中结果
for pred in gpt5_prediction["predictions"]:
    red_hits = [b for b in pred["red_balls"] if b in actual_result["red_balls"]]
    blue_hit = pred["blue_ball"] == actual_result["blue_ball"]

    pred["hit_result"] = {
        "red_hits": red_hits,
        "red_hit_count": len(red_hits),
        "blue_hit": blue_hit,
        "total_hits": len(red_hits) + (1 if blue_hit else 0)
    }

# 找出最佳组
best_pred = max(gpt5_prediction["predictions"], key=lambda p: p["hit_result"]["total_hits"])
gpt5_prediction["best_group"] = best_pred["group_id"]
gpt5_prediction["best_hit_count"] = best_pred["hit_result"]["total_hits"]

# 读取现有历史预测数据
with open('data/predictions_history.json', 'r', encoding='utf-8') as f:
    history_data = json.load(f)

# 检查 25121 期是否已存在
existing_record = next((r for r in history_data['predictions_history'] if r['target_period'] == '25121'), None)

if existing_record:
    # 添加 GPT5 模型到现有记录
    existing_models = [m['model_id'] for m in existing_record['models']]
    if 'GPT5' not in existing_models:
        model_entry = {
            "model_id": gpt5_prediction["model_id"],
            "model_name": gpt5_prediction["model_name"],
            "predictions": gpt5_prediction["predictions"],
            "best_group": gpt5_prediction["best_group"],
            "best_hit_count": gpt5_prediction["best_hit_count"]
        }
        existing_record['models'].append(model_entry)
        print(f"✓ 已将 GPT5 模型添加到 25121 期的历史记录")
    else:
        print(f"⚠️  GPT5 模型已存在于 25121 期历史记录中，跳过")
else:
    # 创建新的历史记录
    new_record = {
        "prediction_date": gpt5_prediction["prediction_date"],
        "target_period": gpt5_prediction["target_period"],
        "actual_result": actual_result,
        "models": [
            {
                "model_id": gpt5_prediction["model_id"],
                "model_name": gpt5_prediction["model_name"],
                "predictions": gpt5_prediction["predictions"],
                "best_group": gpt5_prediction["best_group"],
                "best_hit_count": gpt5_prediction["best_hit_count"]
            }
        ]
    }
    history_data['predictions_history'].insert(0, new_record)
    print(f"✓ 已创建 25121 期的新历史记录并添加 GPT5 模型")

# 保存更新后的数据
with open('data/predictions_history.json', 'w', encoding='utf-8') as f:
    json.dump(history_data, f, ensure_ascii=False, indent=2)

print(f"\n命中结果:")
print(f"最佳组: 第 {gpt5_prediction['best_group']} 组")
print(f"最高命中数: {gpt5_prediction['best_hit_count']} 个")
print(f"\n各组命中详情:")
for pred in gpt5_prediction["predictions"]:
    hit = pred["hit_result"]
    print(f"组 {pred['group_id']} ({pred['strategy']}): 红球 {hit['red_hit_count']} 个 {hit['red_hits']}, 蓝球 {'✓' if hit['blue_hit'] else '✗'}, 共 {hit['total_hits']} 个")
