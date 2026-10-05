v1.1.21 优化大体积 Excel 历史表导入时的文件校验内存占用；现有业务功能、数据库 schema、统计口径和 Excel 表结构保持不变。

- 导入预览开始前、预览完成后以及正式导入前的 SHA-256 校验均改为 1 MB 分块读取。
- 不再为哈希计算把整个 .xlsx 通过 Path.read_bytes() 一次性复制到内存，可减少与 openpyxl/WPS 兼容缓冲叠加时的内存峰值。
- v1.1.20 的源文件快照一致性规则完全保留：预览期间或预览后文件发生变化仍会拒绝导入并要求重新预览。
- 新增回归直接禁止导入源文件使用 Path.read_bytes()，确保预览和正式导入都只依赖流式哈希。
- 实际打包 EXE self-test 同样使用流式哈希核对导出文件。
- 完整 pytest 为 151 项；Linux/Windows Ruff、pytest、Windows onedir 和实际 EXE self-test 均为发布门禁。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
