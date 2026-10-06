v1.1.27 完成整套 Windows 原生桌面 UI 的最后一层组件规范化，重点消除页面、对话框和 reusable widgets 之间残留的样式漂移；不新增业务功能，数据库 schema、统计口径与 Excel 导入导出结构保持不变。

- 新增统一 stack_layout primitive，页面内部纵向内容、设置页主体、图表组件、不良项目选择器和指标卡全部使用同一套垂直间距规则。
- Page 与 dialog_layout 内部也统一复用 stack_layout，页面/对话框的 spacing 和 margins 不再存在重复实现。
- MainWindow 外壳保留独立的 0px/2px 特殊布局节奏，避免把侧栏与顶栏错误套用普通内容区 spacing。
- 新增 align_table_columns helper；检验记录、质量分析、不良项目、组别管理、演示数据、导入预览和不良选择器的数字/状态表头与对应数据方向一致。
- 正常统计统一使用 summary，空数据统一使用 empty，警告/错误/成功继续使用 warning/error/success；修正检验记录正常分页摘要和质量分析“暂无数据”状态的视觉角色漂移。
- ChartWidget 的“暂无数据”统一使用 empty 角色，并由浅色/深色主题共同控制颜色。
- 导入预览去掉重复的正文大标题，遵循 Windows 原生对话框习惯：窗口标题负责标题，正文只保留摘要、说明、筛选和操作。
- 组别编辑对话框补齐统一帮助说明，与不良项目编辑、演示数据、导入预览保持同一正文层级。
- 新增组件布局、表头对齐、摘要/空状态语义回归；完整 pytest 预期为 167 项。
- 实际打包 Product-QC-Daily.exe --self-test 同步验证 stack layout、summary/empty 角色与表头对齐规则。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
