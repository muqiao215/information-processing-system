#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


BUNDLE_PATH = Path("/tmp/follow_builders_bundle.json")
MARKDOWN_PATH = Path("/root/.ductor/workspace/output_to_user/ai_builders_digest_latest.md")
MANIFEST_PATH = Path("/root/.ductor/workspace/output_to_user/ai_builders_digest_sources_latest.json")


SECTION_TITLES = {
    "A": "A. AI前沿与工具",
    "B": "B. 创业与战略",
    "C": "C. 产品与体验",
    "D": "D. 行业与观点",
    "E": "E. 技术实践",
}

SECTION_INTROS = {
    "A": "今天这栏的主线很清楚：AI 工具正在从单点能力升级成工作台、托管平台和稳定基础设施。",
    "B": "创业讨论继续往组织密度、供给约束和个人杠杆迁移，关键不再只是“能不能做”，而是“谁能以更轻的结构持续做”。",
    "C": "产品体验的边界正在外扩，聊天框之外的资料组织、后台执行、默认工作流和生成式界面都开始变成主战场。",
    "D": "行业层面的变化已经不只是模型排名，而是团队协作、职业分工和平台格局如何被 agent 重新改写。",
    "E": "技术实践越来越像一条完整链路：评测、托管、权限、会话、工具编排和运行时可观测性缺一不可。",
}

SECTION_KEYWORDS = {
    "A": [
        "agent", "agents", "managed agents", "notebook", "notebooks", "gemini",
        "gateway", "model", "models", "webgpu", "webassembly", "browser",
        "platform", "infrastructure", "sandbox", "console", "cli",
    ],
    "B": [
        "business", "subscription", "company", "companies", "employees", "team",
        "teams", "bootstrapped", "solo", "china", "pricing", "strategy",
        "market", "org", "organization", "household",
    ],
    "C": [
        "design", "frontend", "product", "experience", "workflow", "workflows",
        "content", "chat", "source", "sources", "organize", "review",
        "non-technical", "personalized", "upload", "project", "projects",
    ],
    "D": [
        "future", "humanity", "industry", "knowledge work", "manager",
        "managers", "team", "teams", "org", "organization", "slack", "public",
        "culture", "everyone", "company", "companies", "web",
    ],
    "E": [
        "code", "coding", "eval", "judge", "sandbox", "harness", "tool",
        "tools", "api", "mcp", "automation", "deploy", "self-hosting",
        "local model", "local models", "tracing", "session", "checkpointing",
        "permission", "permissions", "trace",
    ],
}

