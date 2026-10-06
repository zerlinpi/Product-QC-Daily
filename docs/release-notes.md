v1.1.29 继续收口整套 Windows 原生桌面 UI 的字段语义与表格密度，把“视觉一致”进一步统一到 buddy、可访问名称、系统动作图标入口与表格高度算法；不新增业务功能，数据库 schema、统计口径和 Excel 导入导出结构保持不变。

- 新增 field_label helper：所有可见字段标题统一使用 fieldLabel 角色，并在有对应控件时自动建立 Qt buddy 关系与可访问名称。
- 质量总览、日检录入、检验记录、质量分析、报表中心中的 grid 表单字段与 QFormLayout 现在使用同一套标签语义，不再只在部分页面具备 buddy / accessibleName。
- 系统设置中的“原表模板 / 导出目录 / 备份目录”即使使用按钮+文本框组合布局，也显式把字段标签绑定到对应输入框。
- 不良项目页和录入页不良项目选择器的搜索框补齐统一可访问名称。
- 新增 table_minimum_rows helper：分析排行、组别统计、设置页组别表和不良项目选择器不再使用彼此无关的固定像素高度，而是基于统一表头高度 + 28px 行高 + 可见行数计算最小高度。
- button helper 增加 Qt StandardPixmap 图标入口；报表中心、系统设置和导入预览的打开/保存/文件夹动作统一通过同一系统图标路径生成，继续使用 Windows 原生 style。
- 表格的内容型高度仍允许按“需要展示多少行”差异化，避免为了表面统一而牺牲信息密度。
- 新增字段 buddy / accessibleName、表格密度算法和系统图标回归；完整 pytest 预期为 172 项。
- 实际打包 Product-QC-Daily.exe --self-test 同步验证设置字段 buddy、可访问名称，以及分析/设置/不良选择器表格的统一高度算法。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
