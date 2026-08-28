# 紫微斗数排盘 Skill

一个同时面向 Codex 和 Claude Code 的开源紫微斗数 Agent Skill。项目遵循
[Agent Skills 开放格式](https://agentskills.io)，使用固定版本的
[`iztro`](https://github.com/SylarLong/iztro) 完成确定性排盘，并提供命盘校验、流派口径对照、
大限流年及专题解读的工作流程。

> [!IMPORTANT]
> **请理性看待紫微斗数。** 紫微斗数属于传统文化与民俗研究范畴，尚无可靠科学证据证明它能准确预测个人命运。
> 本项目的输出只适合文化研究、娱乐和自我反思，不应替代现实调查、独立判断或专业意见。
> 请勿依据命盘独自作出医疗、心理、法律、投资、婚姻、升学或职业等重大决定。

## 项目特点

- 通过脚本排盘，避免语言模型凭记忆计算星曜、宫位和四化。
- 支持公历、农历、闰月、具体时间及早子时/晚子时。
- 支持通行版与中州派，以及天盘、地盘和人盘选项。
- 输出十二宫、主辅杂曜、生年四化、大限与指定日期流年。
- 支持 Markdown 和 JSON，方便人工阅读或程序继续处理。
- Python 自动生成事业、财运、身心、感情、整体和学业六类事实包。
- 提供确定性规则解盘 CLI，支持事业、财帛、姻缘及双方姻缘合盘。
- 出生时间未知时，可比较早子至晚子共 13 个候选时辰。
- 同一份 `SKILL.md` 可供 Codex 和 Claude Code 使用，无需维护两套提示词。
- 提供黄金用例和自动化测试，便于检查升级后的排盘一致性。
- 不依赖外部算命 API，也不需要任何 API Key。

## 使用前须知

排盘结果会受到出生时间、历法换年、晚子时归日、闰月处理和流派算法等因素影响。不同软件结果不一致时，
应先核对参数与算法口径，不宜简单判断某一方“绝对正确”。接近时辰边界的出生时间，还应考虑真太阳时造成的跨时辰可能。

解读时应区分三类内容：

1. 脚本计算出的命盘结构；
2. 传统紫微斗数体系中的象征性解释；
3. 结合个人经历作出的推断。

后两者都不是经过科学验证的事实，更不代表事件必然发生。好的使用方式是把结果当作一种提问和反思框架，
再回到现实证据、个人选择与可执行行动上。

## 环境要求

- Node.js 18 或更高版本
- Python 3.10 或更高版本
- npm

## 安装

```bash
git clone https://github.com/tsuki8/ziweidoushu-skill.git
cd ziweidoushu-skill
npm install
```

只使用命令行排盘时，克隆到任意目录即可。作为 Agent Skill 使用时，请继续参阅下方的
[Codex 与 Claude Code](#codex-与-claude-code) 安装说明。

## 快速开始

使用公历和具体出生时间排盘：

```bash
node scripts/ziwei_pan.mjs \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --target-date 2025-01-01
```

使用农历和时辰排盘：

```bash
node scripts/ziwei_pan.mjs \
  --lunar 2000-07-17 \
  --shichen 寅 \
  --sex 女
```

输出机器可读的 JSON：

```bash
node scripts/ziwei_pan.mjs \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --format json
```

使用中州派天盘：

```bash
node scripts/ziwei_pan.mjs \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --algorithm zhongzhou \
  --astro-type heaven
```

查看全部参数：

```bash
node scripts/ziwei_pan.mjs --help
```

自动生成六大主题事实包：

```bash
python3 scripts/ziwei_auto.py \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --target-date 2025-01-01
```

省略出生时间时，自动切换为 13 个候选时辰比较：

```bash
python3 scripts/ziwei_auto.py \
  --solar 2000-08-16 \
  --sex 女
```

### 事业、财帛和姻缘解盘

`ziwei_interpret.py` 是不调用外部模型的规则解盘程序。它复用同一排盘引擎，并将脚本事实、传统解释、
现实建议和证据分开输出：

```bash
python3 scripts/ziwei_interpret.py \
  --topic 事业 \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --target-date 2026-08-28
```

`--topic` 支持：

- `事业` / `career`
- `财帛`、`财运` / `wealth`
- `姻缘`、`感情` / `relationship`
- `合盘` / `compatibility`

如需机器可读结果，添加 `--format json`；如需保存，添加 `--output result.md`。

### 姻缘合盘

合盘需要两人的完整出生时间和性别。第二人的参数统一使用 `--partner-*` 前缀；由于涉及第三方资料，
还必须用 `--partner-consent` 确认已经获得对方许可：

```bash
python3 scripts/ziwei_interpret.py \
  --topic 合盘 \
  --solar 2000-08-16 --hour 03:30 --sex 女 --label 甲方 \
  --partner-solar 1998-12-20 \
  --partner-hour 14:20 \
  --partner-sex 男 \
  --partner-label 乙方 \
  --partner-consent \
  --target-date 2026-08-28
```

程序比较双方单盘关系结构、需求与表达方式、生年四化跨盘映射和宫位地支辅助信号，不生成匹配分数，
也不判断“唯一正缘”或保证婚期。

## Codex 与 Claude Code

Codex 和 Claude Code 都能读取包含 `SKILL.md`、脚本和引用资料的 Agent Skill。本仓库使用共同的
`SKILL.md` 作为唯一事实源；`agents/openai.yaml` 只补充 Codex 的界面元数据，不影响 Claude Code。

### Codex

个人 Skill 默认安装到 `~/.agents/skills/`：

```bash
git clone https://github.com/tsuki8/ziweidoushu-skill.git \
  ~/.agents/skills/ziwei-skill
npm install --prefix ~/.agents/skills/ziwei-skill
```

在 Codex CLI 或 IDE 扩展中输入 `$ziwei-skill` 显式调用，也可以直接描述排盘需求让 Codex 自动匹配。
如果新增 Skill 后未出现，请重新启动 Codex。详细机制参见
[Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills)。

### Claude Code

个人 Skill 默认安装到 `~/.claude/skills/`：

```bash
git clone https://github.com/tsuki8/ziweidoushu-skill.git \
  ~/.claude/skills/ziwei-skill
npm install --prefix ~/.claude/skills/ziwei-skill
```

在 Claude Code 中输入 `/ziwei-skill` 显式调用，也可以直接描述排盘需求让 Claude 自动匹配。
详细机制参见 [Claude Code Skills 文档](https://code.claude.com/docs/en/skills)。

### 同时供两者使用

希望只维护一份克隆时，可将仓库放在任意固定目录，再把该目录链接到两个 Skill 目录。以下是 macOS/Linux 示例：

```bash
mkdir -p ~/.agents/skills ~/.claude/skills
ln -s /absolute/path/to/ziweidoushu-skill ~/.agents/skills/ziwei-skill
ln -s /absolute/path/to/ziweidoushu-skill ~/.claude/skills/ziwei-skill
```

Windows 用户可以分别克隆，或使用目录联接。不要把同一目录复制后分别修改；否则两个 Agent 会逐渐使用不同规则。

### 示例请求

Codex：

```text
使用 $ziwei-skill，按明确的算法口径为我排紫微斗数命盘。
请先列出排盘参数和命盘事实，再进行传统文化层面的解释，并提醒我理性参考。
```

Claude Code：

```text
/ziwei-skill 按明确的算法口径为我排紫微斗数命盘。
请先列出排盘参数和命盘事实，再进行传统文化层面的解释，并提醒我理性参考。
```

Skill 会要求完整的日期、出生时辰和性别。出生城市主要用于接近时辰边界时核对真太阳时；不需要姓名等无关信息。

## 账户登录与 API Key

本仓库不读取 Codex 或 Claude Code 的账户凭据，也不直接调用 OpenAI 或 Anthropic API。账户/API Key
只用于认证你选择的 Agent 客户端；排盘和测试始终在本地执行。

Codex 支持 ChatGPT 账户登录和 OpenAI API Key：

```bash
# ChatGPT 账户
codex login

# 已在当前安全环境中设置 OPENAI_API_KEY 时
printenv OPENAI_API_KEY | codex login --with-api-key
```

Claude Code 支持 Claude.ai 账户、Claude Console 和 Anthropic API Key：

```bash
# Claude.ai/Console 账户
claude auth login

# API Key 由当前 Shell、密钥管理器或 CI 注入
claude
```

使用 Claude API Key 时设置 `ANTHROPIC_API_KEY`；它会优先于已有的订阅账户登录。认证细节参见
[Codex Authentication](https://learn.chatgpt.com/docs/auth) 和
[Claude Code Authentication](https://code.claude.com/docs/en/authentication)。不要把 API Key、认证缓存或真实个案数据提交到仓库。

## JSON 与程序集成

不使用任何 AI 账户，也可以把排盘脚本当作本地确定性 CLI 接口：

```bash
node scripts/ziwei_pan.mjs \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --target-date 2025-01-01 \
  --format json

python3 scripts/ziwei_auto.py \
  --solar 2000-08-16 \
  --hour 03:30 \
  --sex 女 \
  --format json
```

Node 入口返回完整命盘、全部大限和目标日期的流年、流月、流日、流时；Python 入口返回适合 Agent
继续处理的精简事实包。两者当前都输出 `schemaVersion: "1.0"`。新增字段按向后兼容方式加入，调用方仍应保留
未知字段并检查 `schemaVersion`。

规则解盘入口同样输出 `schemaVersion: "1.0"`。单盘结果使用 `mode: "interpretation"`，合盘使用
`mode: "compatibility"`；每条 `finding` 都包含 `fact`、`traditionalInterpretation`、`practicalNote`
和 `evidence`，便于调用方区分证据层级。

## 测试

```bash
npm test
```

测试覆盖黄金用例、公历与农历等价、早晚子时、目标日期全部运限、13 时辰比较、六大主题事实包、
事业/财帛/姻缘规则解盘及双方合盘，以及：

- 通行版与中州派；
- 天盘、地盘和人盘；
- 正月/立春换年；
- 农历月/节气运限分界；
- 自然年/生日虚岁分界；
- 晚子时归当日/次日；
- 闰月调整开关。

## 隐私与安全

- 项目不调用外部算命 API，排盘在本机完成。
- 脚本不会主动上传或持久化出生资料。
- Agent 客户端的账户登录与 API Key 只负责模型访问，不会改变本地排盘算法。
- 不要将真实个案、聊天记录、API Key、`auth.json`、`.credentials.json` 或其他敏感信息提交到公开仓库。
- 命令行参数可能被终端历史记录保存；对隐私要求较高时，请同时留意本机的 Shell 历史设置。
- 健康相关内容只能视为传统文化象征，不用于诊断疾病或预测寿命。

## 项目结构

```text
.
├── SKILL.md                     # Skill 工作流程与安全边界
├── agents/openai.yaml           # Skill 展示信息
├── references/
│   ├── calculation.md           # 排盘口径、算法和黄金用例
│   ├── interpretation.md        # 解读框架与专题规则
│   └── supplementary.md         # 补充体系、隐私与安全边界
├── scripts/
│   ├── ziwei_pan.mjs            # 确定性排盘命令行工具
│   ├── ziwei_time_compare.mjs   # 13 时辰候选比较
│   ├── ziwei_auto.py            # 六主题自动事实包
│   ├── ziwei_interpret.py       # 事业、财帛、姻缘与合盘规则解读
│   ├── ziwei_rules.py           # 可审查的星曜词义与解盘规则表
│   ├── test_ziwei_pan.mjs       # Node 回归测试
│   ├── test_skill_metadata.mjs  # Codex/Claude Code 兼容性测试
│   ├── test_ziwei_auto.py       # Python 自动化测试
│   └── test_ziwei_interpret.py  # 规则解盘与合盘测试
└── package.json
```

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。排盘依赖 `iztro@2.6.0`，其采用 MIT License。

## 最后提醒

命盘无法替你认识一个人，也无法替你承担选择的后果。面对感情、工作、金钱和健康问题时，请优先使用可验证的信息，
咨询真正具备资质的专业人士，并保留改变计划和人生方向的主动权。
