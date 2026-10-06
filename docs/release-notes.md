v1.1.22 降低本地备份与恢复大数据文件时的内存峰值；现有业务功能、数据库 schema、统计口径和 Excel 表结构保持不变。

- 备份数据库与签名文件改为 1 MB 分块计算 SHA-256，并由 ZipFile 直接流式写入 ZIP，不再通过 Path.read_bytes() 整文件载入内存。
- 恢复时数据库与签名文件改为分块解压、边写入边校验 SHA-256，不再通过 ZipFile.read() 一次性读取完整条目。
- 已存在的同名签名改为流式哈希比较，避免双方图片同时进入内存。
- 加固 ZIP 清单边界：限制 manifest 大小，并拒绝重复 ZIP 条目；原有路径安全、完整性校验和失败回滚保持不变。
- 新增回归，直接禁止备份/恢复 payload 使用 Path.read_bytes() 与 ZipFile.read()。
- 实际打包 EXE self-test 继续执行真实 backup/restore；完整 pytest 预期为 153 项。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
