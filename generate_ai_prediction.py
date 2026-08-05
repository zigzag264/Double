# -*- coding: utf-8 -*-
"""
双色球 AI 预测自动生成脚本
自动调用 AI 模型生成下期预测数据
"""

import json
import os
import sys
import time as time_module
from datetime import datetime, timedelta
from openai import OpenAI
from openai import (
    APITimeoutError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
    AuthenticationError,
    NotFoundError,
    BadRequestError,
)
from typing import Dict, Any, Optional

# ==================== 配置区 ====================
# API 配置（通过环境变量设置）
BASE_URL = os.environ.get("AI_BASE_URL")
API_KEY = os.environ.get("AI_API_KEY")
if not API_KEY:
    print("❌ 请设置环境变量 AI_API_KEY")
    sys.exit(1)
if not BASE_URL:
    print("❌ 请设置环境变量 AI_BASE_URL")
    sys.exit(1)

# 模型配置列表（8 个模型共用同一套 API 凭证）
# 每模型可单独配置：streaming 支持、超时、温度、重试次数
MODELS = [
    {
        "id": "deepseek-v3",
        "name": "DeepSeek V3",
        "model_id": "deepseek-v3",
        "supports_streaming": True,
        "timeout": 180,
        "temperature": 0.8,
        "max_retries": 2,
    },
    {
        "id": "deepseek-v3.2-exp",
        "name": "DeepSeek V3.2 Exp",
        "model_id": "deepseek-v3.2-exp",
        "supports_streaming": True,
        "timeout": 180,
        "temperature": 0.8,
        "max_retries": 2,
    },
    {
        "id": "qwen3.5-122b-a10b",
        "name": "Qwen 3.5 122B",
        "model_id": "qwen3.5-122b-a10b",
        "supports_streaming": True,
        "timeout": 240,
        "temperature": 0.7,
        "max_retries": 2,
    },
    {
    {
        "id": "tongyi-xiaomi-analysis-pro",
        "name": "Tongyi Analysis Pro",
        "model_id": "tongyi-xiaomi-analysis-pro",
        "supports_streaming": True,
        "timeout": 240,
        "temperature": 0.8,
        "max_retries": 2,
    },
    {
        "id": "Moonshot-Kimi-K2-Instruct",
        "name": "Kimi K2",
        "model_id": "Moonshot-Kimi-K2-Instruct",
        "supports_streaming": True,
        "timeout": 180,
        "temperature": 0.8,
        "max_retries": 2,
    },
]

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOTTERY_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "lottery_history.json")
AI_PREDICTIONS_FILE = os.path.join(SCRIPT_DIR, "data", "ai_predictions.json")
PREDICTIONS_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "predictions_history.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "doc", "prompt2.0.md")

# ==================== 工具函数 ====================

def load_prompt_template() -> str:
    """加载 Prompt 模板文件"""
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ 加载 Prompt 文件失败: {str(e)}")
        raise

