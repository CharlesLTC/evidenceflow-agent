# AI 使用记录

当前 Codex 会话根据用户提供的主规格、执行提示词、验收 JSON 和原始 Word 题目，实际完成架构、合成数据、代码、测试、调试、报告、文档及终端执行。未使用子 Agent 或另一个规划服务替代执行。

用户提供规格并在本机配置模型凭证，随后确认文件路径；Codex 将项目旁 env 文件复制到项目内部被 Git 忽略的 .env。没有在 Git 或报告中保存密钥。除规格和凭证配置外，未观察到用户对实现代码的人工修改；不宣称独立人工代码审核已经完成。

运行时 live 决策由 qwen-plus 完成；真实工具调用、Usage 和 Guard 修订见 Trace。Dense 为实际多语 MiniLM。MockModel/ScriptedModel 的离线结果不计为 live。

验证使用实际 pip、pytest、HTTP、Streamlit AppTest、真实模型场景和检索消融；保留退出码、JUnit、JSON、数据哈希和失败修复。未执行 Critic、未标注事实支持率、未知 USD 单价均不填猜测值。
