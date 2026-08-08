# 企业微信内部协议 — 全合成脱敏 fixture（WECOM-00）

本目录下的全部文件都是**手工编写的合成数据**，不是任何真实抓包或真实账号数据的副本或变形。
文件里出现的 Cookie 值、`sid`/`vid`/`uid`、`form_id`/`template_id`/`journaluuid`、人名、公司名、
头像 URL 和日报正文，均为虚构占位符，刻意使用 `SYNTHETIC-*`/`900000000000000N` 这类明显不真实的
形态，避免与真实标识混淆，也避免脱敏时遗漏个别字段。

## 与真实样例的关系

`backend/wx-ribao/`（已在根 `.gitignore` 精确忽略，见 ISS-028/WECOM-00）保存了用户提供的真实参考
脚本 `wx-ribao.py` 和一次真实提交的原始 HTTP 抓包（`http_raw_request.txt`/`http_raw_response.txt`）。
本目录的 fixture 参考了那份真实资料**归纳出的协议形状**（字段名、嵌套结构、成功判定字段），但不
包含其中任何真实取值；两者不应被混淆，也不允许把真实文件里的任何值复制粘贴进本目录。

| Fixture 文件 | 对应接口 | 置信度 |
|---|---|---|
| `answer_page_request.http` | `POST /formcol/answer_page`（提交日报） | 高：字段名、multipart 顺序、`wwjournal_data`/`form_reply` 嵌套结构直接对应真实抓包，仅替换取值 |
| `answer_page_response.json` | `POST /formcol/answer_page` 的响应 | 高：`head.ret`/`body.form`/`body.answer_replys` 结构直接对应真实抓包，仅替换取值 |
| `get_template_combine_info_response.json` | `POST /journal/get_template_combine_info` | 中：`head.ret`/`body.entrys`/`body.template_id` 字段名来自 `wx-ribao.py` 的代码路径分析；`body.form.question.items` 复用了 `answer_page` 响应里已验证的题目结构形状，无该接口本身的真实抓包可比对 |
| `get_journal_list_response.json` | `POST /wework/journal/get_journal_list` | 低：字段名仅来自 `wx-ribao.py` 对 `errcode`/`entrys`/`journalid`/`createtime` 的引用，没有任何真实抓包佐证；`WECOM-04` 实现该 Client 时应在受控测试账号上重新核对真实响应形状，而不是假定此 fixture 已完整覆盖 |

## 使用约束

- 仅供后续 `WECOM-04`（内部协议 Client 合同测试）等阶段的 mock transport / 契约测试使用。
- 新增或修改本目录文件时，只允许写入合成数据；`backend/tests/test_wecom_fixture_hygiene.py`
  会在本机存在 `backend/wx-ribao/` 时，动态提取真实样例里的 token 并断言本目录不包含，作为
  防止手滑粘贴真实值的回归防线。
- 题目/字段的中文标签（“日期”“今日工作”“明日计划”“其他事项”“附件”）是通用模板文案，不构成
  个人可识别信息，予以保留以贴近真实协议形状；人名、公司名、头像域名等可识别信息一律使用虚构值。
