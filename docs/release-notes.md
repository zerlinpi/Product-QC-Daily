v1.1.13 继续把现有七页界面收口为 Windows 本地桌面软件风格，不新增业务模块、不修改数据库 schema，也不改变 Excel 原表兼容规则。

- Windows 下继续优先 WindowsVista / Windows 原生 style，标准按钮、输入框、ComboBox、DateEdit、菜单、表格表头、GroupBox、MessageBox、复选框和滚动条不再由全局 QSS 重绘。
- 原来的白底圆角卡片改为 Qt 原生 StyledPanel；质量指标使用原生 QGroupBox，页面层级更接近普通 Windows 管理软件。
- 左侧导航由自绘按钮改为原生 QListWidget，选中高亮、键盘焦点和系统图标间距由 Qt/Windows style 负责；未保存录入拒绝切页时导航选择会自动恢复。
- 页面标题缩到 12pt、页面边距进一步收紧；顶栏和主要布局保持紧凑，数据表使用 28px 原生网格。
- 导入预览底部改用 QDialogButtonBox，让按钮顺序、默认按钮和 Esc 行为遵循 Windows Dialog 规则。
- 保留浅色 / 深色 / 跟随系统、Windows 标题栏同步、中文 UI、原生文件保存窗口和既有快捷键。
- 完整 pytest 为 139 项；Windows onedir 和实际 `Product-QC-Daily.exe --self-test` 验证原生 style、七页导航及现有导出/备份流程。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。升级仅替换程序目录，用户数据仍保存在 `%LOCALAPPDATA%/Product-QC-Daily/`。
