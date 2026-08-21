# -*- coding: utf-8 -*-
"""
双色球 统计模型预测自动生成脚本
自动调用本地统计/概率/机器学习模型生成下期预测数据

说明：现仅由 stats_models.py 的 10 个纯标准库统计模型生成预测，
不调用 API、不消耗 token。
"""

import json
import os
from datetime import datetime

from typing import Dict, Any

from stats_models import generate_stats_predictions

# ==================== 配置区 ====================
# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOTTERY_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "lottery_history.json")
AI_PREDICTIONS_FILE = os.path.join(SCRIPT_DIR, "data", "ai_predictions.json")
PREDICTIONS_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "predictions_history.json")

# ==================== 工具函数 ====================

def _dump_json(obj) -> str:
    """紧凑 JSON（无缩进）序列化，用于落盘的数据文件。

    相比 indent=2 可减小 30%~50% 体积，减少 git 体积、传输与首屏 parse 成本。
    归档备份与部署文件统一使用此格式。
    """
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def _write_json_file(path: str, obj) -> None:
    """以紧凑格式写入 JSON 文件。"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(_dump_json(obj))


def load_lottery_history() -> Dict[str, Any]:
    """加载历史开奖数据"""
    try:
        with open(LOTTERY_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载历史数据失败: {str(e)}")
        raise


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
        seen_groups = set()
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

            # 检查红球范围（01-33）
            for b in group["red_balls"]:
                if not (b.isdigit() and 1 <= int(b) <= 33):
                    print(f"    ⚠️  红球超出范围: {b}")
                    return False

            # 检查蓝球是否为空
            if not group["blue_ball"]:
                print(f"    ⚠️  蓝球为空")
                return False

            # 检查蓝球范围（01-16）
            if not group["blue_ball"].isdigit() or not (1 <= int(group["blue_ball"]) <= 16):
                print(f"    ⚠️  蓝球超出范围: {group['blue_ball']}")
                return False

            # 检查重复组（红蓝完全相同）
            group_key = (tuple(group["red_balls"]), group["blue_ball"])
            if group_key in seen_groups:
                print(f"    ⚠️  存在完全重复的预测组: {group['red_balls']} + {group['blue_ball']}")
                return False
            seen_groups.add(group_key)

            # 检查红球数组内是否有重复号码
            if len(set(group["red_balls"])) != 6:
                print(f"    ⚠️  红球存在重复号码: {group['red_balls']}")
                return False

        # 检查 4 组策略名互不相同（防止同一模型输出重复策略名，导致排行期数虚增）
        strategies = [g.get("strategy", "") for g in prediction["predictions"]]
        if len(set(strategies)) != len(strategies):
            print(f"    ⚠️  策略名重复: {strategies}")
            return False

        return True

    except Exception as e:
        print(f"    ⚠️  验证出错: {str(e)}")
        return False


def generate_predictions() -> Dict[str, Any]:
    """生成统计模型的预测"""
    print("\n" + "="*50)
    print("📊 双色球统计模型预测自动生成")
    print("="*50 + "\n")

    # 加载历史数据
    print("📊 加载历史开奖数据...")
    lottery_data = load_lottery_history()

    # 归档旧预测（如果已开奖）
    archived = archive_old_prediction(lottery_data)

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

    # 预测日期：取历史数据最近更新日（last_updated 的日期部分）
    prediction_date = (lottery_data.get("last_updated", "") or "")[:10] or target_date
    print(f"📅 预测日期: {prediction_date}\n")

    all_predictions = []

    # ============ 生成统计/概率/机器学习模型预测（本地计算，不调用 API） ============
    print("=" * 50)
    print("📊 生成统计数学模型预测 (10 种)...")
    print("=" * 50)
    stats_predictions = []
    try:
        stats_predictions = generate_stats_predictions(
            target_period, prediction_date, lottery_data.get("data", []))
    except Exception as e:
        print(f"  ⚠️  统计模型生成异常: {type(e).__name__}: {e}")

    if stats_predictions:
        # 先做去重/防复读后处理，再严格校验格式
        valid_stats = []
        for sm in stats_predictions:
            sm = post_process_prediction(sm, lottery_data.get("data", []))
            if validate_prediction(sm):
                valid_stats.append(sm)
        all_predictions.extend(valid_stats)
        names = "、".join(sm["model_name"] for sm in valid_stats)
        print(f"  ✓ 统计模型通过校验 {len(valid_stats)}/{len(stats_predictions)} 个: {names}\n")
    else:
        print("  ⚠️  统计模型预测为空（历史数据不足），跳过\n")

    # 构建最终输出
    if not all_predictions:
        print("❌ 没有成功生成任何预测")
        if archived:
            # 旧预测已归档但新预测失败，清空文件避免脏数据进入邮件推送
            print("  ℹ️  旧预测已被归档，正在清空 ai_predictions.json...")
            _clear_predictions_file()
        return None

    result = {
        "prediction_date": prediction_date,
        "target_period": target_period,
        "models": all_predictions
    }

    print(f"✅ 成功生成 {len(all_predictions)} 个统计模型的预测\n")
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

def _red_hits_between(group_reds: list, draw_reds: list) -> int:
    """计算两组红球的重合数"""
    return len(set(group_reds) & set(draw_reds))


def _repair_group(group: Dict[str, Any], recent_draws: list) -> Dict[str, Any]:
    """
    修复与近期开奖过于相似的预测组。
    将重合过多的红球替换为同区间内近期出现较少的号码。
    """
    # 找出最近3期开奖
    last3 = [d for d in recent_draws[:3] if isinstance(d, dict) and "red_balls" in d]
    if not last3:
        return group

    new_reds = list(group["red_balls"])
    new_blue = group["blue_ball"]

    # 检查红球：与任何一期重合 ≥5 则修复
    for draw in last3:
        hits = _red_hits_between(new_reds, draw["red_balls"])
        if hits >= 5:
            # 找出重合的号码
            overlap = [b for b in new_reds if b in draw["red_balls"]]
            # 替换 1-2 个重合号码
            replacements_needed = min(hits - 4, 2)  # 降到 4 重合以下
            for _ in range(replacements_needed):
                if not overlap:
                    break
                to_replace = overlap.pop(0)
                # 确定该号码所在的区间
                n = int(to_replace)
                if n <= 11:
                    candidates = [f"{i:02d}" for i in range(1, 12)]
                elif n <= 22:
                    candidates = [f"{i:02d}" for i in range(12, 23)]
                else:
                    candidates = [f"{i:02d}" for i in range(23, 34)]

                # 排除当前组已有的号码
                candidates = [c for c in candidates if c not in new_reds]
                # 排除近期开奖中该区间出现过的号码（避免换汤不换药）
                for d in last3:
                    candidates = [c for c in candidates if c not in d["red_balls"]]

                if candidates:
                    # 选区间内数值最接近的号码（保持风格相似但不重复）
                    candidates.sort(key=lambda c: abs(int(c) - n))
                    new_reds.remove(to_replace)
                    new_reds.append(candidates[0])

            new_reds.sort()

    # 检查蓝球：与最近3期任何一期蓝球相同则换一个
    if new_blue and any(new_blue == d.get("blue_ball", "") for d in last3):
        all_blue = [f"{i:02d}" for i in range(1, 17)]
        # 排除该模型其他组已用的蓝球（调用时传入的 group 可能不全，但先简单排除近期出现过的）
        used = {d.get("blue_ball", "") for d in last3}
        available = [b for b in all_blue if b not in used and b != new_blue]
        if available:
            # 选数值最接近的
            target = int(new_blue)
            available.sort(key=lambda b: abs(int(b) - target))
            new_blue = available[0]

    return {
        "group_id": group["group_id"],
        "strategy": group["strategy"],
        "red_balls": new_reds,
        "blue_ball": new_blue,
        "description": group.get("description", "")
    }


def _normalize_balls(prediction: Dict[str, Any]) -> None:
    """将合法红蓝球规整为 2 位零填充字符串、红球按数值升序排列（原地修改）。

    统一规整后，去重键、字典序排序校验、归档时的命中比对（按原字符串相等）
    才一致可靠。非法号码原样保留，交由 validate_prediction 拒绝，避免在此处
    静默吞掉格式错误。
    """
    for g in prediction.get("predictions", []):
        reds = g.get("red_balls", [])
        normalized = []
        for b in reds:
            if isinstance(b, str) and b.isdigit() and 1 <= int(b) <= 33:
                normalized.append(f"{int(b):02d}")
            else:
                normalized.append(b)
        # 全为 2 位零填充串时字典序即数值序；混入非法值时该模型会被 validate 拒绝，排序无影响
        g["red_balls"] = sorted(normalized)
        blue = g.get("blue_ball")
        if isinstance(blue, str) and blue.isdigit() and 1 <= int(blue) <= 16:
            g["blue_ball"] = f"{int(blue):02d}"


def post_process_prediction(prediction: Dict[str, Any], history_data: list) -> Dict[str, Any]:
    """
    对模型预测进行后处理：
    0. 规整：红蓝球统一为 2 位零填充
    1. 去重：移除红蓝完全相同的重复组
    2. 防复读：修复与近期开奖太相似的组
    3. 补齐：确保总是 4 组
    """
    # 0. 规整号码格式（须在去重/排序/校验/归档之前）
    _normalize_balls(prediction)

    recent_draws = [d for d in history_data if isinstance(d, dict) and "red_balls" in d and "blue_ball" in d]

    # 1. 去重
    seen = set()
    unique_groups = []
    for g in prediction["predictions"]:
        key = (tuple(g["red_balls"]), g["blue_ball"])
        if key not in seen:
            seen.add(key)
            unique_groups.append(g)
        else:
            print(f"    ⚠️  发现重复组 (策略: {g['strategy']})，已移除")

    # 2. 防复读修复
    repaired = []
    for g in unique_groups:
        # 检查是否与最近3期过于相似
        needs_repair = False
        for draw in recent_draws[:3]:
            if _red_hits_between(g["red_balls"], draw["red_balls"]) >= 5:
                needs_repair = True
                print(f"    ⚠️  策略「{g['strategy']}」与 {draw.get('period', '?')} 期红球重合 ≥5，执行修复")
                break
        if needs_repair:
            repaired.append(_repair_group(g, recent_draws))
        else:
            repaired.append(g)

    # 3. 补齐到 4 组（如果去重后不足）
    # 补齐时使用备用策略名，确保不与现有组重复
    _FALLBACK_STRATEGIES = ["均值回归", "区间平衡", "奇偶优化", "跨度精选"]
    existing_strategies = {g["strategy"] for g in repaired}
    fallback_idx = 0
    while len(repaired) < 4:
        # 以最后一组为蓝本生成变体
        template = repaired[-1] if repaired else unique_groups[0]
        # 取一个不重复的备用策略名
        strategy_name = template["strategy"]
        while strategy_name in existing_strategies and fallback_idx < len(_FALLBACK_STRATEGIES):
            strategy_name = _FALLBACK_STRATEGIES[fallback_idx]
            fallback_idx += 1
        existing_strategies.add(strategy_name)
        variant = {
            "group_id": len(repaired) + 1,
            "strategy": strategy_name,
            "red_balls": list(template["red_balls"]),
            "blue_ball": template["blue_ball"],
        }
        # 交换红球中的两个不同区间号码
        reds = list(variant["red_balls"])
        # 找一个可替换的号码
        all_reds = [f"{i:02d}" for i in range(1, 34)]
        available = [r for r in all_reds if r not in reds]
        if available:
            # 替换第 (len(repaired) % 6) 个位置
            idx = len(repaired) % 6
            old = reds[idx]
            # 找同区间可用的
            n = int(old)
            if n <= 11:
                pool = [r for r in available if 1 <= int(r) <= 11]
            elif n <= 22:
                pool = [r for r in available if 12 <= int(r) <= 22]
            else:
                pool = [r for r in available if 23 <= int(r) <= 33]
            if pool:
                pool.sort(key=lambda r: abs(int(r) - n))
                reds[idx] = pool[0]
                reds.sort()
        variant["red_balls"] = reds
        variant["blue_ball"] = template["blue_ball"]
        variant["description"] = template.get("description", "")
        repaired.append(variant)
        print(f"    ⚠️  补齐第 {len(repaired)} 组预测")

    # 重新编号 group_id
    for i, g in enumerate(repaired):
        g["group_id"] = i + 1

    prediction["predictions"] = repaired
    return prediction


def archive_old_prediction(lottery_data: Dict[str, Any]) -> bool:
    """将旧预测归档到历史记录（如果已开奖）。返回是否成功归档。"""
    try:
        # 检查是否存在旧预测文件
        if not os.path.exists(AI_PREDICTIONS_FILE):
            print("  ℹ️  没有旧预测需要归档\n")
            return False

        # 读取旧预测
        with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            old_predictions = json.load(f)

        old_target_period = old_predictions.get("target_period")
        if not old_target_period:
            print("  ⚠️  旧预测文件格式异常，跳过归档\n")
            return False

        # 检查该期号是否已开奖
        latest_period = lottery_data.get("data", [{}])[0].get("period")
        if not latest_period or int(old_target_period) > int(latest_period):
            # 兜底检测：若预测日期已过去较久仍未见开奖，多半是爬虫未更新数据
            try:
                pred_date = datetime.strptime(old_predictions.get("prediction_date", ""), "%Y-%m-%d")
                days_passed = (datetime.now() - pred_date).days
            except Exception:
                days_passed = 0

            if days_passed >= 3:
                print(f"  ⚠️  旧预测期号 {old_target_period} 的预测日期已过去 {days_passed} 天仍未见开奖数据！")
                print(f"  ⚠️  最新期号仅到 {latest_period}，请先运行爬虫更新开奖数据 (fetch_history/fetch_lottery_history.py)")
                print(f"  ⚠️  否则该期预测将无法自动归档\n")
            else:
                print(f"  ℹ️  旧预测期号 {old_target_period} 尚未开奖，无需归档\n")
            return False

        print(f"  📦 旧预测期号 {old_target_period} 已开奖，开始归档...")

        # 查找实际开奖结果
        actual_result = None
        for draw in lottery_data.get("data", []):
            if draw.get("period") == old_target_period:
                actual_result = draw
                break

        if not actual_result:
            print(f"  ⚠️  找不到期号 {old_target_period} 的开奖结果，跳过归档\n")
            return False

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
            return False

        # 为每个模型计算命中结果
        models_with_hits = []
        for model_data in old_predictions.get("models", []):
            # 为每组预测计算命中
            predictions_with_hits = []
            for pred_group in model_data.get("predictions", []):
                pred_with_hit = pred_group.copy()
                pred_with_hit["hit_result"] = calculate_hit_result(pred_group, actual_result)
                predictions_with_hits.append(pred_with_hit)

            # 跳过没有预测组的模型，避免 max() 空序列崩溃导致整期归档失败
            if not predictions_with_hits:
                print(f"    ⚠️  模型 {model_data.get('model_id', '?')} 无预测组，跳过归档")
                continue

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

        # 保存历史记录（紧凑格式）
        _write_json_file(PREDICTIONS_HISTORY_FILE, history_data)

        print(f"  ✅ 已将期号 {old_target_period} 的预测归档到历史记录")
        print(f"  📊 归档模型数: {len(models_with_hits)}\n")
        return True

    except Exception as e:
        print(f"  ⚠️  归档旧预测时出错: {str(e)}")
        print(f"  继续生成新预测...\n")
        return False

def _clear_predictions_file():
    """清空当前预测文件（写入空结构），避免邮件推送展示过期货。"""
    empty = {
        "prediction_date": "",
        "target_period": "",
        "models": []
    }
    try:
        _write_json_file(AI_PREDICTIONS_FILE, empty)
        print(f"  ✓ 已清空 {os.path.basename(AI_PREDICTIONS_FILE)}")
    except Exception as e:
        print(f"  ⚠️  清空预测文件失败: {e}")

def _cleanup_archive_backups(archive_dir: str, prefix: str, keep: int = 10):
    """保留最近 keep 份指定前缀的归档备份，自动清理更旧的（避免备份无限堆积）"""
    try:
        backups = [f for f in os.listdir(archive_dir)
                   if f.startswith(prefix) and f.endswith('.json')]
        backups.sort(key=lambda f: os.path.getmtime(os.path.join(archive_dir, f)), reverse=True)
        for old in backups[keep:]:
            os.remove(os.path.join(archive_dir, old))
    except OSError:
        pass


def save_predictions(predictions: Dict[str, Any]):
    """保存预测数据到文件"""
    try:
        print("💾 保存预测数据...")

        # 创建备份（写入 archive 目录，仅保留最近 10 份）
        if os.path.exists(AI_PREDICTIONS_FILE):
            archive_dir = os.path.join(os.path.dirname(AI_PREDICTIONS_FILE), "archive")
            os.makedirs(archive_dir, exist_ok=True)
            backup_file = os.path.join(archive_dir, f"ai_predictions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            _write_json_file(backup_file, backup_data)
            print(f"  ✓ 已创建备份: {os.path.basename(backup_file)}")
            _cleanup_archive_backups(archive_dir, "ai_predictions_backup_", keep=10)

        # 保存新预测（紧凑格式）
        _write_json_file(AI_PREDICTIONS_FILE, predictions)

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
