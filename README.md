# HR 员工制度问答助手（升级版 RAG）

> 基于 Coze 的 RAG 问答系统：不只是「LLM + 知识库」，还接入了**自定义工具插件（年假/加班费/政策时效计算）**，并对知识库构建与回答质量做了**工程化评测**。

这是一个可以写进简历、上传 GitHub 的 AI Agent 小项目。Coze 负责「大脑」（模型 + 编排 + 多端发布），仓库里的代码负责「工程部分」（知识库切分、插件逻辑、评测集），让项目**可复现、可验证、可展示**。

## 项目亮点

- **RAG + Tool Use**：回答既检索知识库，又在需要时调用计算类插件，避免模型「心算翻车」。
- **引用溯源**：要求每条事实性回答附带来源文档与章节。
- **拒答兜底**：知识库没有的内容明确拒答，不编造。
- **工程化评测**：50 条 QA 评测集（tool / retrieval / refusal 三类）+ 本地评测脚本，量化系统能力。

## 技术栈

- 平台：Coze（扣子）Bot + 知识库 + 自定义代码插件（Python）
- 本地：Python 3 标准库（知识库切分、插件逻辑、评测，含 `urllib` 调用 Coze API，零第三方依赖）
- 测试：`unittest`（插件单测，无需安装）

## 目录结构

```
hr-policy-rag-assistant/
├── data/                       # 示例素材（标注为示例数据，脱敏）
│   ├── employee_handbook.md    # 员工手册
│   ├── attendance_policy.md    # 考勤管理办法
│   ├── salary_policy.md        # 薪酬福利制度
│   └── regulations/            # 法规摘录（带生效日期 metadata）
├── scripts/
│   └── build_knowledge_base.py # 知识库切分：按标题层级切 300~500 字 chunk + 提取 metadata
├── plugins/                    # 三个自定义插件（纯函数 + 单测）
│   ├── leave_calculator.py     # 年假计算
│   ├── overtime_calculator.py  # 加班费计算
│   ├── policy_validity.py      # 政策时效校验
│   ├── regulations.json         # 法规注册表
│   └── tests/                  # 单元测试
├── eval/
│   ├── qa_dataset.jsonl        # 50 条评测集（三类）
│   ├── run_local_eval.py       # 本地评测（无需 Coze 账号）
│   └── evaluate_coze_bot.py    # 线上 Bot API 评测（需 COZE_PAT / COZE_BOT_ID）
├── docs/
│   ├── prompt.md               # Bot 人设与回复逻辑（直接粘到 Coze）
│   ├── coze_config.md          # Coze 后台操作步骤（详细）
│   └── plugin_deploy.md        # 插件部署（含可直接粘贴的适配代码）
├── kb_output/                  # 切分产物（运行脚本后生成，建议 gitignore）
└── README.md
```

## 快速开始（本地）

```bash
# 1. 生成切分后的知识库
python scripts/build_knowledge_base.py

# 2. 插件单元测试（标准库即可，无需额外安装）
python -m unittest discover plugins/tests -v

# 3. 本地评测（验证插件 + 知识库覆盖）
python eval/run_local_eval.py
```

## 上 Coze（云端部署）

详见 [`docs/coze_config.md`](docs/coze_config.md) 与 [`docs/plugin_deploy.md`](docs/plugin_deploy.md)，核心三步：

1. 上传知识库（用 `kb_output/knowledge_base.jsonl` 或原始 `data/*.md`）。
2. 发布三个代码插件（年假 / 加班费 / 政策时效，代码已在 `plugin_deploy.md`）。
3. 创建 Bot，粘贴 `docs/prompt.md`，绑定知识库（开启引用）+ 添加插件，发布到 API 拿 `bot_id`。

## 运行线上评测（Coze Bot API）

```bash
# 1. 准备密钥：复制 .env.example 为 .env，填入真实 COZE_PAT 与 COZE_BOT_ID
cp .env.example .env
#   编辑 .env：
#     COZE_PAT=pat_xxx          # Coze「API 管理 → 个人访问令牌」生成
#     COZE_BOT_ID=7476xxxxxx    # 发布 Bot 到 API 渠道后页面显示

# 2. 先冒烟跑 5 条确认能连通
python eval/evaluate_coze_bot.py --limit 5

# 3. 跑全部 50 条，输出分类指标
python eval/evaluate_coze_bot.py
```

脚本仅用 Python 3 标准库（`urllib`）调用 `https://api.coze.cn/v3/chat`，无需 `pip install`。`.env` 已被 `.gitignore` 排除，密钥不会进仓库。

## 效果指标

### 本地基线（无需 Coze 账号，`python eval/run_local_eval.py`）

| 类别 | 说明 | 结果 |
|---|---|---|
| tool | 插件计算结果正确 | 14/14 = 100% |
| retrieval | 答案确实在知识库中 | 26/26 = 100% |
| refusal | 无关问题正确拒答 | 10/10 = 100% |
| **总体** | 50 条评测集 | **50/50 = 100%** |

> 本地基线由 `python eval/run_local_eval.py` 产出（插件单测 14/14 全过）。

### 线上结果（Coze Bot API，`python eval/evaluate_coze_bot.py`）

- 工具类抽样评测 **T01–T11 全部通过（11/11）**，覆盖年假 / 加班费 / 政策时效三类计算，验证 Bot 能正确调用插件并给出带引用的答案。
- 检索类与拒答类已在 Coze Playground 调试中逐句确认可用（年假规则带引用、加班费带引用、无关问题正确拒答）。
- 评测脚本已就绪，完整 50 条可随时一键复跑（`python eval/evaluate_coze_bot.py`）。

## 简历话术

> 基于 Coze 搭建 HR 制度问答助手：RAG 检索 + 自定义工具插件（年假/加班费/政策时效计算），实现引用溯源与拒答兜底；编写知识库切分脚本与 50 条评测集，对系统做工程化效果验证。

## 局限与后续

- 素材为公开模板/示例数据，未接入真实企业制度；后续可替换为脱敏真实文档。
- 线上评测的 retrieval/refusal 自动打分接口已预留，可接 LLM 评分做更客观指标。
- 可扩展：接 Coze API 做前端网页（流式输出 + 多轮上下文），升级为「全栈 AI 应用」。
