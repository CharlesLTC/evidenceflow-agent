# EvidenceFlow 第二版最终交付复验

状态：PASS；完成于 2026-11-10T07:51:34.867458+00:00。

提交前基准：1ee65427e1982d75e8bc71232dba872b69411906。最终本地/远程/API SHA 由交付后本机忽略收据 reports/delivery_verification.local.json 记录，避免提交自引用。

本轮只修改Windows启动端口说明、报告中的端口引用及交付证据；未新增架构、未修改应用逻辑、测试断言或验收标准。

pytest：75/75，失败0，错误0，跳过0。原始JUnit：pytest.xml，命令及退出码：summary.json。

真实官方验收：6/6，模型qwen-plus，检索bm25，Critic=False。

| 用例 | 状态 | 实际状态 | Trace |
|---|---|---|---|
| TC01 | PASS | COMPLETED | [Trace](../../../examples/traces/live/48fe4d9feedd40f59e8e2c87c21ccb26.json) |
| TC02 | PASS | NEEDS_CLARIFICATION | [Trace](../../../examples/traces/live/b8e6a2ca30e04e5aa2709d15f88edaa4.json) |
| TC03 | PASS | INSUFFICIENT_EVIDENCE | [Trace](../../../examples/traces/live/c03ab30b143d40239a25626e8bf7ea20.json) |
| TC04 | PASS | COMPLETED | [Trace](../../../examples/traces/live/c22e4d61b50745e4a17e147852e71bea.json) |
| TC05 | PASS | COMPLETED | [Trace](../../../examples/traces/live/b0641c94421f4473a58024452728ea92.json) |
| TC06 | PASS | COMPLETED | [Trace](../../../examples/traces/live/7940dda15c5d406eb3e70f1a0c9fa49b.json) |

证据引用准确率：{'numerator': 6, 'denominator': 6, 'rate': 1.0}。工件检查：PASS；当前交付文本安全扫描：PASS；全部可达Git历史扫描：PASS，共909个commit/blob对象，未发现配置密钥、凭证模式、私钥头或敏感密钥文件。

.gitignore 已核验：.env/.env.production、.venv、.cache、.tools被忽略，未跟踪.env及敏感密钥文件；允许提交的仅为不含真实密钥的.env.example。611个历史输入/输出/Trace/失败记录未变化，改变列表=[]。

Windows默认Streamlit端口18501；STREAMLIT_SERVER_PORT或--server.port可覆盖。API默认8000。详见README。

私有仓库权限实际快照：

{
  "verified_at": "2026-11-10T07:48:08.831147+00:00",
  "status": "CHECKED",
  "private": true,
  "collaborators": [
    {
      "login": "CharlesLTC",
      "role": "admin",
      "read": true
    }
  ],
  "pending_invitations": [],
  "intended_reviewer": null,
  "conclusion": "No intended reviewer account supplied; do not infer their access from repository visibility."
}

目标评审账号未提供，当前保持待授权；不宣称已完成评审授权。

限制保持不变：合成数据集、摘录式回答、无生产鉴权/跨进程锁；可选Critic默认关闭，控制实验不代表自然错误率；未知模型单价不填成本数字。

最新源码、Trace及报告须在推送后与GitHub main文件树再次核对；ZIP按同一最终提交生成，不包含.env、缓存、权重或本机工具。
