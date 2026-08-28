---
name: ziwei-skill
description: >
  确定性紫微斗数排盘、校盘与传统文化分析。Use when the user asks for 紫微斗数、紫微排盘、紫微命盘、
  命宫、身宫、十二宫、十四主星、四化、三方四正、大限、流年、夫妻宫、正缘、事业财运、合盘，
  or wants to compare charts from different Zi Wei Dou Shu apps or lineages. Supports solar/lunar dates,
  leap months, early/late Zi hour, common and Zhongzhou algorithms, and machine-readable chart output.
---

# 紫微斗数排盘与解读

使用确定性脚本排盘。不要让语言模型口算命身宫、星曜、四化或运限。

## 收集并确认信息

收集：

1. 公历或农历出生日期；农历注明是否闰月。
2. 精确出生时间或时辰；没有时辰时停止排盘。
3. 性别。
4. 出生城市；时间靠近时辰边界时用于真太阳时核对。
5. 分析主题：整体、事业、感情、财运、健康、某年运势或合盘。

复述关键信息并允许用户修正。已有完整信息时直接继续，不重复询问姓名等无关字段。默认当事人在世，当前日期取系统日期。

## 安装依赖

若 `node_modules/iztro` 不存在，在 Skill 根目录运行：

```bash
npm install
```

依赖固定为 MIT 开源的 `iztro@2.6.0`。不调用外部算命 API，不要求用户提供 API Key。

## 排盘

优先使用公历与具体时间：

```bash
node scripts/ziwei_pan.mjs --solar 2000-08-16 --hour 03:30 --sex 女 --target-date 2025-01-01
```

农历与子时示例：

```bash
node scripts/ziwei_pan.mjs --lunar 2000-07-17 --shichen 寅 --sex 女
node scripts/ziwei_pan.mjs --lunar 2001-04-12 --leap --shichen 子 --zi late --sex 男
```

机器可读输出：

```bash
node scripts/ziwei_pan.mjs --solar 2000-08-16 --hour 03:30 --sex 女 --format json
```

需要中州派时显式指定：

```bash
node scripts/ziwei_pan.mjs --solar 2000-08-16 --hour 03:30 --sex 女 --algorithm zhongzhou --astro-type heaven
```

运行 `node scripts/ziwei_pan.mjs --help` 查看全部参数。

## 使用排盘结果

将脚本输出的出生信息、命身宫、五行局、十二宫、十四主星、辅杂曜、生年四化、大限和目标日期运限作为唯一排盘依据。可重新排版，不得凭记忆移动星曜或覆盖四化。

出现时辰边界警告时，先核对真太阳时。无法核定时，分别运行相邻两个时辰，只说明结构差异，不把其中一个假定为事实。

按需读取：

- 排盘参数、算法口径、黄金用例或跨软件差异：`references/calculation.md`
- 宫位、主星、四化、运限和专题解读：`references/interpretation.md`

## 解读顺序

依次分析：

1. 命宫、身宫、命主、身主、五行局。
2. 命宫三方四正：命宫、迁移、财帛、官禄。
3. 生年禄、权、科、忌的落星与落宫。
4. 命、官禄、财帛、夫妻、迁移、福德六个核心宫。
5. 当前大限，再叠目标流年；目标年份必须传 `--target-date` 生成。
6. 提出 3–5 个已发生年份供用户校准，再收窄未来判断。

不要单宫单星下结论。空宫借看对宫，并检查三方四正、辅曜、煞曜与四化。

## 专题规则

### 正缘与感情

以夫妻宫为核心，结合命宫、福德、官禄、迁移、本命四化、当前大限和流年。描述适配关系模式、对象倾向和较活跃窗口，不声称能锁定唯一对象、姓名、长相或必然结婚年份。

### 事业与财运

事业以官禄宫为核心，结合命宫、财帛、迁移和身宫。财运以财帛宫为核心，结合官禄、田宅、福德和四化。区分长期能力结构与阶段性触发。

### 健康

只讨论传统文化中的压力与生活习惯象征，不诊断疾病、不预测寿命，明确建议以医学专业意见为准。

## 对照其他软件

先收集对方软件名称、命宫、身宫、五行局、十四主星和四化截图。逐项比较：

- 通行版或中州派；
- 天盘、地盘或人盘；
- 四化与亮度表；
- 闰月处理；
- 正月初一或立春换年；
- 晚子时归日；
- 真太阳时。

若参数不同，报告“口径差异”，不要称任一方绝对错误。

## 验证

修改脚本、依赖或排盘口径后运行：

```bash
npm test
```

黄金用例写在 `references/calculation.md`。测试失败时停止解盘，先修正排盘。

## 输出与安全

- 开头明确本次采用的算法、天盘类型和时间规则。
- 区分脚本事实、传统解释和基于用户反馈的推断。
- 不使用恐吓性断语，不预测死亡、重病或必然灾祸。
- 不把用户发在聊天中的 API Key 写入文件、命令或日志。
- 结尾说明：传统命理仅供文化研究与娱乐参考，人生决策应以现实信息为准。
