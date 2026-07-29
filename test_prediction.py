#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 AI 预测脚本功能"""

import json
import os

def test_prediction_file():
    """测试预测文件格式"""
    print("=" * 50)
    print("测试 AI 预测数据文件")
    print("=" * 50 + "\n")
    
    try:
        with open("data/ai_predictions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 基本字段检查
        assert "prediction_date" in data, "缺少 prediction_date 字段"
        assert "target_period" in data, "缺少 target_period 字段"
        assert "models" in data, "缺少 models 字段"
        
        print(f"✅ 基本字段完整")
        print(f"   预测日期: {data['prediction_date']}")
        print(f"   目标期号: {data['target_period']}\n")
        
        # 模型数量检查
        models = data["models"]
        print(f"✅ 模型数量: {len(models)}")
        
        # 检查每个模型
        for model in models:
            model_name = model.get("model_name", "未知")
            predictions = model.get("predictions", [])
            
            # 检查预测组数量
            assert len(predictions) == 5, f"{model_name} 预测组数量不正确: {len(predictions)}"
            
            # 检查每组预测
            for pred in predictions:
                red_balls = pred.get("red_balls", [])
                blue_ball = pred.get("blue_ball")
                
                # 红球检查
                assert len(red_balls) == 6, f"{model_name} 红球数量不正确"
                assert red_balls == sorted(red_balls), f"{model_name} 红球未排序"
                
                # 蓝球检查
                assert blue_ball, f"{model_name} 蓝球为空"
            
            print(f"   ✓ {model_name}: 5 组预测，格式正确")
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    test_prediction_file()
