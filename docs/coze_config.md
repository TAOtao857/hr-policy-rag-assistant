# Coze 后台配置操作步骤（详细版）

> 目标：把你本地仓库里的「知识库 + 插件 + 提示词」搬进 Coze，跑出一个能推理、能算数、会引用来源的 HR 助手 Bot。
> 全程在 Coze 控制台（coze.cn）网页端操作，无需写前端。
> 建议按顺序做：**先本地跑通 → 再上 Coze**，这样出问题能快速定位是本地代码还是平台配置。

---

## 0. 前置：先在本地跑通（5 分钟）

```bash
cd hr-policy-rag-assistant

# 1) 生成切分后的知识库
python scripts/build_knowledge_base.py
#   -> 产出 kb_output/knowledge_base.jsonl（每行一个 chunk，带 metadata）

# 2) 跑插件单元测试（确认三个插件逻辑正确）
python -m pytest plugins/tests -q
#   若没装 pytest：python -m unittest discover plugins/tests

# 3) 跑本地评测（验证插件 + 知识库是否覆盖评测集）
python eval/run_local_eval.py
#   看三类命中率，tool 类应为 100%，retrieval/refusal 取决于素材
```

本地全绿后，再开始下面的云端配置。

---

## 1. 知识库

### 1.1 生成切分产物（已做，确认一下）
确保 `kb_output/knowledge_base.jsonl` 已生成。它每行结构是：
```json
{"id":"kb0001","content":"...","metadata":{"source":"employee_handbook.md","section":"第二章 考勤","level":2,"effective_date":null,"revoked_date":null}}
```

### 1.2 上传到 Coze
1. 进入 **Coze 控制台 → 知识库 → 创建知识库**。
2. 知识库类型选「**本地内容 / 文档**」。
3. 上传方式二选一：
   - **方案 A（推荐，省事）**：直接上传 `data/` 下的原始 `.md` 文件，分段方式选「自动分段」，召回参数先用默认。
     - 优点：快，Coze 自动按语义切。
     - 代价：分段粒度由平台决定，metadata 需要我们手动补。
   - **方案 B（更工程化，展示能力）**：把 `kb_output/knowledge_base.jsonl` 的每一行 `content` 作为一个独立片段上传（可借助 Coze 知识库 API 批量导入，或复制粘贴成多个小文本片段）。
     - 优点：分段和 metadata（source/section/effective_date）完全可控，和本地评测一致。
4. 上传完成后，进入知识库的「**元数据**」或分段编辑页，给关键分段补 `source`、`section`、`effective_date` 等标签（用于回答引用）。

> 提示：Coze 界面会更新，若找不到「自动分段/自定义分段」入口，以当前控制台实际选项为准；核心动作不变——**把知识灌进去 + 开启召回**。

---

## 2. 插件（自定义代码）

详见 **`docs/plugin_deploy.md`**，里面有每个插件的参数声明表 + 可直接粘贴到 Coze 的完整代码（含平台要求的 `main(args)` 适配层）。

简要路径：
1. **Coze 控制台 → 插件 → 创建插件 → 代码插件（Python）**。
2. 创建三个插件（或在一个插件里加三个工具，按平台支持的粒度）：
   - `leave_calculator` —— 年假计算
   - `overtime_calculator` —— 加班费计算
   - `policy_validity` —— 政策时效校验
3. 把 `plugin_deploy.md` 里对应代码整段粘贴进编辑器，按文档声明参数，点「**测试**」用单测里的样例验证。
4. 保存并「**发布**」插件。

---

## 3. Bot 搭建

1. **创建 Bot**：Coze →  Bots（或「我的 Bot」）→ 创建。
2. **人设与回复逻辑**：把本仓库 `docs/prompt.md` 全文复制粘贴进去。
3. **绑定知识库**：在 Bot 编辑器的「知识」/「添加知识库」里，选第 1 步创建的知识库；开启「**引用**」（让回答带来源）。
4. **添加插件**：在「插件」里搜索并添加第 2 步发布的三个插件。
5. **调试**：在右侧对话框试几条（见 `eval/qa_dataset.jsonl` 里的 question）：
   - 「2020-03-01 入职，到 2026-09-01 有多少天年假？」→ 应调用年假插件，返回 5 天并附依据。
   - 「《员工手册》里加班费怎么算？」→ 应检索到知识库并附引用。
   - 「公司食堂今天吃什么？」→ 应拒答，不编造。

---

## 4. 评测（线上）

1. 发布 Bot 到「**API**」渠道，拿到 `bot_id`（在 Bot 设置 / 发布页可见）。
2. 获取个人访问令牌（PAT）：Coze → 个人设置 → API / 令牌，生成一个 `COZE_PAT`。
3. 本地运行线上评测：
   ```bash
   export COZE_PAT="你的令牌"
   export COZE_BOT_ID="你的bot_id"
   python eval/evaluate_coze_bot.py
   ```
   > 说明：`evaluate_coze_bot.py` 目前逐条打印回答前 60 字，作为「能不能调通 + 抽样看质量」的基线。retrieval/refusal 的自动打分接口已留好，可按需接 LLM 评分。
4. 把线上跑出来的结果填回 `README.md` 的「效果指标」一节，作为项目交付物。

---

## 5. 收尾（GitHub 交付）

- 把 Coze 后台的**提示词、插件配置截图、Bot 设置**存档到 `docs/`（已有 `prompt.md`、`coze_config.md`、`plugin_deploy.md`）。
- 仓库根目录放一张架构图（可用 `docs/architecture.png` 或 README 里的 Mermaid）。
- `README.md` 写清：做了什么、怎么本地复现、怎么上 Coze、效果指标、局限与后续。
- 推到 GitHub，简历即可写：「基于 Coze + RAG 的 HR 制度问答助手，含自定义工具插件与工程化评测」。
