v1.1.39 继续收口 v1.1.38 的现代 Windows 桌面视觉一致性，只修复已识别的 UI 残留，不新增业务功能；数据库 schema、统计口径和 Excel 导入导出结构保持不变。

- Dashboard / Analytics KPI 不再使用带标题切边框观感的 QGroupBox，改为与图表一致的平面 card：标题使用 muted 层级，大数字保留质量语义色，整体更接近现代桌面管理软件。
- 图表与表格状态语义色统一回 v1.1.38 Design Tokens：浅色 success/warning/error 使用 #16a34a / #d97706 / #dc2626，深色使用 #4ade80 / #f59e0b / #fb7185，避免主界面与 PyQtGraph/状态单元格出现两套色彩体系。
- 补齐 QDoubleSpinBox 主题，避免“生成演示数据”中的返工率/不良率输入仍保留 Fusion 默认外观；SpinBox、DateEdit、TimeEdit 的右侧 subcontrol 继续使用统一的扁平处理。
- QDialog / QMessageBox 明确跟随 panel/text token；QCalendarWidget 的背景、文本、工具按钮 hover 和日期选择状态进入同一 light/dark 主题。
- 表格增加柔和 row hover，选中行仍保持 primary-soft，继续保留无网格线、数字右对齐、状态居中与高信息密度。
- 更新 UI 回归测试与实际打包 EXE self-test，要求新 selector、平面 KPI card 和新版语义色真实进入最终 Windows 可执行程序。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
