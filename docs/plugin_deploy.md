# 插件部署（Coze 代码插件 · 云侧 IDE）

本仓库 `plugins/` 下三个插件是**纯函数**（带单测），Coze 自定义代码插件需要按平台固定签名重写——入口必须是 `def handler(args: Args[Input]) -> Output:`，**不是 `main`**。

每个插件在 Coze 里是**一个工具（Tool）**，工具名必须以字母/下划线开头（**用英文**，不要用中文）：

| 序号 | 工具英文名 | 用途 |
|---|---|---|
| 1 | `calc_annual_leave` | 年假天数计算 |
| 2 | `calc_overtime_pay` | 加班费计算 |
| 3 | `check_policy_validity` | 政策时效校验 |

---

## 通用操作步骤

1. **Coze 控制台 → 资源 → + 资源 → 插件 → 创建插件 → 云侧插件 → 在 Coze IDE 中创建 → Python3**。
2. 填「创建工具」弹窗：工具名称 = 上表英文名，介绍填中文。
3. 进 IDE 编辑器后，**把默认模板全删**，把下面对应插件代码整段粘贴。
4. 切「**元数据**」Tab，按「输入参数 / 输出参数」表逐条添加。
5. 切回「**代码**」Tab，点右上「试运行 / ▶ 运行」，用「测试样例」验证。
6. 验证通过 → 页面右上「**发布**」。

> ⚠️ 关键点：入口函数**必须是 `handler`**，且必须 `from runtime import Args` + `from typings.<工具名>.<工具名> import Input, Output`，读参用 `args.input.<字段名>`（不是 `args["..."]`）。

---

## 1. 年假计算（calc_annual_leave）

### 工具元数据

**描述**：
```
根据员工入职日期和当前日期，按中国《职工带薪年休假条例》计算应休带薪年假天数。
同年入职按剩余日历天数折算；工龄1-10年享5天、10-20年享10天、20年以上享15天；
工龄不足1年返回0天。
```

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `entry_date` | String | ✅ | 入职日期 `YYYY-MM-DD`（视作已具备年假资格的工龄起点）|
| `as_of` | String | ❌ | 计算基准日 `YYYY-MM-DD`，默认今天 |

**输出参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `eligible` | Boolean | 是否享受年假 |
| `base_days` | Number | 法定基础天数（0/5/10/15）|
| `days` | Number | 实际应休天数 |
| `service_years` | Number | 实际工龄 |
| `note` | String | 备注 |

### 完整代码

```python
from runtime import Args
from typings.calc_annual_leave.calc_annual_leave import Input, Output
from datetime import date


def _parse(d):
    return date.fromisoformat(d)


def handler(args: Args[Input]) -> Output:
    entry_date = args.input.entry_date
    as_of = args.input.as_of

    e = _parse(entry_date)
    a = _parse(as_of) if as_of else date.today()
    if e.year == a.year:
        remaining = (date(a.year, 12, 31) - e).days + 1
        return {
            "eligible": True,
            "base_days": 5,
            "days": int(remaining / 365 * 5),
            "service_years": 0,
            "note": f"入职当年按剩余日历天数折算（剩余{remaining}天）",
        }
    service = a.year - e.year - ((a.month, a.day) < (e.month, e.day))
    if service < 1:
        return {
            "eligible": False,
            "base_days": 0,
            "days": 0,
            "service_years": service,
            "note": "连续工作未满1年，不享受年休假",
        }
    base = 5 if service < 10 else (10 if service < 20 else 15)
    return {
        "eligible": True,
        "base_days": base,
        "days": base,
        "service_years": service,
        "note": "",
    }
```

### 测试样例（粘到「试运行」输入框）

- 输入：`{"entry_date":"2020-03-01","as_of":"2026-09-01"}` → `eligible=true, base_days=5, days=5, service_years=6, note=""`
- 输入：`{"entry_date":"2026-03-01","as_of":"2026-09-01"}` → `days=4`（入职当年折算）
- 输入：`{"entry_date":"2025-10-01","as_of":"2026-03-01"}` → `eligible=false, days=0`（未满1年）

---

## 2. 加班费计算（calc_overtime_pay）

### 工具元数据

**描述**：
```
根据时薪或月薪计算加班费。
加班类型=工作日 1.5倍、休息日 2倍（不能补休）、法定节假日 3倍。
月薪会自动按 21.75天/月、8小时/天 折算时薪。
```

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `hourly_base` | Number | ❌* | 时薪；与 `monthly_salary` 二选一 |
| `monthly_salary` | Number | ❌* | 月薪；填了自动折算时薪（÷21.75÷8）|
| `hours` | Number | ✅ | 加班小时数 |
| `ot_type` | String | ✅ | 加班类型，枚举：`工作日` / `休息日` / `法定节假日` |

\* `hourly_base` 与 `monthly_salary` 至少填一个；两个都给则优先用 `hourly_base`。

**输出参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `hourly_base` | Number | 实际使用的时薪 |
| `overtime_pay` | Number | 加班费金额 |

### 完整代码

