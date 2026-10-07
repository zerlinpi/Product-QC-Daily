v1.1.38 重新设计 Windows 桌面端视觉体系，参考 fantastic-admin/basic 的现代后台设计语言，重点解决旧版 WindowsVista 控件外观偏 Win7、层级沉重的问题；业务功能、数据库、统计口径和 Excel 导出结构保持不变。

- Windows 主界面不再优先使用 WindowsVista/Windows Qt style；统一改为 Fusion 作为跨平台绘制基底，避免系统旧主题影响主界面观感。
- 建立应用自己的浅色/深色 Design Tokens：main background、panel、sidebar、muted、border、hover、primary、primary-soft、success、warning、error 等语义角色。
- 参考 fantastic-admin 的布局层级：主内容区浅灰、侧栏/顶栏独立面板、1px 细边界、柔和 hover/active 背景、蓝色 primary 激活状态。
- 左侧导航宽度调整为 204px，菜单行高 40px，图标 18px；菜单项加入 8px 圆角、hover 背景和柔和蓝色 active 状态。
- 顶栏高度调整为 48px，页面标题 16pt / 700，整体从旧式桌面工具感转向现代后台应用感。
- 表单控件统一为 32px 高；按钮、输入框、下拉框、日期/时间、数字输入、文本框使用 6px 圆角、细边框和清晰 focus 状态。
- 主按钮使用 primary 蓝，危险操作使用红色描边与浅危险背景；禁用状态统一弱化，不再依赖 Win7 原生按钮皮肤。
- QGroupBox / 图表 card 使用白色或暗色 panel、10px 圆角和 1px border，保留桌面端信息密度但去除旧式立体边框。
- 表格表头 36px、数据行 34px，关闭旧式网格线；保留交替行，并使用浅蓝选中态、柔和表头背景和现代滚动条。
- QMenu、QToolTip、QProgressBar、QScrollBar 同步进入统一主题，避免主窗口现代但弹出层仍像旧 Windows 控件。
- 深色模式同步使用深灰面板、蓝色 active、柔和 muted/border，而不是简单反转颜色。
- Windows 原生标题栏继续跟随明暗模式；文件选择器、系统窗口行为、快捷键、离线数据和所有业务交互保持不变。
- 保留 v1.1.32–v1.1.37 的 Excel 图表缓存、长文本行高、冻结窗格、打印布局和报表视觉层级优化。
- 更新 UI 与实际打包 EXE 自检：要求 Fusion style、现代 QSS selectors、204px sidebar、40px nav、32px controls、36/34px table density 和 48px topbar 均真实进入最终 EXE。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