CURATED_OVERRIDES = {
    "https://claude.com/blog/claude-code-desktop-redesign": {
        "title": "Claude Blog：Claude Code 桌面端重做，面向并行 agent 工作方式",
        "summary": "这次 redesign 的核心不是把终端功能搬进 App，而是承认 agentic coding 已经变成“多任务在飞、人在调度”的工作形态。侧边栏、多会话、可拖拽布局、终端、编辑器、预览和 diff 都围绕同一个方向：开发者正在从单线程提问者变成多个 agent 会话的编排者。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://www.youtube.com/playlist?list=PLOhHNjZItNnMm5tdW61JpnyxeYH5NDDx8": {
        "title": "Training Data：从 SEO 到 agent-led growth，营销对象正在从人变成 agent",
        "summary": "James Cadwallader 的判断很清楚：AI 搜索不只是新的流量入口，而是“谁在浏览互联网”发生了变化。品牌内容以后既要被索引，也要被 agent 理解、比较和带回给用户，这会把增长、内容、分发和归因重新组织一遍。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/levie/status/2044225408972009842": {
        "title": "Aaron Levie：企业 agent 会让 forward deployed engineer 更重要",
        "summary": "他提醒大家别低估企业 agent 的落地成本：卖 agent 不像卖一个装完就结束的软件，而更像交付一段真实业务流程。供应商需要懂客户领域、接系统、整理上下文、验证效果，所以懂业务又懂工程的前线角色短期内反而会更值钱。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/danshipper/status/2044079255726838273": {
        "title": "Dan Shipper：Sparkle v4 把桌面整理做成持续运行的文件系统 agent",
        "summary": "Sparkle 的方向很具体：不是让用户自己学一套整理法，而是让 agent 读取文件系统、提出结构、清理重复和旧文件，并在后台按计划维持秩序。它代表了一类更日常的 agent 产品机会：从高大上的知识工作，落到个人环境维护和低频杂务。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/petergyang/status/2044061039671820406": {
        "title": "Peter Yang：AI 输出不是终稿，人的 taste 仍然负责把平均值推高",
        "summary": "这条是对“外包思考”的很好纠偏。agent 可以快速铺开大量可能性，但真正的产品与创作质量，来自人继续判断、塑形和删改。对 builder 来说，关键能力不是把 prompt 写成魔法咒语，而是把 AI 给出的平均答案继续磨到有品味。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/claudeai/status/2044131493966909862": {
        "title": "Claude：桌面端支持一个窗口并行管理多个 Claude Code 会话",
        "summary": "多会话并排不是小功能，它把 coding agent 的产品重心从“一个聊天线程”推向“任务队列与执行面板”。当用户同时开 refactor、bug fix、测试补齐和 review，会话管理本身就变成核心体验。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/claudeai/status/2044131495296586041": {
        "title": "Claude：终端、文件编辑、预览和 diff 进入同一个可拖拽工作台",
        "summary": "这条补充说明了桌面端真正想吞掉的工作面：测试、改文件、看 HTML/PDF、审 diff 和调用 CLI 插件都尽量留在同一界面里。agent 工具正在从聊天框变成轻量 IDE 和执行控制台的混合体。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/_catwu/status/2044212251717186007": {
        "title": "Cat Wu：Claude Code 桌面端把本地与云端多会话放到一个控制台",
        "summary": "她作为高频用户强调的是具体工作流：看 git 状态、固定活跃会话、同时观察本地和云端任务。这个反馈说明 agent 产品的竞争会越来越落在“多线程项目控制”上，而不只是模型回答质量。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/_catwu/status/2044103103591657941": {
        "title": "Cat Wu：Routines 让 Claude Code 可以按计划、GitHub 事件和 API 启动",
        "summary": "定时任务、GitHub 事件和 API 触发把 Claude Code 从手动工具推向后台自动化。对团队来说，这意味着 agent 可以逐渐接管重复性维护、检查和代码流转任务，而不是只在开发者主动打开时才工作。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/alexalbert__/status/2044144091395699055": {
        "title": "Alex Albert：Claude Code 桌面端开始变成不必离开的工作 hub",
        "summary": "他的反馈很有代表性：当 Cowork 和 Code 能覆盖大部分日常任务，用户打开其他应用甚至终端的频率会下降。AI 工具的下一步竞争，很可能是争夺默认工作入口，而不是只做单点助手。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/zarazhangrui/status/2044211269767704929": {
        "title": "Zara Zhang：从 Chrome 历史和新标签页出发，Tab Out 找到高频入口",
        "summary": "这条 build log 的价值在产品判断：只是做一个按钮没人会点，所以她把浏览历史、打开标签页和任务分组放到用户每天都会看到的新标签页。AI 功能要真正被用起来，入口频率往往比模型炫技更重要。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/zarazhangrui/status/2044114136364397043": {
        "title": "Zara Zhang：Tab Out 简化成纯本地 Chrome extension，80% 时间在砍功能",
        "summary": "她把一个小工具从服务端、Node 和复杂依赖里剥离出来，最后变成纯本地扩展。这个过程很值得 builder 记住：Claude 往往会 overkill，真正的产品速度来自持续压缩范围、删掉架构和保留最短路径。",
        "sections": ["B", "C", "E"],
    },
    "https://x.com/nikunj/status/2044277884777574565": {
        "title": "Nikunj Kothari：vibe code 能做掉简单流程，但做不掉系统深度",
        "summary": "他用 Slack 通知系统提醒大家：很多简单 workflow 会被一周末做掉，但真正高质量、有细节、有长期维护价值的系统仍然需要时间和坚持。AI 会压缩入门成本，却不会自动交付产品深度。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/garrytan/status/2044292522256806260": {
        "title": "Garry Tan：GBrain 开源，个人 agent 记忆正在向大规模 markdown brain 演进",
        "summary": "GBrain 的关键信号是规模和可读性：个人知识库已经推到一万七千多页，还保持开源、MIT 和文本化。长期看，个人 agent 的差异不会只在模型，而在可迁移、可审查、可持续生长的 memory 与 skill 资产。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/rauchg/status/2044067044325503404": {
        "title": "Guillermo Rauch：agent coding platform 需要弹性数据库作为默认底座",
        "summary": "他把 app generation 和 Postgres-compatible 弹性数据库放在一起讲，说明 agent 平台不是只生成前端或代码片段。真正能跑起来的 agent coding 产品，必须把数据层、扩缩容和持久化也纳入默认架构。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/amasad/status/2044277183766770029": {
        "title": "Amjad Masad：一次性转换小工具正在被压缩成可复用 skill",
        "summary": "这条很短，但方向明确：过去要反复写的一次性转换应用，现在可以沉淀为 skill。随着 agent 生态成熟，很多“做个小工具”的需求会变成“调用或改造一个 skill”，复用粒度会继续上移。",
        "sections": ["A", "B", "C", "E"],
    },
    "https://x.com/petergyang/status/2044234654241436066": {
        "title": "Peter Yang：Claude Code 桌面与移动端之间仍缺顺滑会话接力",
        "summary": "他的问题点出了 agent 产品的下一个体验短板：用户不想记指令，也不想手动 remote-control，只希望同一个任务能自然跨桌面和手机继续。长期任务 agent 一旦普及，跨设备 session continuity 会变成基本能力。",
        "sections": ["C", "E"],
    },
    "https://x.com/rauchg/status/2043869656931529034": {
        "title": "Guillermo Rauch：开源云端 coding agent 参考平台，AI 软件工厂开始具象化",
        "summary": "Vercel 这次开源的不是一个零碎 demo，而是一套面向真实软件公司的参考平台。它点出的核心很直接：通用 coding agent 很难天然适配大仓库、团队知识、内部流程和制度约束，所以公司会把护城河逐渐转向自己的 agent 基础设施、知识接入和工作流编排。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/levie/status/2043883641366032638": {
        "title": "Aaron Levie：企业里会出现新的“agent 部署者与管理者”岗位",
        "summary": "他把企业 agent 落地说得很务实：真正关键的人，不只是会点几下 AI 工具，而是能挑出最高杠杆流程、设计人机分工、接入系统与数据，并持续评估 agent 是否真的创造价值。AI 采用越深入，这类新岗位越会从临时职责变成正式工种。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/petergyang/status/2043848480423325757": {
        "title": "Peter Yang：别把时间都花在折腾 OpenClaw/Claude Code 配置上",
        "summary": "这条提醒很重要，因为它点破了很多 builder 的伪进展：不断优化工具链、提示词和本地配置，会带来强烈的掌控感，但不一定对应真实产出。AI 工作流真正的分水岭，是能不能稳定把它们接回“完成任务”而不是“持续调环境”。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/trq212/status/2043814646600348046": {
        "title": "Thariq：Claude Code 新渲染器开始改善长时间使用时的交互手感",
        "summary": "这类更新看起来像界面小修，但对高频使用 coding agent 的人很关键。减少闪烁、改善可读性和交互稳定性，意味着产品开始从“能不能跑”转向“能不能长时间舒服地用”，这会直接影响 agent 工具的日常黏性。",
        "sections": ["C", "E"],
    },
    "https://x.com/amasad/status/2043785145606656223": {
        "title": "Amjad Masad：应用托管开始按地区配置，合规与隐私进入默认产品层",
        "summary": "地区化部署能力说明 AI 应用平台正在补足走向企业和全球市场时最实际的一层：数据驻留、合规与隐私要求。builder 以后比拼的不只是生成速度，还要比谁能更快进入受监管和跨地区的真实业务场景。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/ryolu_/status/2043891602381500583": {
        "title": "Ryo Lu：多面板与多 agent 视图会成为下一代工作台的基础能力",
        "summary": "左右上下自由拆分听上去只是布局更新，但它背后其实是 agent 产品形态的变化。随着用户同时管理多个上下文、多个执行线程和多个助手，界面必须从单聊天窗口进化成更像操作台的形态。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/garrytan/status/2043948971568312473": {
        "title": "Garry Tan：GBrain 想把搜索、skillpacks 和语音 agent 合成一个主观工作台",
        "summary": "这条发布的重点不是又一个工具集合，而是个人 agent 工作台正在朝“有记忆、有技能包、有语音接口”的统一体演进。谁先把这些层真正打通，谁就更接近能长期陪跑用户的个人操作系统。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/garrytan/status/2043948627291451625": {
        "title": "Garry Tan：搜索调优、搜索评测与 CJK 支持，说明 recall 正在走向工程化",
        "summary": "记忆检索如果没有评测、健康检查和多语言支持，就很难成为生产能力。GBrain 这轮更新传递的信号很明确：agent 的 recall 体系正在从灵感型 feature 变成需要持续调参与验证的基础设施。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/nikunj/status/2043808491807396059": {
        "title": "Nikunj Kothari：真正的无限 token 额度，正在变成人才竞争的一部分",
        "summary": "这条玩笑背后其实是非常现实的创业问题。agent 公司一边想吸引最强 builder，一边又要控制推理成本；而前沿模型公司反过来天然拥有更宽松的 token 供给。AI 创业的组织设计、薪酬结构和成本模型，会越来越受算力预算影响。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/danshipper/status/2043819933675450455": {
        "title": "Dan Shipper：软件工程会分化成 pirate 与 architect 两种角色",
        "summary": "这条判断抓住了 AI coding 对团队结构的真实冲击。一个角色负责高速试错、迅速找到价值，另一个角色负责把混乱原型整理成可维护系统。agent 不是把工程流程抹平，而是在放大探索与收敛这两种工作方式的差异。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/danshipper/status/2043739805276619223": {
        "title": "Dan Shipper：“an agent is just a folder”是很强的系统心智模型",
        "summary": "把 agent 理解成文件夹，本质上是在强调 agent 不只是一个会回复的模型，而是一组可读写的记忆、技能、上下文和工作产物。这种模型对产品设计、协作方式和工程实现都很有启发，因为它把 agent 从聊天界面拉回到可管理的工作对象。",
        "sections": ["C", "D", "E"],
    },
    "https://x.com/swyx/status/2043778767798317349": {
        "title": "Swyx：全球大部分 agent 与 AI engineering 正在被旧金山一小块区域吸走",
        "summary": "这句夸张表达背后反映的是人才、资本、项目与偶遇密度仍然极端集中。哪怕 AI 已经让远程协作更强，真正高密度的 builder 网络效应依旧存在，这会继续影响创业者选址、招聘与信息优势分布。",
        "sections": ["B", "D"],
    },
    "https://x.com/swyx/status/2043770029024653798": {
        "title": "Swyx：可组合与主动化让 agent 使用量翻倍，递归式 agent 开始冒头",
        "summary": "这里最值得看的不是单个产品数据，而是组合式 agent 和主动执行正在一起放大需求。一旦 agent 能彼此调用、持续跟进任务，使用场景就会从点状助手转向更连续的流程自动化。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/swyx/status/2043786360012845509": {
        "title": "Swyx：写作 skill 模板开源，skill 本身正在变成可复制资产",
        "summary": "当写作方法、提示结构和工作套路可以被封装成 skill 模板并公开复用时，个人经验就开始转化成可传播的生产资料。对 agent 生态来说，skills 会越来越像真正的产品单元，而不只是附属提示词。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://www.youtube.com/@NoPriorsPodcast": {
        "title": "No Priors：AI for Atoms 说明 frontier AI 正在外溢到材料工程",
        "summary": "这期访谈的价值在于，它把大家熟悉的软件与模型叙事外推到了材料科学。Liam Fedus 从 OpenAI 转向做材料工程，说明 frontier AI 的下一波增量不只在聊天或编码，而会进入实验、制造和更长研发周期的行业场景。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/levie/status/2045355693050655048": {
        "title": "Aaron Levie：agent 会把企业软件推向 headless 与按消费计费",
        "summary": "Levie 这条长帖把 enterprise SaaS 的下一步说得很清楚：过去软件价值被人的 seat 数和一天能点多少按钮限制，agent 则可以 24/7 并行调用系统、处理合同、迁移营销数据和跑客户流程。结果不是软件价值被吃掉，而是平台要开放给外部 agent，并把“人买 seat、agent 买 consumption”变成新的收入结构。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/nikunj/status/2045250489189908534": {
        "title": "Nikunj Kothari：Fintool 被 Microsoft 收购，垂直 AI 产品继续并入大平台",
        "summary": "Nikunj 以天使投资人身份提到 Fintool 加入 Microsoft，这条信号不在交易本身，而在于“模型还没成熟前就能做复杂金融推理”的垂直产品，正在被大平台吸收。对创业者来说，专门领域里的重推理体验仍然有价值，但退出和扩张路径可能越来越靠近平台公司。",
        "sections": ["B", "D"],
    },
    "https://x.com/claudeai/status/2045156271251218897": {
        "title": "Claude：从代码库和设计文件自动生成团队设计系统",
        "summary": "Claude Design 的方向不是单次出图，而是读代码库与设计文件，抽取团队的品牌、组件和样式规则，再自动应用到新项目。它说明设计系统正在从静态文档变成可执行上下文：AI 不只是帮你画页面，而是开始维护团队产品的一致性。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/claudeai/status/2045222254699511855": {
        "title": "Claude：Claude for Word 登陆 Pro 和 Max，办公套件成为高频入口",
        "summary": "Claude for Word 配合 Opus 4.7 进入 Pro/Max，信号在于 AI 助手继续往用户已经工作的文档界面里钻。对产品团队来说，高频入口比新聊天窗口更重要；对商业化来说，Office 场景也更容易支撑高阶订阅。",
        "sections": ["A", "B", "C"],
    },
    "https://x.com/GoogleLabs/status/2045250788864495874": {
        "title": "Google Labs：Flow Music 把自然语言创作扩展到歌曲与 playlist",
        "summary": "ProducerAI 变成独立的 Flow Music，意味着 Flow 家族从图像、视频继续扩展到音乐生成、分享和 remix。更大的趋势是，多模态创作工具正在按媒介拆成专门入口，同时又被统一到同一个创作品牌和工作流里。",
        "sections": ["A", "C"],
    },
    "https://x.com/zarazhangrui/status/2045374512691360177": {
        "title": "Zara Zhang：很多设计场景里，用代码设计优于图像生成",
        "summary": "Zara 的观察很适合产品 builder：当目标是可控、可迭代、可复用的图形时，HTML/CSS 这类代码媒介往往比一次性 image gen 更强。AI 时代的设计能力不只是会生成好看的图，而是能选择正确媒介，把视觉产物变成可维护系统。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/zarazhangrui/status/2045394997630099922": {
        "title": "Zara Zhang：写作不等于生成文字，生成反而是最不重要的一步",
        "summary": "这条是对 LLM 写作误区的精准纠偏。写作真正难的是观察、判断、组织材料、形成观点和删改，生成文字只是最后的表层动作。对内容产品和知识工作来说，AI 的价值不该停在“吐字快”，而要回到思考与编辑流程。",
        "sections": ["C", "D"],
    },
    "https://x.com/ryolu_/status/2045336089867825157": {
        "title": "Ryo Lu：好 agent 等于好 harness、好模型和可跨环境运行",
        "summary": "这句短公式很有工程含量：agent 产品的体验不是模型单独决定的，而是模型、harness、权限、运行环境和迁移能力一起决定的。谁能让同一套 agent 在本地、云端和不同工具里稳定跑，谁就更接近可用的生产系统。",
        "sections": ["A", "E"],
    },
    "https://x.com/danshipper/status/2045241699992047638": {
        "title": "Dan Shipper：Opus 4.7 需要按编码、写作和表格等真实任务做 vibe check",
        "summary": "Every 对 Opus 4.7 的测试提醒大家，模型升级不能只看单个 benchmark。builder 更需要把它放进 coding、writing、spreadsheets 等真实任务里观察手感、失败模式和边界，这种横向 vibe check 会越来越接近产品团队的日常评测方法。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/kevinweil/status/2045230426210648348": {
        "title": "Kevin Weil：OpenAI for Science 被分散进各研究团队",
        "summary": "Kevin Weil 离开 OpenAI，同时提到 OpenAI for Science 正在去中心化进入其他研究团队。这里的行业信号是：AI for science 不再只是一个孤立产品组，而可能成为前沿实验室多条研究线的基础能力，科学加速会从项目变成组织能力。",
        "sections": ["B", "D"],
    },
    "https://x.com/claudeai/status/2045248224659644654": {
        "title": "Claude：Opus 4.7 版 Claude Code hackathon 继续强化 builder 生态",
        "summary": "Claude Code hackathon 这类活动不只是营销，它把模型发布、开发者反馈和真实项目压力测试绑在一起。100K API credits 的奖池背后，是模型公司越来越依赖 builder 社区来发现工具边界、放大样例并训练市场预期。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/petergyang/status/2045307149740609591": {
        "title": "Peter Yang：Claude Design 已能覆盖视频、幻灯片、网站、移动端和设计系统",
        "summary": "这个 demo 的价值在于展示 Claude Design 的跨媒介野心：不是只做一张图，而是把视频、slides、web、mobile app 和 design system 放进同一套生成体验里。产品体验的竞争正在从“生成一个资产”转向“覆盖完整表达工作流”。",
        "sections": ["A", "C"],
    },
    "https://x.com/mattturck/status/2045211226272129274": {
        "title": "Matt Turck：Anthropic Labs 形成 Claude Code、Skills、Cowork、Design 连续产品线",
        "summary": "这条短评指向一个重要格局：Anthropic 不再只是发布模型，而是在围绕 code、skills、cowork 和 design 连续推出工作流产品。模型公司的竞争正在往应用层、默认入口和多场景工作台延伸。",
        "sections": ["A", "B", "D"],
    },
    "https://x.com/kevinweil/status/2043510607736189193": {
        "title": "Kevin Weil：别把人类智能和机器智能看成同一条尺子上的高低",
        "summary": "他提醒大家不要只盯着“AI 什么时候追平人类”这种线性叙事。更重要的方向是承认两种智能在高维空间里各有擅长，再去设计新的协作形态和问题分工。这种视角对产品设计和能力评估都更有启发。",
        "sections": ["A", "D"],
    },
    "https://x.com/levie/status/2043426157367095397": {
        "title": "Aaron Levie：企业 AI 正在从聊天演示转向真正进工作流的 agent",
        "summary": "他这轮密集拜访里最重要的信号有三条：企业在从“百花齐放试一试”转向聚焦具体自动化场景；预算开始按 token 和算力被严肃管理；真正的落地瓶颈已经从模型能力转向系统碎片化、变更管理和跨 agent 互操作。企业级 agent 进入了更硬的一阶段。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/levie/status/2043318118169354302": {
        "title": "Aaron Levie：安全岗位也会出现 Jevons Paradox，AI 越强人越不够用",
        "summary": "他的判断很值得重视：AI 会让漏洞发现速度和代码规模一起暴涨，但响应、修复、架构决策仍需要高水平人工判断。结果不是安全岗位缩水，而是安全团队会面对更多待分诊的问题、更高的处置压力和更大的专业人才缺口。",
        "sections": ["B", "D", "E"],
    },
    "https://x.com/garrytan/status/2043566215927328955": {
        "title": "Garry Tan：agentic engineering 的结构应该是 fat skills、fat code、thin harness",
        "summary": "这条几乎可以当成今年 agent 工程的一句压缩公式。模糊判断和经验动作沉淀进 markdown skills，必须精确执行的部分写进代码，而 harness 尽量保持薄。这种分层方式同时提升了可移植性、可维护性和人机协作的清晰度。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/zarazhangrui/status/2043415572688629937": {
        "title": "Zara Zhang：把浏览器新标签页重做成个人工作台，而不是空白入口",
        "summary": "她把一个日常痛点做成了很完整的产品实验：按域名分组、批量清理 easy wins、检测重复标签、把暂不处理的页面转成 checklist。重点不只是“能 vibe code 一个页面”，而是说明 AI 让个人把高频界面改造成适合自己工作流的专属工具变得现实。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/nikunj/status/2043374140443553885": {
        "title": "Nikunj Kothari：创业可以学 DoorDash，从被忽视的郊区市场切入",
        "summary": "他借 DoorDash 的历史提醒创业者，不一定非要在最拥挤的核心地带正面肉搏。随着更多有经验的人不愿再为大城市通勤买单，贴近大城市但不在中心区的供给缺口，可能会孕育出一批新的公司形态和办公基础设施机会。",
        "sections": ["B", "D"],
    },
    "https://x.com/adityaag/status/2043501400626491758": {
        "title": "Aditya Agarwal：Anthropic 身上有一种早期 Facebook 式的创业文化",
        "summary": "他看到的不是人员背景相似，而是公司内部那种自下而上的 hacker 气质、强任务感和“玩得很开心”的创业状态。这类文化判断虽然主观，但很有参考价值，因为模型公司的长期差异未必只来自研究路线，也来自组织气质和执行方式。",
        "sections": ["B", "D"],
    },
    "https://x.com/rauchg/status/2043381737754120592": {
        "title": "Guillermo Rauch：把最苛刻的客户直接拉进群，产品反馈闭环会快很多",
        "summary": "这不是简单的用户运营技巧，而是一种很强的产品机制设计。让 demanding customers 和工程负责人在同一条实时反馈链路里，团队就更难躲在 roadmap 和调研报告后面，而会被迫面对真实问题、快速响应、持续交付。",
        "sections": ["B", "C", "D"],
    },
    "https://claude.com/blog/preparing-your-security-program-for-ai-accelerated-offense": {
        "title": "Claude Blog：AI 正在把攻防节奏同时拉快，安全体系必须按“机器时代”重排",
        "summary": "这篇文章最关键的提醒是，AI 正在缩短从补丁发布到可利用攻击出现之间的时间窗口。企业不能再把修补、暴露面管理和优先级排序当成例行工作，而要按更快的机器节奏重构安全流程。对所有软件团队来说，这已经不是安全部门的局部议题，而是工程基本盘。",
        "sections": ["A", "D", "E"],
    },
    "https://x.com/levie/status/2043192337111924930": {
        "title": "Aaron Levie：agent token 需求会把数据中心开支推到新量级",
        "summary": "他给出了一个很重要的判断：今天最吃 token 的还只是少量 coding agent，等这类长任务 agent 扩散到更大范围的知识工作后，算力与资本开支压力会再上一个台阶。真正被低估的不是聊天，而是后台持续运行的 agent 负载。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/steipete/status/2043136624469619050": {
        "title": "Peter Steinberger：把 harness 做成插件后，多 runtime 对比会容易很多",
        "summary": "这条更新的价值不只是“可插拔”，而是把 agent 运行时和上层产品形态进一步解耦。harness 一旦能替换，团队就能更快比较 Anthropic SDK、自定义实现和其他执行后端，基础设施实验成本会明显下降。",
        "sections": ["A", "B", "E"],
    },
    "https://x.com/zarazhangrui/status/2043202553538925031": {
        "title": "Zara Zhang：人与人协作会退回到定方向、审质量和彼此陪伴",
        "summary": "她把一个很可能发生的迁移说得很清楚：项目同步、状态汇报和交接会越来越交给 agent，人类沟通则更多保留给目标判断、好坏标准、创意碰撞和情绪连接。组织协作的默认接口正在变化。",
        "sections": ["B", "C", "D"],
    },
    "https://x.com/garrytan/status/2043198783006355747": {
        "title": "Garry Tan：可扩展的 agent 架构应该是 thin harness、fat skills",
        "summary": "这句话值得记下来，因为它直接指出了 agent 产品的结构重点。真正该沉淀的是 skills、memory 和文档化能力，而不是把所有逻辑都塞进 harness 里。这样系统才更容易迁移、调试和长期演化。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/levie/status/2043051227387433144": {
        "title": "Aaron Levie：AI 不会消灭律师，反而会把法律需求继续放大",
        "summary": "这是一个典型的“AI 提高需求弹性”案例。门槛下降后，更多人会提出法律问题、触发更多审查与执行动作，同时 AI 自己又会制造新的合规和知识产权议题，所以专业服务未必缩小，反而可能变得更繁忙。",
        "sections": ["C", "D"],
    },
    "https://x.com/nikunj/status/2043092455550259341": {
        "title": "Nikunj Kothari：警惕只把创业公司当估值游戏的 VC",
        "summary": "这条抱怨背后其实是创业融资环境的一个老问题：有些投资人关心的是短期估值抬升和账面回报，而不是公司长期建设。对创始人来说，AI 热潮越高，这类资本错配反而越容易出现。",
        "sections": ["B", "D"],
    },
    "https://x.com/steipete/status/2043136615640694797": {
        "title": "Peter Steinberger：strict-agentic 的重点是别让 GPT 停在“给计划”",
        "summary": "他在试图解决一个很多团队都踩到的问题：模型很会写计划，但不一定继续执行。把 execution contract 明确成 strict-agentic，本质上是在给 agent 运行时增加更强的继续工作约束，这对真实交付比提示词花活更重要。",
        "sections": ["A", "E"],
    },
    "https://x.com/rauchg/status/2043020059896091016": {
        "title": "Guillermo Rauch：microVM 沙箱的竞争开始卷向真实世界性能与稳定性",
        "summary": "这条发布说明基础设施竞争已经进入更硬的一层：不仅要跑得快，还要在客户真实负载里稳定。对 coding agent、并行计算和受限执行环境来说，沙箱不再是附属组件，而是在前台决定可用性的核心能力。",
        "sections": ["A", "E"],
    },
    "https://x.com/garrytan/status/2043198780800197025": {
        "title": "Garry Tan：记忆不该死在 harness 里，memory 和 skills 都应回到 markdown",
        "summary": "这条比上一条更进一步，把 agent 长期记忆的落点说死了：memory、skills、brain 最好都落在人能读写的 markdown 和 git 里。这样一来，harness 才只是调度层，而不是绑死系统的黑箱内核。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/zarazhangrui/status/2043187721989149146": {
        "title": "Zara Zhang：最高效的人类协作，可能是一人端到端配一群 agents",
        "summary": "这条判断直接挑战了很多组织默认流程。她认为与其让多人频繁对齐，不如把一个问题交给单一 owner 端到端推进，再由 agent 补足执行密度。AI 时代的组织单元，可能会重新向“小而完整”收缩。",
        "sections": ["B", "C", "D"],
    },
    "https://x.com/steipete/status/2043136620006961384": {
        "title": "Peter Steinberger：让 Codex 直接当 harness，拿回线程、resume 与执行控制",
        "summary": "把 Codex 直接放进 harness 位置，不只是换模型，而是把线程管理、会话续跑、压缩和执行能力一起交给更成熟的运行时。对 agent 产品来说，这类替换会显著改变稳定性上限和交互手感。",
        "sections": ["A", "E"],
    },
    "https://x.com/adityaag/status/2043144970060939487": {
        "title": "Aditya Agarwal：真正的 agent 差异在长周期记忆管理，不在简单循环",
        "summary": "他把“agent”和“把 LLM 放进 loop”区分开的关键，落在 long-horizon memory management 上。这一点很重要，因为一旦任务跨天、跨工具、跨上下文，记忆架构才是真正决定效果的底层分水岭。",
        "sections": ["A", "D", "E"],
    },
    "https://x.com/karpathy/status/2042341482531864741": {
        "title": "Andrej Karpathy：OpenClaw 把最新 agent 能力第一次带给大批非技术用户",
        "summary": "他点出的关键不是模型又进步了一点，而是 OpenClaw 这种形态第一次让很多原本只把 AI 当成网页聊天工具的人，直接体验到 agent 模型的执行力。真正的扩散点开始从技术圈向外渗透。",
        "sections": ["C", "D"],
    },
    "https://x.com/karpathy/status/2042334451611693415": {
        "title": "Andrej Karpathy：社会对 AI 能力的认知正在严重分层",
        "summary": "免费旧模型的体验，和付费前沿 agent 在编程、研究里的表现，已经像两种不同技术。这个认知落差会直接影响市场判断、组织决策和对风险与机会的估值。",
        "sections": ["A", "B", "D", "E"],
    },
    "https://x.com/_catwu/status/2042345489778331915": {
        "title": "Cat Wu：Claude Code 接入 Bedrock 与 Vertex 的门槛继续下降",
        "summary": "这类接入优化看起来只是安装变快，实质上是在把企业常见的云与权限体系接到 coding agent 上。采用门槛一降，团队落地速度就会明显上来。",
        "sections": ["A", "E"],
    },
    "https://x.com/trq212/status/2042335178388103559": {
        "title": "Thariq：Monitor Tool 让 Claude Code 真正能盯住运行中的系统",
        "summary": "能启动 dev server、持续观察错误，再把反馈带回 agent，这意味着 coding agent 不再只会改静态代码，而是开始进入带观测闭环的真实开发流程。",
        "sections": ["C", "E"],
    },
    "https://x.com/trq212/status/2042318547519762678": {
        "title": "Thariq：Prompting 会变成和写作、表达一样的高杠杆能力",
        "summary": "他把 prompting 定义成“通过 harness 与 agent 对话”的技能。重点不在写花哨提示词，而在于提升人和 agent 之间的信息带宽，让协作更稳定、更可教。",
        "sections": ["C", "D"],
    },
    "https://x.com/rauchg/status/2042358253510963384": {
        "title": "Guillermo Rauch：下一代云将围绕 agentic infrastructure 重建",
        "summary": "长时运行、沙箱、令牌分发、自愈与自优化，被放到同一套基础设施叙事里。对 builder 来说，未来云平台卖的不是机器，而是 agent 能不能持续可靠地干活。",
        "sections": ["A", "B", "E"],
    },
    "https://x.com/alexalbert__/status/2042329150086922574": {
        "title": "Alex Albert：让 Sonnet 中途请教 Opus，性能更高且总成本更低",
        "summary": "这条很像托管 agent 设计的缩影：别让便宜模型死磕难题，而是在关键节点调用更强模型给计划。多模型协作正在从技巧变成默认架构模式。",
        "sections": ["A", "E"],
    },
    "https://x.com/levie/status/2042469771275329594": {
        "title": "Aaron Levie：真正被低估的是“非软件行业”的自动化需求",
        "summary": "他把零售、药研、金融、医疗等场景串起来讲得很清楚：过去很多项目不是不重要，而是太贵、太难、数据太乱。现在 agent 降低了执行成本，软件需求会外溢到大量传统行业。",
        "sections": ["B", "D"],
    },
    "https://x.com/levie/status/2042392664943870443": {
        "title": "Aaron Levie：AI 采用已经分成聊天派与长任务 agent 派",
        "summary": "聊天工具的提效是有上限的，而能在后台长时运行、会用工具、会接数据的 agent，才可能带来 100% 以上的生产率跃迁。真正的难点会转向上下文、合规、安全与企业流程改造。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/garrytan/status/2042497872114090069": {
        "title": "Garry Tan：给 OpenClaw/Hermes 加上“万级 Markdown 总召回”能力",
        "summary": "GBrain 这类项目的价值不在又多一个知识库，而在于把 agent 的长期记忆从聊天窗口外移到真实文档堆里。谁先解决 recall，谁就更接近可用的个人 agent 工作台。",
        "sections": ["C", "E"],
    },
    "https://x.com/sama/status/2042342572958630332": {
        "title": "Sam Altman：Codex 需求溢出到足以支撑更高价位订阅层",
        "summary": "一句简短公告背后是很直接的商业信号：高强度 coding agent 已经开始把用户从“试用 AI”推向“愿意为稳定产能付费”。价格分层会越来越围绕可交付工作量来设计。",
        "sections": ["A", "B", "D"],
    },
    "https://x.com/claudeai/status/2042308627478773808": {
        "title": "Claude：Sonnet 加 Opus advisor，在 SWE-bench 多语种上更强还更省",
        "summary": "评测结果说明 advisor 模式不是营销包装，而是可测的系统设计改进。更高通过率加更低单任务成本，会推动更多团队把“强模型兜底”做成生产默认值。",
        "sections": ["A", "E"],
    },
    "https://x.com/claudeai/status/2042308625989882054": {
        "title": "Claude：Advisor Tool 已经进入 Messages API 的单次请求链路",
        "summary": "当 Sonnet 或 Haiku 在中途遇到难点时，可以直接咨询 Opus 再继续执行。这说明多模型分层协作，已经开始被封装成开发者 API 的原生能力，而不是手工拼装技巧。",
        "sections": ["A", "E"],
    },
    "https://x.com/joshwoodward/status/2041982173402821018": {
        "title": "Josh Woodward：Gemini 把 Notebook 能力并回主产品",
        "summary": "Gemini 这次不是给聊天产品多加一个侧栏，而是把资料上传、长期整理和会话同步做成统一工作台。信号很明确：AI 产品正在从“会聊”走向“能持续围绕资料工作”。",
        "sections": ["A", "C"],
    },
    "https://x.com/petergyang/status/2041989206495653915": {
        "title": "Peter Yang：无限量 AI 订阅不会一直成立",
        "summary": "他把 Anthropic 对 OpenClaw 的限制、本地模型路线和中国市场观察放在一起看，核心指向同一件事：AI 供给与成本结构还远没稳定，定价模型和产品形态都还会继续重排。",
        "sections": ["B", "D", "E"],
    },
    "https://x.com/trq212/status/2042005043289977232": {
        "title": "Thariq：Claude Code 的下一个扩散点是非技术岗位",
        "summary": "比起继续优化程序员工作流，更大的机会可能是把 agent 带进非技术团队的日常流程里。只要有人帮忙搭起前几步，效率提升就会非常可见，这其实是产品教育和默认路径设计的问题。",
        "sections": ["C", "D"],
    },
    "https://x.com/amasad/status/2042133509939298511": {
        "title": "Amjad Masad：个人 builder 正在被赋予“整支团队”级能力",
        "summary": "Replit 这句宣传话术背后是真正的创业结构变化：当一个人就能调用接近团队规模的产能，bootstrapped business 的速度、边界和竞争方式都会重新定义。",
        "sections": ["B", "D"],
    },
    "https://x.com/rauchg/status/2041957973531226372": {
        "title": "Guillermo Rauch：AI Gateway 卖的是稳定性，不只是转发能力",
        "summary": "无停机、去锁定、免密钥、默认不训练，这些卖点说明基础设施层已经开始围绕“安心感”设计产品。模型越来越像可替换供应商，而治理与可靠性正在前置成核心价值。",
        "sections": ["A", "E"],
    },
    "https://x.com/rauchg/status/2041883605711122488": {
        "title": "Guillermo Rauch：Web 会成为 AI 原生界面的主场",
        "summary": "把浏览器视作 IDE、把 WebGPU/WebAssembly 视作性能底座，再往上推到生成式 UI，这是一条完整判断链。它意味着下一波 AI 产品创新未必先长在 App 里，而会先长在 Web 上。",
        "sections": ["A", "C", "D"],
    },
    "https://x.com/alexalbert__/status/2041941720611614786": {
        "title": "Alex Albert：Managed Agents 把“周末原型”和“生产级部署”接到了一起",
        "summary": "过去很多 agent 项目死在自建基础设施上。现在托管式 agent 的吸引力在于，你还能保留 harness、tools 和 skills 的灵活度，但不用自己扛 self-hosting 的复杂性。",
        "sections": ["A", "E"],
    },
    "https://x.com/levie/status/2041975669928702370": {
        "title": "Aaron Levie：知识工作里的后台 agent 已经可以直接接业务流",
        "summary": "把 Box API、MCP 和 Claude Managed Agents 接起来之后，文档审阅、数据抽取和系统对接开始变成几分钟就能搭好的能力。这不是 demo，而是在把 agent 塞回企业原有内容栈。",
        "sections": ["C", "E"],
    },
    "https://x.com/nikunj/status/2042020992969744702": {
        "title": "Nikunj Kothari：个人知识库正在从归档库变成 AI 生成式出版物",
        "summary": "LLMwiki 用推文、书签、聊天记录和个人写作做输入，再让 AI 自动长出文章和前端呈现。重要的不是又一个 wiki，而是“多源私有数据 + 生成式表达”正在变成个人产品的新模板。",
        "sections": ["C", "D"],
    },
    "https://x.com/steipete/status/2042017534816231486": {
        "title": "Peter Steinberger：评测系统先要解决评委偏差",
        "summary": "他在做 character eval 时发现 Claude 会偏向给自己打第一，于是先把模型名从 judge 里移掉。这个细节很关键，说明 eval 工程的难点已经从“有没有 benchmark”转向“评委本身有没有偏”。",
        "sections": ["E"],
    },
    "https://x.com/danshipper/status/2041903948873777629": {
        "title": "Dan Shipper：当每个人都有 agent，组织会长出一张并行的 AI 组织图",
        "summary": "Every 的经验很有价值：agent 会逐渐带上主人的风格，公开协作场景会自然形成“先问 agent 再找人”的礼仪，而管理层也会被迫重新学习如何分配任务、公开记忆和处理代理行为。",
        "sections": ["B", "D"],
    },
    "https://x.com/adityaag/status/2041985720706122070": {
        "title": "Aditya Agarwal：AI coding 正在反过来塑造团队",
        "summary": "当整个团队都开始每周写代码，变化不只是效率提升，而是自动化意识、响应延迟、角色边界和目标野心一起被重写。工具先被团队采用，然后工具开始改造团队本身。",
        "sections": ["B", "D", "E"],
    },
    "https://www.anthropic.com/engineering/managed-agents": {
        "title": "Anthropic Engineering：把 agent 的脑、手和会话彻底拆开",
        "summary": "这篇工程文最重要的判断不是又一个架构图，而是 session、harness、sandbox 必须解耦，接口需要比实现活得更久。托管 agent 想规模化，首先要摆脱“单容器宠物机”的运维思路。",
        "sections": ["A", "E"],
    },
    "https://claude.com/blog/claude-managed-agents": {
        "title": "Claude Blog：Managed Agents 正在把 agent infra 产品化",
        "summary": "从沙箱、鉴权、状态、检查点到 tracing，过去要团队自己搭的那一堆重活，现在被压缩成托管平台能力。对 builder 来说，这意味着可以把更多精力放到用户体验和任务设计，而不是底层搬砖。",
        "sections": ["A", "E"],
    },
    "https://www.youtube.com/playlist?list=PLuMcoKK9mKgHtW_o9h5sGO2vXrffKHwJL": {
        "title": "AI & I by Every：EBM 想补上 LLM 在高正确性场景里的短板",
        "summary": "这期访谈围绕一个很硬的命题展开：如果 AI 要进入芯片、硬件、金融或其他 mission-critical 系统，光靠会生成的 LLM 还不够，还需要更可验证、可纠错、可证明的推理结构。Logical Intelligence 试图把 EBM 与 LLM 结合，去补齐“能不能信它”的那一层。",
        "sections": ["A", "D", "E"],
    },
    "https://x.com/rauchg/status/2044445445636972578": {
        "title": "Guillermo Rauch：每个团队都会长出自己的 design factory",
        "summary": "Rauch 借 Shader Lab 这类案例讲得很直接：现在更容易的路径，已经不是去采购 SaaS，而是用 Claude Code、Three.js、Next.js 和现成底座把内部工具重新拼出来。对 builder 来说，这意味着团队会越来越像拥有一套持续制造软件的工厂，而不是一堆孤立工具的买家。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "https://x.com/levie/status/2044621545348481285": {
        "title": "Aaron Levie：AI 会自动化一段流程，但会把瓶颈推到下一段人工环节",
        "summary": "Levie 的判断很务实：AI 提高某一段产出后，新的约束很快会出现在法律、安全、销售、医疗等仍需要人判断的环节。更多代码会带来更多安全问题，更多 AI 外呼会带来更多真实对话，竞争也会逼着公司把这些新增环节一起补齐，所以很多岗位不会消失，而是会在新瓶颈处重新膨胀。",
        "sections": ["B", "D", "E"],
    },
    "https://x.com/steipete/status/2044423791405924562": {
        "title": "Peter Steinberger：agent harness 的安全加固正在从可选项变成基本盘",
        "summary": "面对 GPT 5.4-Cyber 这类更强的逆向与攻击能力，Steinberger 强调开源 agent 项目不能再把安全当成附属工程。快速迭代、代码加固、公开 advisory 和持续被安全团队找洞，都会逐渐成为这类基础设施可信与否的分水岭。",
        "sections": ["A", "D", "E"],
    },
    "https://x.com/swyx/status/2044542494420214217": {
        "title": "Swyx：subagents 只是优化题，能组合和管理 agent 的 boss agent 才是能力题",
        "summary": "这条把今年 agent 讨论往前推了一步。subagents 更像并行化与调度优化，而真正更难的是让 agent 能彼此组合、被上层 agent 查询和管理，也就是从“多开几个工人”升级到“出现真正的管理层”。这会决定下一代 agent 工作台到底只是更快，还是出现新能力边界。",
        "sections": ["A", "C", "D", "E"],
    },
    "https://x.com/joshwoodward/status/2044452201947627709": {
        "title": "Josh Woodward：Gemini 原生登陆 Mac，小团队百日堆出 100+ 功能",
        "summary": "Gemini on Mac 传递出的信号不只是又一个桌面客户端，而是大模型产品正在认真争夺本地默认入口。100% 原生 Swift、不到 100 天堆出 100 多个功能，也说明这些团队已经把桌面端视为高频工作界面，而不是网页之外的附属壳层。",
        "sections": ["A", "C", "E"],
    },
    "https://x.com/nikunj/status/2044489137542332717": {
        "title": "Nikunj Kothari：真正耗时的不是生成代码，而是把系统想清楚",
        "summary": "Nikunj 进一步补充了他对 vibe coding 的判断：给 Claude Code 一张系统图，很多实现确实可以一把过；但问题在于，形成那张系统图前的澄清、取舍和长期思考，今天的 AI 还代替不了。对 builder 来说，清晰度、深度和坚持仍然是决定系统质量的稀缺资产。",
        "sections": ["B", "C", "D", "E"],
    },
    "https://x.com/steipete/status/2044482797449150520": {
        "title": "Peter Steinberger：开放式 agent 经过四个月补课后才开始长出像样的安全模型",
        "summary": "这条更新把“能跑”与“能上线”之间的差距说得很明白：真正的 agent 产品需要沙箱、allow-list、逐次执行授权和被安全研究员持续压力测试。短短几个月补进数千小时工作量，说明开放式 agent 的权限体系还在快速成形期。",
        "sections": ["A", "D", "E"],
    },
    "https://x.com/zarazhangrui/status/2044515052435476685": {
        "title": "Zara Zhang：在 AI 时代，play 本身就是正经工作",
        "summary": "她把很多 builder 心里模糊的感受说清楚了：所谓“玩模型”，不是浪费时间，而是用非功利方式去碰能力边界、找意外反馈、积累直觉。很多真正有产品价值的发现，往往不是从明确 KPI 出发，而是从好奇心驱动的试错里长出来。",
        "sections": ["B", "C", "D"],
    },
    "https://x.com/swyx/status/2044598788065731017": {
        "title": "Swyx：Meta 的 AI 叙事开始从翻车转向平台级反攻",
        "summary": "Swyx 用几条线索把 Meta 最近的动向串了起来：继续招人、扎克回到一线写代码、推出更强模型、并收购 Dreamer 和 Manus 去补 AI OS 的 prosumer 层。重点不在某个单品，而在大公司是否会重新用组织、资本和分发能力把 AI 平台层卷回来。",
        "sections": ["A", "B", "D"],
    },
    "https://x.com/petergyang/status/2044418914856353901": {
        "title": "Peter Yang：中国之行提醒产品 builder 重新理解供给效率与工作节奏",
        "summary": "这条不是常规意义上的 AI 产品发布，而是一种一线观察：当你看到中国的 AI 工作文化、极致履约效率、电动车普及和日常生活组织方式，会更直观地理解为什么某些产品节奏、成本结构和用户预期会长成今天这样。对创业者来说，这类现场感知往往比二手观点更有用。",
        "sections": ["B", "C", "D"],
    },
    "https://x.com/amasad/status/2044437437141909609": {
        "title": "Amjad Masad：开源包可能需要像 star 一样可见的 security-compute 指标",
        "summary": "如果前沿模型可以大规模自动找漏洞，那么开源生态下一步缺的就不只是 CVE 列表，而是“到底投入了多少算力在持续加固这个包”的可见信号。Amjad 提出的 security-compute 指标很值得记住，它把信任问题从静态声誉拉向持续投入与可验证防护。",
        "sections": ["A", "D", "E"],
    },
}

CURATED_TITLE_OVERRIDES = {
    "Scaling Global Organizations in the Age of AI with ServiceNow CEO Bill McDermott": {
        "title": "No Priors：ServiceNow CEO 谈 AI 时代的全球组织与企业平台韧性",
        "summary": "Bill McDermott 的访谈提醒大家，企业 AI 不是把一个 SaaS 平台简单替换成 LLM。真正的成本包括迁移平台、重建流程、GPU 与 token 开销、错误容忍度和组织执行力。对 enterprise builder 来说，AI 机会很大，但落地逻辑仍然要尊重客户、流程和平台韧性。",
        "sections": ["A", "B", "D"],
    },
    "Marc Andreessen introspects on The Death of the Browser, Pi + OpenClaw, and Why &quot;This Time Is Different&quot;": {
        "title": "Latent Space：浏览器是否会被 AI 重写，正在从边缘话题变成主流判断",
        "summary": "这期讨论把几个本来分散的话题拉到了一起看：浏览器的角色是否会被 agent 改写，OpenClaw/Pi 这类入口形态为什么重要，以及为什么很多人开始认真相信“这次确实不一样”。它背后的核心问题是，AI 时代的默认计算界面到底会长成什么样。",
        "sections": ["A", "C", "D"],
    },
    "The Agentic Economy: How AI Agents Will Transform the Financial System with Circle Co-Founder and CEO Jeremy Allaire": {
        "title": "No Priors：agentic economy 开始深入支付与金融基础设施",
        "summary": "这期访谈最值得关注的不是泛泛而谈金融 AI，而是把 agent、支付、稳定币和区块链执行层放在一起讨论。它提醒我们：下一波 agent 应用不只会改写知识工作，也会改写资金如何流动与结算。",
        "sections": ["A", "B", "C", "D", "E"],
    },
    "Ep 84: OpenAI’s Chief Scientist on Continual Learning Hype, RL Beyond Code, &amp; Future Alignment Directions": {
        "title": "Unsupervised Learning：OpenAI 首席科学家谈长期 agent、RL 外溢与 alignment",
        "summary": "这期的核心线索是：coding agent 的爆发被视为更长时自主研究系统的前奏，而下一步难点会落在长期任务、部分进展评估、RL 在非代码领域的泛化，以及更具体的 alignment 工程路径上。",
        "sections": ["A", "B", "D", "E"],
    },
}


def load_bundle() -> dict:
    if not BUNDLE_PATH.exists():
        raise FileNotFoundError(f"Bundle not found: {BUNDLE_PATH}")
    return json.loads(BUNDLE_PATH.read_text())


def format_generated_at(iso_value: str | None) -> str:
    if not iso_value:
        return "unknown"
    normalized = iso_value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def shorten(text: str, limit: int = 90) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_feed_status(bundle: dict) -> dict:
    feeds = bundle.get("feeds", {})
    stats = bundle.get("stats", {})
    issues = []

    x_items = feeds.get("x", {}).get("x", [])
    podcast_items = feeds.get("podcasts", {}).get("podcasts", [])
    blog_items = feeds.get("blogs", {}).get("blogs", [])

    if not x_items:
        issues.append("X feed returned 0 items on this run.")
    if not podcast_items:
        issues.append("Podcast feed returned 0 items on this run.")
    elif stats.get("podcast_count", 0) < 5:
        issues.append(f"Podcast feed returned only {stats.get('podcast_count', 0)} item(s) on this run.")
    if not blog_items:
        issues.append("Blogs feed returned 0 items on this run.")
    elif stats.get("blog_count", 0) < 5:
        issues.append(f"Blogs feed returned only {stats.get('blog_count', 0)} item(s) on this run.")

    return {
        "xFeedLoaded": "x" in feeds,
        "podcastFeedLoaded": "podcasts" in feeds,
        "blogFeedLoaded": "blogs" in feeds,
        "issues": issues,
    }


def feed_issues_cn(feed_status: dict) -> str:
    issues = feed_status.get("issues", [])
    if not issues:
        return "所有 feed 均正常"

    translated = []
    for issue in issues:
        if issue == "X feed returned 0 items on this run.":
            translated.append("X feed 本轮返回 0 条")
        elif issue == "Podcast feed returned 0 items on this run.":
            translated.append("播客 feed 本轮返回 0 条")
        elif issue == "Blogs feed returned 0 items on this run.":
            translated.append("博客 feed 本轮返回 0 条")
        elif issue.startswith("Podcast feed returned only "):
            count = re.search(r"(\d+)", issue)
            translated.append(f"播客 feed 本轮仅返回 {count.group(1) if count else '?'} 条")
        elif issue.startswith("Blogs feed returned only "):
            count = re.search(r"(\d+)", issue)
            translated.append(f"博客 feed 本轮仅返回 {count.group(1) if count else '?'} 条")
        else:
            translated.append(issue)

    return "；".join(translated)


LOW_SIGNAL_PATTERNS = [
    "broadway",
    "cabaret",
    "limited seating",
    "fumbled lyrics",
    "most hated company in the world",
    "neet practice tests",
    "vicha ratanapakdee",
    "slack propaganda",
    "lazy no effort",
    "maps theory of twitter",
    "free to try right now",
    "download or update the claude desktop app",
    "this release makes me unreasonably happy",
    "agents are going to use software 100x more than people will in the future",
    "vancouver, it’s been a blast",
    "vancouver, it's been a blast",
    "it&apos;s neck and neck lol",
    "it's neck and neck lol",
    "wow and a colossus profile",
    "excited for this https",
]


def is_low_signal(item: dict) -> bool:
    text = clean_text((item.get("originalTitle") or "") + " " + (item.get("originalText") or "")).lower()
    return any(pattern in text for pattern in LOW_SIGNAL_PATTERNS)


def extract_sources(bundle: dict) -> list[dict]:
    extracted: list[dict] = []

    for builder in bundle.get("feeds", {}).get("x", {}).get("x", []):
        for tweet in builder.get("tweets", []):
            extracted.append(
                {
                    "type": "x",
                    "source": "x",
                    "author": builder.get("name"),
                    "handle": builder.get("handle"),
                    "publishedAt": tweet.get("createdAt"),
                    "url": tweet.get("url"),
                    "originalTitle": None,
                    "originalText": tweet.get("text"),
                    "likes": tweet.get("likes", 0),
                    "retweets": tweet.get("retweets", 0),
                    "replies": tweet.get("replies", 0),
                }
            )

    for item in bundle.get("feeds", {}).get("podcasts", {}).get("podcasts", []):
        extracted.append(
            {
                "type": "podcast",
                "source": item.get("source"),
                "author": item.get("name"),
                "handle": None,
                "publishedAt": item.get("publishedAt"),
                "url": item.get("url"),
                "originalTitle": item.get("title"),
                "originalText": item.get("transcript") or item.get("description"),
                "likes": 0,
                "retweets": 0,
                "replies": 0,
            }
        )

    for item in bundle.get("feeds", {}).get("blogs", {}).get("blogs", []):
        extracted.append(
            {
                "type": "blog",
                "source": item.get("source") or item.get("name"),
                "author": item.get("name"),
                "handle": None,
                "publishedAt": item.get("publishedAt"),
                "url": item.get("url"),
                "originalTitle": item.get("title"),
                "originalText": item.get("content") or item.get("description"),
                "likes": 0,
                "retweets": 0,
                "replies": 0,
            }
        )

    return extracted


def infer_sections(text: str, item_type: str) -> list[str]:
    lowered = text.lower()
    sections = [
        key for key, keywords in SECTION_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]

    if not sections:
        if item_type == "blog":
            sections = ["A", "E"]
        elif item_type == "podcast":
            sections = ["B", "D"]
        else:
            sections = ["A", "C"]

    return sections


def generic_title(item: dict) -> str:
    author = item.get("author") or "Unknown"
    text = clean_text(item.get("originalTitle") or item.get("originalText"))
    if not text:
        return f"{author}：值得关注的一条更新"
    return f"{author}：{shorten(text, 36)}"


def generic_summary(item: dict, sections: list[str]) -> str:
    text = clean_text((item.get("originalTitle") or "") + " " + (item.get("originalText") or ""))
    lowered = text.lower()

    if "notebook" in lowered:
        return "Notebook 能力正在从独立产品并回主应用，说明 AI 工具在把聊天、资料、长期上下文和项目组织整合成一个工作台。"
    if "managed agents" in lowered:
        return "托管式 agent 的重心已经从“能不能跑”转到“能不能省掉运维、权限、状态和 tracing 的重活”，平台化速度明显在加快。"
    if "gateway" in lowered or "lock-in" in lowered:
        return "基础设施层开始把稳定性、去锁定和治理能力当成核心卖点，builder 购买的不是一次调用，而是更稳的运行边界。"
    if "webgpu" in lowered or "webassembly" in lowered or "browser" in lowered:
        return "Web 技术栈正在重新成为 AI 产品的主舞台，浏览器、WebGPU 和生成式 UI 之间的组合值得继续跟踪。"
    if "subscription" in lowered or "local model" in lowered or "local models" in lowered:
        return "AI 订阅和本地模型路线被一起讨论，说明成本结构、供给约束和产品定价仍在快速重排。"
    if "non-technical" in lowered:
        return "真正的大规模扩散点往往不是更强的程序员工具，而是让非技术岗位也能把 agent 接进日常流程。"
    if "solo" in lowered or "bootstrapped" in lowered:
        return "当个人 builder 可以调用接近团队规模的能力，创业门槛和组织结构会继续被压薄。"
    if "slack" in lowered or "organization" in lowered or "team" in lowered:
        return "这条内容最值得看的地方，是 agent 如何改变团队礼仪、信息流和责任分配，而不只是单点提效。"
    if "eval" in lowered or "judge" in lowered:
        return "评测工程正在从“做不做 benchmark”走向“如何降低评委偏差并提高结果可信度”。"
    if "code" in lowered or "coding" in lowered:
        return "AI coding 已经不只是提效小技巧，它开始反过来改造团队分工、工作节奏和 ambition 上限。"

    if "A" in sections and "E" in sections:
        return "这条更新指向同一个方向：工具能力和运行基础设施正在一起成熟，builder 可以把更多精力放到实际任务而不是底层折腾上。"
    if "B" in sections and "D" in sections:
        return "它更像一条组织与产业信号，而不是单一功能发布，值得从结构变化而非短期热度去理解。"
    if "C" in sections:
        return "这条内容对产品团队的启发在于，真正的差异化正在长在工作流细节和默认交互路径里。"
    return "这条更新虽然表达简短，但背后反映的是 builder 对产品、组织或工程边界的重新定义。"


def score_item(item: dict, sections: list[str]) -> float:
    text = clean_text((item.get("originalTitle") or "") + " " + (item.get("originalText") or ""))
    base = min(len(text), 800) / 80
    engagement = min(item.get("likes", 0), 5000) / 500
    bonuses = 0.0
    if item["type"] == "blog":
        bonuses += 4.0
    elif item["type"] == "podcast":
        bonuses += 3.5
    if len(sections) >= 2:
        bonuses += 1.2
    return base + engagement + bonuses


def lookup_override(item: dict) -> dict | None:
    title_override = CURATED_TITLE_OVERRIDES.get(item.get("originalTitle"))
    if title_override:
        return title_override

    url = item.get("url")
    url_override = CURATED_OVERRIDES.get(url)
    if item.get("type") == "podcast" and url_override:
        # Podcast feeds sometimes expose a channel or playlist URL for each new
        # episode. Do not let an old episode summary stick to a new transcript.
        if "youtube.com/@" in url or "playlist?" in url:
            return None
    return url_override


def normalize_item(item: dict) -> dict:
    override = lookup_override(item)
    text = clean_text((item.get("originalTitle") or "") + " " + (item.get("originalText") or ""))
    sections = override["sections"] if override else infer_sections(text, item["type"])
    title = override["title"] if override else generic_title(item)
    summary = override["summary"] if override else generic_summary(item, sections)
    priority_boost = 8.0 if override else 0.0
    return {
        **item,
        "title": title,
        "summary": summary,
        "sections": sections,
        "score": score_item(item, sections) + priority_boost,
    }


def select_items(normalized_items: list[dict]) -> list[dict]:
    section_counts = {key: 0 for key in SECTION_TITLES}
    chosen_urls: set[str] = set()
    selected: list[dict] = []
    candidates = []
    for item in normalized_items:
        text = clean_text((item.get("originalTitle") or "") + " " + (item.get("originalText") or ""))
        if is_low_signal(item):
            continue
        if item["url"] not in CURATED_OVERRIDES and len(text) < 60:
            continue
        candidates.append(item)
    candidates.sort(key=lambda item: item["score"], reverse=True)

    while True:
        underfilled = {key for key, count in section_counts.items() if count < 5}
        if not underfilled:
            break

        best = None
        best_gain = 0
        for item in candidates:
            if item["url"] in chosen_urls:
                continue
            gain = sum(1 for section in item["sections"] if section in underfilled)
            if gain > best_gain or (gain == best_gain and best is not None and item["score"] > best["score"]):
                best = item
                best_gain = gain

        if not best or best_gain == 0:
            break

        selected.append(best)
        chosen_urls.add(best["url"])
        for section in best["sections"]:
            section_counts[section] += 1

    if len(selected) < 12:
        for item in candidates:
            if item["url"] in chosen_urls:
                continue
            selected.append(item)
            chosen_urls.add(item["url"])
            if len(selected) >= 12:
                break

    return selected


def build_manifest(bundle: dict) -> dict:
    normalized = [normalize_item(item) for item in extract_sources(bundle)]
    selected = select_items(normalized)

    return {
        "generatedAt": bundle.get("generatedAt"),
        "sourceBundleStats": bundle.get("stats", {}),
        "feedStatus": build_feed_status(bundle),
        "selectedSourceCount": len(selected),
        "selectedSources": [
            {
                "type": item["type"],
                "source": item.get("source"),
                "author": item.get("author"),
                "handle": item.get("handle"),
                "publishedAt": item.get("publishedAt"),
                "url": item.get("url"),
                "title": item["title"],
                "summary": item["summary"],
                "sections": [SECTION_TITLES[key] for key in item["sections"]],
                "originalTitle": item.get("originalTitle"),
                "originalText": item.get("originalText"),
            }
            for item in selected
        ],
    }


def build_markdown(manifest: dict) -> str:
    items_by_section = {key: [] for key in SECTION_TITLES}
    for item in manifest["selectedSources"]:
        for section_key, section_title in SECTION_TITLES.items():
            if section_title in item["sections"]:
                items_by_section[section_key].append(item)

    issue_line = feed_issues_cn(manifest.get("feedStatus", {}))

    lines = [
        "# AI Builders Digest 5 Briefs",
        "",
        f"生成时间：{format_generated_at(manifest.get('generatedAt'))}",
        "",
        (
            "本次抓取摘要："
            f"X 共 {manifest['sourceBundleStats'].get('tweet_count', 0)} 条推文，"
            f"播客 {manifest['sourceBundleStats'].get('podcast_count', 0)} 条，"
            f"博客 {manifest['sourceBundleStats'].get('blog_count', 0)} 条。"
            f"Feed 状态：{issue_line}。"
        ),
        "",
    ]

    for section_key, section_title in SECTION_TITLES.items():
        lines.append(f"## {section_title}")
        lines.append(SECTION_INTROS[section_key])
        lines.append("")
        for index, item in enumerate(items_by_section[section_key], start=1):
            lines.append(f"{index}. **{item['title']}**")
            lines.append(f"   {item['summary']} 来源：{item['author']}。")
        lines.append("")

    lines.extend(
        [
            "---",
            f"source manifest saved path: {MANIFEST_PATH}",
            f"markdown digest saved path: {MARKDOWN_PATH}",
            f"total selected source count: {manifest['selectedSourceCount']}",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    bundle = load_bundle()
    manifest = build_manifest(bundle)
    markdown = build_markdown(manifest)
    MARKDOWN_PATH.write_text(markdown)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
