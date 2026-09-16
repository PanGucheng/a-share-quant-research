# 环境、依赖、许可证与 Skills

## 环境隔离

| 项目 | 本轮使用 |
|---|---|
| 主研究目录 | `E:\qlib_prj\qlib_baseline`，main@e06f9d1，只读 |
| 独立 worktree | `E:\qlib_prj\qlib_rqalpha_audit`，audit/rqalpha-poc-20260916 |
| Python | `E:\qlib_prj\rqalpha_poc_env\Scripts\python.exe`，3.10.19，独立venv，无system-site-packages |
| 官方源码 | `E:\qlib_prj\rqalpha_upstream_audit`，a5fb4e43879c381e61131399dcc094d495c7080a |
| 官方 Skills 源码 | `E:\qlib_prj\ricequant_skills_audit`，602e5452baf8221fbc501400adab60598911d51d；仅审阅 |
| PoC包 | RQAlpha6.4.0，numpy1.26.4，pandas2.3.3；完整版本见 [receipt](ENVIRONMENT.json) |
| 主环境（只读metadata） | LightGBM4.6.0，numpy2.2.6，pandas2.3.3，pyqlib0.1.dev6 |

RQAlpha 当前依赖在 Python≤3.11 要求 numpy<2，而主环境 numpy2.2.6；直接安装可能降级，故
隔离不是形式工作。venv只复用基础Python，不继承训练环境site-packages；没有在主环境pip安装、卸载或升级。
安装标准依赖包括 rqrisk，但没有安装/初始化 rqdatac、没有许可证凭证、没有bundle下载。
`pip check` 通过；20个审计核心源码文件与安装包 LF hash 相同，不能仅凭版本号认为代码一致。
[源码依赖](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/pyproject.toml)

PoC运行禁用auto_update_bundle、rqdatac、analyser；socket连接被拒绝。
该禁网只用于测试运行，安装包/克隆官方代码阶段使用网络。测试没有读取 canonical、scores 或 labels。
从既有封存E2输入读取一个日值投影及三条事件，字节hash检查不重算全期数据。
LightGBM主合同hash为 `86ca07f8005990225443febe287662ddf0a66189d116b441777e37332f590a74`，
25个绑定源码/配置文件前后核对一致；不将正在合法增长的训练输出错误要求为静止。

可复现安装依赖保存在 [requirements.lock.txt](../../experiments/rqalpha_poc/requirements.lock.txt)，
RQAlpha项固定官方Git SHA，其余固定安装版本。这是版本锁，不是 wheel 内容hash/跨平台二进制保证。
复建时仅向新的独立环境安装。该实验未加入主环境 requirements 或默认研究pipeline。

## RQAlpha license 工程记录

不能只看pyproject中的Apache-2.0标签。根LICENSE区分非商业个人/科研使用与商业用途；当前纯个人、
非商业研究PoC符合其描述的非商业使用路径，仍须遵守Apache2.0及该附加许可。商业个人用途及组织使用
受到额外授权限制，不因“内部使用”或“只有adapter”自动豁免。
[锁定版本许可证](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/LICENSE)

非商业条件下可按Apache2.0框架进行内部适配/修改；若未来分发，需保留许可证、版权/适用notice并标记修改。
本轮没有fork或修改官方core，也没有在项目中复制分发其源码。未来商业服务、销售集成或从研究转个人实际交易，
应向米筐确认授权分类；本报告不推断个人盈利实盘当然属于非商业，也不是法律结论。没有购买或申请许可证。

## Ricequant basic Skill 审阅

只审阅 [basic/ricequant/SKILL.md](https://github.com/ricequant/ricequant-skills/blob/602e5452baf8221fbc501400adab60598911d51d/skills/basic/ricequant/SKILL.md)
与官方README。它是Markdown/YAML文档查询说明，主要导航RQAlphaPlus、RQData等文档，不是开源RQAlpha
6.4.0接口契约。没有必须使用Claude专属SDK的代码；但描述和自动subagent要求面向Claude，示例用bash/curl/grep。
可移植性判断为“内容可适配”，本轮未安装、未验证Codex自动触发行为。

有价值的部分是document-index与官方Markdown文档索引。需要的最小适配是只使用该目录、缩小触发条件到
明确Ricequant文档问题、转换Windows命令、把自动subagent要求改为遵从宿主授权，并加上“AlphaPlus能力不能
推定开源RQAlpha存在”的版本提示。其自动agent指令仅作为审计对象，未作为本次运行指令执行。

frontmatter声明Proprietary并引用LICENSE.txt，但该basic目录仅有SKILL.md，审阅checkout未找到对应license文件。
因此暂建议保留官方链接作知识辅助，先澄清使用/再分发条款，再考虑仅安装basic/ricequant。没有全量安装
research skills，也没有安装RQData Python/RQAMS/RQSDK或更换数据体系。这些商业组件不构成本轮自定义DataSource
运行的前置条件。
