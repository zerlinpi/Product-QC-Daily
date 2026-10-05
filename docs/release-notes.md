v1.1.20 加固 Excel 历史日检表导入预览的源文件一致性和资源释放；现有业务功能、数据库 schema、统计口径和 Excel 表结构保持不变。

- 预览开始前记录源文件 SHA-256，预览完成后再次计算；如果文件在预览期间被 Excel 自动保存、同步盘或其他程序改写，会提示重新生成导入预览。
- 正式导入前仍保留原有哈希复核，因此不会把与用户预览内容不同的文件静默导入。
- 工作簿对象统一通过 finally 关闭；即使表头无法识别、行列超限或预览过程中发生其他异常，也会释放 openpyxl 资源。
- 不改变现有重复检测、编号冲突、演示数据隔离、签名解析和异常报告规则。
- 新增 2 项导入完整性回归，完整 pytest 为 150 项；Linux/Windows Ruff、pytest、Windows onedir 与实际 EXE self-test 均为发布门禁。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
