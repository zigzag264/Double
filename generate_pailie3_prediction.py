# -*- coding: utf-8 -*-
"""
排列三 AI 预测自动生成脚本
自动调用 AI 模型生成下期排列三预测数据
"""

import json
import os
import sys
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, Any

# ==================== 配置区 ====================
BASE_URL = os.environ.get("AI_BASE_URL") or "https://token.sensenova.cn/v1"
API_KEY = os.environ.get("AI_API_KEY")
if not API_KEY:
    print("❌ 请设置环境变量 AI_API_KEY")
    sys.exit(1)

# 模型配置列表
MODELS = [
    {"id": "sensenova-6.7-flash-lite", "name": "SenseNova 6.7 Flash-Lite", "model_id": "SenseNova6.7Flash"},
    {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "model_id": "DeepSeekV4"}
]

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAILIE3_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "pailie3_history.json")
PAILIE3_PREDICTIONS_FILE = os.path.join(SCRIPT_DIR, "data", "pailie3_predictions.json")
PAILIE3_HISTORY_PREDICTIONS_FILE = os.path.join(SCRIPT_DIR, "data", "pailie3_predictions_history.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "doc", "prompt_pailie3.md")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ 加载 Prompt 文件失败: {str(e)}")
        raise


def load_pailie3_history() -> Dict[str, Any]:
    try:
        with open(PAILIE3_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载历史数据失败: {str(e)}")
        raise


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def extract_json_from_response(response_text: str) -> str:
    text = response_text.strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()
    return text


def call_ai_model(client: OpenAI, model_config: Dict[str, str], prompt: str) -> Dict[str, Any]:
    try:
        print(f"  ⏳ 正在调用 {model_config['name']} 模型...")
        response = client.chat.completions.create(
            model=model_config['id'],
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的彩票数据分析师，擅长基于历史数据进行模式分析和预测。请严格按照要求返回 JSON 格式数据，不要有任何额外的解释或说明。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8
        )
        response_text = response.choices[0].message.content.strip()
        json_text = extract_json_from_response(response_text)
        prediction_data = json.loads(json_text)
        print(f"  ✅ {model_config['name']} 预测成功")
        return prediction_data
    except json.JSONDecodeError as e:
        print(f"  ❌ {model_config['name']} JSON 解析失败: {str(e)}")
        print(f"  原始响应前500字符:\n{response_text[:500]}")
        raise
    except Exception as e:
        print(f"  ❌ {model_config['name']} 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        import traceback
        print(f"  详细堆栈:\n{traceback.format_exc()}")
        raise


def validate_prediction(prediction: Dict[str, Any]) -> bool:
    try:
        required_fields = ["prediction_date", "target_period", "model_id", "model_name", "predictions"]
        for field in required_fields:
            if field not in prediction:
                print(f"    ⚠️  缺少字段: {field}")
                return False
        if len(prediction["predictions"]) != 5:
            print(f"    ⚠️  预测组数量不正确: {len(prediction['predictions'])}")
            return False
        for group in prediction["predictions"]:
            result = group.get("result", "")
            if not result or len(result) != 3:
                print(f"    ⚠️  开奖号码格式不正确: {result}")
                return False
            try:
                digits = [int(c) for c in result]
                if not all(0 <= d <= 9 for d in digits):
                    print(f"    ⚠️  数字超出范围: {result}")
                    return False
            except ValueError:
                print(f"    ⚠️  包含非数字字符: {result}")
                return False
        return True
    except Exception as e:
        print(f"    ⚠️  验证出错: {str(e)}")
        return False


def calculate_hit_result(prediction_result: str, actual_result: str) -> Dict[str, Any]:
    pred_digits = list(prediction_result)
    actual_digits = list(actual_result)

    # 直选命中
    exact_match = pred_digits == actual_digits
    # 位置命中数
    position_hits = sum(1 for p, a in zip(pred_digits, actual_digits) if p == a)
    # 数字命中（不区分位置）
    pred_set = set(pred_digits)
    actual_set = set(actual_digits)
    digit_hits = len(pred_set & actual_set)
    # 组选三/六判断
    pred_unique = len(set(pred_digits))
    actual_unique = len(set(actual_digits))

    return {
        "pred_digits": pred_digits,
        "exact_match": exact_match,
        "position_hits": position_hits,
        "digit_hits": digit_hits,
        "pred_unique": pred_unique,
        "actual_unique": actual_unique,
        "total_hits": position_hits
    }


def archive_old_prediction(pailie3_data: Dict[str, Any]):
    try:
        if not os.path.exists(PAILIE3_PREDICTIONS_FILE):
            print("  ℹ️  没有旧预测需要归档\n")
            return

        with open(PAILIE3_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            old_predictions = json.load(f)

        old_target_period = old_predictions.get("target_period")
        if not old_target_period:
            print("  ⚠️  旧预测文件格式异常，跳过归档\n")
            return

        latest_period = pailie3_data.get("data", [{}])[0].get("period")
        if not latest_period or int(old_target_period) > int(latest_period):
            print(f"  ℹ️  旧预测期号 {old_target_period} 尚未开奖，无需归档\n")
            return

        print(f"  📦 旧预测期号 {old_target_period} 已开奖，开始归档...")

        actual_result = None
        for draw in pailie3_data.get("data", []):
            if draw.get("period") == old_target_period:
                actual_result = draw
                break

        if not actual_result:
            print(f"  ⚠️  找不到期号 {old_target_period} 的开奖结果，跳过归档\n")
            return

        history_data = {"predictions_history": []}
        if os.path.exists(PAILIE3_HISTORY_PREDICTIONS_FILE):
            with open(PAILIE3_HISTORY_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

        existing_record = next((r for r in history_data["predictions_history"]
                               if r["target_period"] == old_target_period), None)
        if existing_record:
            print(f"  ℹ️  期号 {old_target_period} 已存在于历史记录中\n")
            return

        models_with_hits = []
        for model_data in old_predictions.get("models", []):
            predictions_with_hits = []
            for pred_group in model_data.get("predictions", []):
                pred_with_hit = pred_group.copy()
                pred_with_hit["hit_result"] = calculate_hit_result(
                    pred_group.get("result", ""), actual_result.get("result", ""))
                predictions_with_hits.append(pred_with_hit)

            best_pred = max(predictions_with_hits, key=lambda p: p["hit_result"]["total_hits"])
            models_with_hits.append({
                "model_id": model_data.get("model_id"),
                "model_name": model_data.get("model_name"),
                "predictions": predictions_with_hits,
                "best_group": best_pred["group_id"],
                "best_hit_count": best_pred["hit_result"]["total_hits"]
            })

        new_record = {
            "prediction_date": old_predictions.get("prediction_date"),
            "target_period": old_target_period,
            "actual_result": actual_result,
            "models": models_with_hits
        }

        history_data["predictions_history"].insert(0, new_record)

        with open(PAILIE3_HISTORY_PREDICTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已将期号 {old_target_period} 的预测归档到历史记录")
        print(f"  📊 归档模型数: {len(models_with_hits)}\n")

    except Exception as e:
        print(f"  ⚠️  归档旧预测时出错: {str(e)}")
        print(f"  继续生成新预测...\n")


def save_predictions(predictions: Dict[str, Any]):
    try:
        print("💾 保存预测数据...")

        if os.path.exists(PAILIE3_PREDICTIONS_FILE):
            backup_file = PAILIE3_PREDICTIONS_FILE.replace(".json",
                f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(PAILIE3_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已创建备份: {os.path.basename(backup_file)}")

        with open(PAILIE3_PREDICTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)

        print(f"  ✓ 已保存到: {PAILIE3_PREDICTIONS_FILE}\n")

    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")
        raise


def generate_predictions() -> Dict[str, Any]:
    print("\n" + "="*50)
    print("🤖 排列三 AI 预测自动生成")
    print("="*50 + "\n")

    print("📄 加载 Prompt 模板...")
    try:
        prompt_template = load_prompt_template()
        print(f"  ✓ Prompt 模板加载成功 ({len(prompt_template)} 字符)\n")
    except Exception as e:
        print(f"  ✗ Prompt 模板加载失败: {str(e)}\n")
        return None

    print("📊 加载历史开奖数据...")
    pailie3_data = load_pailie3_history()
    archive_old_prediction(pailie3_data)

    next_draw = pailie3_data.get("next_draw", {})
    target_period = next_draw.get("next_period", "")
    target_date = next_draw.get("next_date_display", "")

    if not target_period:
        print("❌ 无法获取下期期号信息")
        return None

    print(f"🎯 目标期号: {target_period}")
    print(f"📅 开奖日期: {target_date}")
    print(f"📝 历史数据: 最近 {len(pailie3_data.get('data', []))} 期\n")

    history_data = pailie3_data.get("data", [])[:30]
    history_json = json.dumps(history_data, ensure_ascii=False, indent=2)
    prediction_date = datetime.now().strftime("%Y-%m-%d")
    print(f"📅 预测日期: {prediction_date}\n")

    client = get_openai_client()
    all_predictions = []

    print("🔮 开始生成预测...\n")
    for model_config in MODELS:
        try:
            prompt = prompt_template.format(
                target_period=target_period,
                target_date=target_date,
                lottery_history=history_json,
                prediction_date=prediction_date,
                model_id=model_config['model_id'],
                model_name=model_config['name']
            )
            prediction = call_ai_model(client, model_config, prompt)
            if validate_prediction(prediction):
                all_predictions.append(prediction)
                print(f"  ✓ 验证通过\n")
            else:
                print(f"  ✗ 验证失败，跳过该模型\n")
        except Exception as e:
            print(f"  ✗ 处理 {model_config['name']} 时失败")
            print(f"  错误类型: {type(e).__name__}")
            print(f"  错误信息: {str(e)}\n")
            continue

    if not all_predictions:
        print("❌ 没有成功生成任何预测")
        return None

    result = {
        "prediction_date": prediction_date,
        "target_period": target_period,
        "models": all_predictions
    }

    print(f"✅ 成功生成 {len(all_predictions)}/{len(MODELS)} 个模型的预测\n")
    return result


def main():
    try:
        predictions = generate_predictions()
        if predictions:
            save_predictions(predictions)
            print("="*50)
            print("🎉 预测生成完成！")
            print("="*50 + "\n")
            print("📋 预测摘要:")
            print(f"  期号: {predictions['target_period']}")
            print(f"  日期: {predictions['prediction_date']}")
            print(f"  模型数量: {len(predictions['models'])}")
            for model in predictions['models']:
                print(f"    - {model['model_name']}")
                for p in model['predictions']:
                    print(f"      G{p['group_id']} [{p['strategy']}]: {p['result']}")
            print()
        else:
            print("❌ 预测生成失败")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        raise


if __name__ == "__main__":
    main()