```python
from runtime import Args
from typings.calc_overtime_pay.calc_overtime_pay import Input, Output


def monthly_to_hourly(monthly_salary):
    return round(monthly_salary / 21.75 / 8, 2)


def handler(args: Args[Input]) -> Output:
    hourly_base = args.input.hourly_base
    monthly_salary = args.input.monthly_salary
    hours = args.input.hours
    ot_type = args.input.ot_type

    if hourly_base is None and monthly_salary is not None:
        hourly_base = monthly_to_hourly(monthly_salary)

    factor = {"工作日": 1.5, "休息日": 2.0, "法定节假日": 3.0}
    if ot_type not in factor:
        raise ValueError("ot_type 必须为 工作日 / 休息日 / 法定节假日")
    if hourly_base is None:
        raise ValueError("hourly_base 与 monthly_salary 必须至少填一个")

    pay = round(hourly_base * hours * factor[ot_type], 2)
    return {"hourly_base": hourly_base, "overtime_pay": pay}
```

### 测试样例

- 输入：`{"hourly_base":30,"hours":8,"ot_type":"法定节假日"}` → `hourly_base=30.0, overtime_pay=720.0`
- 输入：`{"monthly_salary":8000,"hours":4,"ot_type":"休息日"}` → `hourly_base≈46.0, overtime_pay≈184.0`

---

## 3. 政策时效校验（check_policy_validity）

### 工具元数据

**描述**：
```
判断一条 HR 政策法规在指定基准日是否"现行有效"。
优先按"name"查内嵌法规注册表（包含《职工带薪年休假条例》《劳动法加班工资规定》）；
未匹配则按 effective_date / revoked_date 直接判断。
```

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | String | ❌* | 法规名称，从内嵌注册表里查（最方便）|
| `effective_date` | String | ❌* | 生效日期 `YYYY-MM-DD`（与 `name` 二选一）|
| `revoked_date` | String | ❌ | 废止日期 `YYYY-MM-DD` |
| `as_of` | String | ❌ | 判断基准日 `YYYY-MM-DD`，默认今天 |

\* 优先用 `name`；若没传 `name`，则必须传 `effective_date`。

**输出参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `status` | String | 状态：`现行有效` / `已废止` / `未生效` |
| `valid` | Boolean | 是否现行有效 |
| `name` | String | 法规名称（如按 name 查）|
| `effective_date` | String | 生效日期 |
| `revoked_date` | String | 废止日期（如有）|
| `summary` | String | 摘要（如按 name 查）|

### 完整代码

```python
from runtime import Args
from typings.check_policy_validity.check_policy_validity import Input, Output
from datetime import date


REGULATIONS = [
    {
        "name": "职工带薪年休假条例",
        "effective_date": "2008-01-01",
        "revoked_date": None,
        "summary": "职工连续工作1年以上享受带薪年休假，满1年5天、满10年10天、满20年15天。",
    },
    {
        "name": "劳动法加班工资规定",
        "effective_date": "1995-01-01",
        "revoked_date": None,
        "summary": "工作日加班不低于150%，休息日不能补休不低于200%，法定节假日不低于300%。",
    },
]


def _parse(d):
    return date.fromisoformat(d)


def check_validity(effective_date, revoked_date=None, as_of=None):
    e = _parse(effective_date)
    a = _parse(as_of) if as_of else date.today()
    r = _parse(revoked_date) if revoked_date else None
    if r and a > r:
        return {
            "status": "已废止", "valid": False,
            "effective_date": effective_date, "revoked_date": revoked_date,
        }
    if a < e:
        return {
            "status": "未生效", "valid": False,
            "effective_date": effective_date, "revoked_date": revoked_date,
        }
    return {
        "status": "现行有效", "valid": True,
        "effective_date": effective_date, "revoked_date": revoked_date,
    }


def check_by_name(name, as_of=None):
    for item in REGULATIONS:
        if item["name"] == name:
            res = check_validity(item["effective_date"], item.get("revoked_date"), as_of)
            res["name"] = name
            res["summary"] = item.get("summary", "")
            return res
    raise ValueError(f"注册表中未找到法规: {name}")


def handler(args: Args[Input]) -> Output:
    name = args.input.name
    effective_date = args.input.effective_date
    revoked_date = args.input.revoked_date
    as_of = args.input.as_of

    if name:
        return check_by_name(name, as_of)
    if not effective_date:
        raise ValueError("name 与 effective_date 必须至少填一个")
    return check_validity(effective_date, revoked_date, as_of)
```

### 测试样例

- 输入：`{"name":"职工带薪年休假条例"}` → `status="现行有效", valid=true`
- 输入：`{"name":"未知法规"}` → 抛错 `注册表中未找到法规: 未知法规`（在 Bot 里 Bot 会看到这条提示，正常）
- 输入：`{"effective_date":"2020-01-01","revoked_date":"2022-01-01","as_of":"2026-09-01"}` → `status="已废止", valid=false`

---

## 调试要点

- 「参数缺失」→ 检查元数据里的参数名是否和代码里 `args.input.<字段名>` 完全一致（区分大小写）。
- 「找不到模块 runtime」→ 平台注入的，不用 `pip install`，直接 `from runtime import Args` 即可。
- 返回值必须是 `dict`，且所有字段都是 JSON 可序列化类型（字符串/数字/布尔）。代码内已统一，不要返回 `date` 对象。
- 本地先用仓库 `plugins/tests/` 的单测验证逻辑，再粘到 Coze。

> 入口函数在不同 Coze 版本可能微调；若编辑器提示要 `async def` 或别的命名，照编辑器提示改函数名即可（内部逻辑不变）。