def load_lottery_history() -> Dict[str, Any]:
    """加载历史开奖数据"""
    try:
        with open(LOTTERY_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载历史数据失败: {str(e)}")
        raise

def get_next_draw_date() -> str:
    """
    根据双色球开奖规则（每周二、四、日 21:15）计算下期开奖日期
    返回 YYYY-MM-DD 格式
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日

    # 开奖日: 周二(1), 周四(3), 周日(6)
    draw_weekdays = [1, 3, 6]

    # 如果今天是开奖日且未到开奖时间(21:15)，则预测今天
    if weekday in draw_weekdays:
        draw_time = today.replace(hour=21, minute=15, second=0, microsecond=0)
        if today < draw_time:
            return today.strftime("%Y-%m-%d")

    # 否则找下一个开奖日
    for days_ahead in range(1, 8):
        future_date = today + timedelta(days=days_ahead)
        if future_date.weekday() in draw_weekdays:
            return future_date.strftime("%Y-%m-%d")

    # 理论上不会到这里
    return today.strftime("%Y-%m-%d")

def get_openai_client(default_timeout: int = 120) -> OpenAI:
    """获取 OpenAI 客户端"""
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=default_timeout, max_retries=0)

def extract_json_from_response(response_text: str) -> str:
    """从 AI 响应中提取 JSON 内容"""
    # 去除可能的 markdown 标记
    text = response_text.strip()

    # 如果有 ```json 标记，提取中间的内容
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    return text

# ==================== 模型调用核心 ====================

def _build_messages(prompt: str) -> list:
    """构建统一的 messages 列表"""
    return [
        {
            "role": "system",
            "content": "你是一个专业的彩票数据分析师，擅长基于历史数据进行模式分析和预测。请严格按照要求返回 JSON 格式数据，不要有任何额外的解释或说明。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]


def _call_with_streaming(client: OpenAI, model_config: dict, prompt: str) -> str:
    """流式模式调用，返回完整响应文本"""
    timeout = model_config.get("timeout", 120)
    response_text = ""

    stream = client.chat.completions.create(
        model=model_config["id"],
        messages=_build_messages(prompt),
        temperature=model_config.get("temperature", 0.8),
        stream=True,
        timeout=timeout + 60,  # 流式较慢，额外加 60s
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            response_text += delta.content

    return response_text.strip()


def _call_without_streaming(client: OpenAI, model_config: dict, prompt: str) -> str:
    """非流式模式调用，返回完整响应文本"""
    timeout = model_config.get("timeout", 120)

    response = client.chat.completions.create(
        model=model_config["id"],
        messages=_build_messages(prompt),
        temperature=model_config.get("temperature", 0.8),
        stream=False,
        timeout=timeout,
    )

    return response.choices[0].message.content.strip()


def _is_retryable_error(e: Exception) -> bool:
    """判断错误是否可重试"""
    return isinstance(e, (APITimeoutError, RateLimitError, APIConnectionError, InternalServerError))


def _is_skip_error(e: Exception) -> bool:
    """判断错误是否应跳过（不重试）"""
    return isinstance(e, (AuthenticationError, NotFoundError, BadRequestError))


def _parse_prediction(response_text: str, model_name: str) -> Dict[str, Any]:
    """从响应文本中提取并解析 JSON 预测数据"""
    json_text = extract_json_from_response(response_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"    ❌ {model_name} JSON 解析失败: {e}")
        print(f"    原始响应前500字符:\n{response_text[:500]}")
        raise


def call_ai_model(client: OpenAI, model_config: dict, prompt: str) -> Optional[Dict[str, Any]]:
    """
    调用 AI 模型获取预测（带自动流式回退 + 重试）

    流程：
      1. 若模型支持 streaming → 尝试流式调用
      2. 流式失败 → 自动回退到非流式
      3. 对可重试错误（超时/限流/断连/500）进行重试
      4. 对不可重试错误（认证/模型不存在/参数错误）直接跳过
    """
    model_name = model_config["name"]
    max_retries = model_config.get("max_retries", 2)

    # ---- 尝试流式调用 ----
    if model_config.get("supports_streaming", True):
        for attempt in range(max_retries + 1):
            try:
                t0 = time_module.time()
                response_text = _call_with_streaming(client, model_config, prompt)
                elapsed = time_module.time() - t0
                prediction = _parse_prediction(response_text, model_name)
                print(f"    ✅ 流式成功 | 耗时: {elapsed:.1f}s | 响应: {len(response_text)} 字符")
                return prediction

            except json.JSONDecodeError:
                # JSON 解析失败不可重试
                return None
            except Exception as e:
                if _is_skip_error(e):
                    print(f"    ❌ 流式调用失败 (不可恢复): {type(e).__name__}")
                    print(f"       {e}")
                    break  # 不再尝试流式，进入非流式回退
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"    ⚠️ 流式调用失败 (第{attempt+1}次): {type(e).__name__}")
                    print(f"       {e}")
                    print(f"    ℹ️  等待 {wait}s 后重试...")
                    time_module.sleep(wait)
                else:
                    print(f"    ❌ 流式调用失败 ({max_retries+1}次均失败): {type(e).__name__}")
                    print(f"       {e}")

        # 流式全部失败 → 回退到非流式
        print(f"    ℹ️  回退到非流式模式...")

    # ---- 非流式调用 ----
    for attempt in range(max_retries + 1):
        try:
            t0 = time_module.time()
            response_text = _call_without_streaming(client, model_config, prompt)
            elapsed = time_module.time() - t0
            prediction = _parse_prediction(response_text, model_name)
            print(f"    ✅ 非流式成功 | 耗时: {elapsed:.1f}s | 响应: {len(response_text)} 字符")
            return prediction

        except json.JSONDecodeError:
            return None
        except Exception as e:
            if _is_skip_error(e):
                print(f"    ❌ 非流式调用失败 (不可恢复): {type(e).__name__}")
                print(f"       {e}")
                return None
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"    ⚠️ 非流式调用失败 (第{attempt+1}次): {type(e).__name__}")
                print(f"       {e}")
                print(f"    ℹ️  等待 {wait}s 后重试...")
                time_module.sleep(wait)
            else:
                print(f"    ❌ 非流式调用失败 ({max_retries+1}次均失败): {type(e).__name__}")
                print(f"       {e}")
                return None

def validate_prediction(prediction: Dict[str, Any]) -> bool:
    """验证预测数据格式"""
    try:
        # 检查必需字段
        required_fields = ["prediction_date", "target_period", "model_id", "model_name", "predictions"]
        for field in required_fields:
            if field not in prediction:
                print(f"    ⚠️  缺少字段: {field}")
                return False

        # 检查预测组数量（应4组，不含冷号策略）
        if len(prediction["predictions"]) != 4:
            print(f"    ⚠️  预测组数量不正确: {len(prediction['predictions'])}（应为4组）")
            return False

        # 检查每组预测
        for group in prediction["predictions"]:
            # 检查红球
            if len(group["red_balls"]) != 6:
                print(f"    ⚠️  红球数量不正确: {len(group['red_balls'])}")
                return False

            # 检查红球是否排序
            sorted_reds = sorted(group["red_balls"])
            if group["red_balls"] != sorted_reds:
                print(f"    ⚠️  红球未排序: {group['red_balls']}")
                return False

            # 检查蓝球
            if not group["blue_ball"]:
                print(f"    ⚠️  蓝球为空")
                return False

        return True

    except Exception as e:
        print(f"    ⚠️  验证出错: {str(e)}")
        return False

def generate_predictions() -> Dict[str, Any]:
    """生成所有模型的预测"""
    print("\n" + "="*50)
    print("🤖 双色球 AI 预测自动生成")
    print("="*50 + "\n")

    # 加载 Prompt 模板
    print("📄 加载 Prompt 模板...")
    try:
        prompt_template = load_prompt_template()
        print(f"  ✓ Prompt 模板加载成功 ({len(prompt_template)} 字符)\n")
    except Exception as e:
        print(f"  ✗ Prompt 模板加载失败: {str(e)}\n")
        return None

    # 加载历史数据
    print("📊 加载历史开奖数据...")
    lottery_data = load_lottery_history()

    # 归档旧预测（如果已开奖）
    archive_old_prediction(lottery_data)

    # 获取下期信息
    next_draw = lottery_data.get("next_draw", {})
    target_period = next_draw.get("next_period", "")
    target_date = next_draw.get("next_date_display", "")

    if not target_period:
        print("❌ 无法获取下期期号信息")
        return None

    print(f"🎯 目标期号: {target_period}")
    print(f"📅 开奖日期: {target_date}")
    print(f"📝 历史数据: 最近 {len(lottery_data.get('data', []))} 期\n")

    # 准备历史数据（最近30期）
    history_data = lottery_data.get("data", [])[:30]
    history_json = json.dumps(history_data, ensure_ascii=False, indent=2)

    # 预测日期：根据开奖规则计算下期开奖日期
    prediction_date = get_next_draw_date()
    print(f"📅 预测日期: {prediction_date}\n")

    # 初始化 OpenAI 客户端
    client = get_openai_client(default_timeout=120)

    # 存储所有模型的预测和诊断信息
    all_predictions = []
    diagnostics = []  # 每个模型一条诊断记录

    # 逐个调用模型
    print("🔮 开始生成预测...\n")
    for model_config in MODELS:
        model_name = model_config["name"]
        t_start = time_module.time()
        status = "❌ 失败"
        detail = ""

        try:
            # 构建 prompt
            prompt = prompt_template.format(
                target_period=target_period,
                target_date=target_date,
                lottery_history=history_json,
                prediction_date=prediction_date,
                model_id=model_config['model_id'],
                model_name=model_config['name']
            )

            # 调用模型
            prediction = call_ai_model(client, model_config, prompt)

            if prediction is None:
                detail = "调用失败或解析失败"
                print(f"  ✗ {model_name}: {detail}\n")
            elif validate_prediction(prediction):
                all_predictions.append(prediction)
                status = "✅ 成功"
                detail = "验证通过"
                print(f"  ✓ {model_name}: 验证通过\n")
            else:
                detail = "验证失败（格式不正确）"
                print(f"  ✗ {model_name}: {detail}\n")

        except Exception as e:
            detail = f"{type(e).__name__}: {str(e)}"
            print(f"  ✗ 处理 {model_name} 时异常: {detail}\n")

        elapsed = time_module.time() - t_start
        diagnostics.append({
            "name": model_name,
            "model_id": model_config["model_id"],
            "status": "✅ 成功" if status == "✅ 成功" else "❌ 失败",
            "detail": detail if detail else "成功",
            "elapsed": elapsed,
        })

    # 打印诊断汇总表
    print("\n" + "=" * 60)
    print("📊 模型调用诊断汇总")
    print("=" * 60)
    for d in diagnostics:
        elapsed_str = f"{d['elapsed']:.1f}s" if d['elapsed'] < 60 else f"{d['elapsed']/60:.1f}min"
        print(f"  {d['status']} | {d['name']:<8s} | {elapsed_str:>7s} | {d['detail']}")
    print("=" * 60)
    print(f"  总计: {sum(1 for d in diagnostics if d['status'] == '✅ 成功')}/{len(diagnostics)} 个模型成功\n")

    # 构建最终输出
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

def calculate_hit_result(prediction_group: Dict[str, Any], actual_result: Dict[str, Any]) -> Dict[str, Any]:
    """计算单组预测的命中结果"""
    red_hits = [b for b in prediction_group["red_balls"] if b in actual_result["red_balls"]]
    blue_hit = prediction_group["blue_ball"] == actual_result["blue_ball"]

    return {
        "red_hits": red_hits,
        "red_hit_count": len(red_hits),
        "blue_hit": blue_hit,
        "total_hits": len(red_hits) + (1 if blue_hit else 0)
    }

def archive_old_prediction(lottery_data: Dict[str, Any]):
    """将旧预测归档到历史记录（如果已开奖）"""
    try:
        # 检查是否存在旧预测文件
        if not os.path.exists(AI_PREDICTIONS_FILE):
            print("  ℹ️  没有旧预测需要归档\n")
            return

        # 读取旧预测
        with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            old_predictions = json.load(f)

        old_target_period = old_predictions.get("target_period")
        if not old_target_period:
            print("  ⚠️  旧预测文件格式异常，跳过归档\n")
            return

        # 检查该期号是否已开奖
        latest_period = lottery_data.get("data", [{}])[0].get("period")
        if not latest_period or int(old_target_period) > int(latest_period):
            print(f"  ℹ️  旧预测期号 {old_target_period} 尚未开奖，无需归档\n")
            return

        print(f"  📦 旧预测期号 {old_target_period} 已开奖，开始归档...")

        # 查找实际开奖结果
        actual_result = None
        for draw in lottery_data.get("data", []):
            if draw.get("period") == old_target_period:
                actual_result = draw
                break

        if not actual_result:
            print(f"  ⚠️  找不到期号 {old_target_period} 的开奖结果，跳过归档\n")
            return

        # 读取历史记录文件
        history_data = {"predictions_history": []}
        if os.path.exists(PREDICTIONS_HISTORY_FILE):
            with open(PREDICTIONS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

        # 检查该期号是否已存在
        existing_record = next((r for r in history_data["predictions_history"]
                               if r["target_period"] == old_target_period), None)

        if existing_record:
            print(f"  ℹ️  期号 {old_target_period} 已存在于历史记录中\n")
            return

        # 为每个模型计算命中结果
        models_with_hits = []
        for model_data in old_predictions.get("models", []):
            # 为每组预测计算命中
            predictions_with_hits = []
            for pred_group in model_data.get("predictions", []):
                pred_with_hit = pred_group.copy()
                pred_with_hit["hit_result"] = calculate_hit_result(pred_group, actual_result)
                predictions_with_hits.append(pred_with_hit)

            # 找出最佳预测组
            best_pred = max(predictions_with_hits, key=lambda p: p["hit_result"]["total_hits"])

            models_with_hits.append({
                "model_id": model_data.get("model_id"),
                "model_name": model_data.get("model_name"),
                "predictions": predictions_with_hits,
                "best_group": best_pred["group_id"],
                "best_hit_count": best_pred["hit_result"]["total_hits"]
            })

        # 创建新的历史记录
        new_record = {
            "prediction_date": old_predictions.get("prediction_date"),
            "target_period": old_target_period,
            "actual_result": actual_result,
            "models": models_with_hits
        }

        # 插入到历史记录顶部
        history_data["predictions_history"].insert(0, new_record)

        # 保存历史记录
        with open(PREDICTIONS_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已将期号 {old_target_period} 的预测归档到历史记录")
        print(f"  📊 归档模型数: {len(models_with_hits)}\n")

    except Exception as e:
        print(f"  ⚠️  归档旧预测时出错: {str(e)}")
        print(f"  继续生成新预测...\n")

def save_predictions(predictions: Dict[str, Any]):
    """保存预测数据到文件"""
    try:
        print("💾 保存预测数据...")

        # 创建备份
        if os.path.exists(AI_PREDICTIONS_FILE):
            backup_file = AI_PREDICTIONS_FILE.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已创建备份: {os.path.basename(backup_file)}")

        # 保存新预测
        with open(AI_PREDICTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)

        print(f"  ✓ 已保存到: {AI_PREDICTIONS_FILE}\n")

    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        # 生成预测
        predictions = generate_predictions()

        if predictions:
            # 保存预测
            save_predictions(predictions)

            print("="*50)
            print("🎉 预测生成完成！")
            print("="*50 + "\n")

            # 显示预测摘要
            print("📋 预测摘要:")
            print(f"  期号: {predictions['target_period']}")
            print(f"  日期: {predictions['prediction_date']}")
            print(f"  模型数量: {len(predictions['models'])}")
            for model in predictions['models']:
                print(f"    - {model['model_name']}")
            print()
        else:
            print("❌ 预测生成失败")

    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        raise

if __name__ == "__main__":
    main()
