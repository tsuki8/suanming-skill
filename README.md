# 紫微斗数排盘 Skill

一个面向 Codex/AI Agent 的开源紫微斗数 Skill。项目使用固定版本的
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
- npm

## 安装

```bash
git clone https://github.com/tsuki8/ziweidoushu-skill.git
cd ziweidoushu-skill
npm install
```

如需作为个人 Codex Skill 使用，可将仓库放入你的 Skills 目录，并确保依赖已经安装。

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

## 在 Codex 中使用

安装为 Skill 后，可以这样提出请求：

```text
使用 $ziwei-skill，按明确的算法口径为我排紫微斗数命盘。
请先列出排盘参数和命盘事实，再进行传统文化层面的解释，并提醒我理性参考。
```

Skill 会要求完整的日期、出生时辰和性别。出生城市主要用于接近时辰边界时核对真太阳时；不需要姓名等无关信息。

## 测试

```bash
npm test
```

测试覆盖公历与农历等价排盘、早晚子时、指定日期运限、中州派配置和缺失时间报错等场景。

## 隐私与安全

- 项目不调用外部算命 API，排盘在本机完成。
- 脚本不会主动上传或持久化出生资料。
- 不要将真实个案、聊天记录、API Key 或其他敏感信息提交到公开仓库。
- 命令行参数可能被终端历史记录保存；对隐私要求较高时，请同时留意本机的 Shell 历史设置。
- 健康相关内容只能视为传统文化象征，不用于诊断疾病或预测寿命。

## 项目结构

```text
.
├── SKILL.md                     # Skill 工作流程与安全边界
├── agents/openai.yaml           # Skill 展示信息
├── references/
│   ├── calculation.md           # 排盘口径、算法和黄金用例
│   └── interpretation.md        # 解读框架与专题规则
├── scripts/
│   ├── ziwei_pan.mjs            # 确定性排盘命令行工具
│   └── test_ziwei_pan.mjs       # 自动化测试
└── package.json
```

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。排盘依赖 `iztro@2.6.0`，其采用 MIT License。

## 最后提醒

命盘无法替你认识一个人，也无法替你承担选择的后果。面对感情、工作、金钱和健康问题时，请优先使用可验证的信息，
咨询真正具备资质的专业人士，并保留改变计划和人生方向的主动权。
