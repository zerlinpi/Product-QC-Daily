v1.1.30 继续完成 Windows 原生桌面 UI 的全局一致性收口，重点统一消息弹窗、批量编辑弹窗、内容型尺寸和自适应断点；不新增业务功能，数据库 schema、统计口径和 Excel 导入导出结构保持不变。

- 新增统一 message_box / show_information 入口：普通信息、操作失败、导出完成、备份完成、恢复完成、数据库检查完成和“软件已运行”提示统一使用同一套原生 QMessageBox 配置。
- 所有原生消息框统一移除上下文帮助按钮，并统一“确定”按钮的 84×28 最小尺寸、默认按钮和键盘行为；危险确认仍默认落在“取消”，避免误操作。
- 检验记录中的“批量修改组别 / 批量修改检验员”不再使用独立 QInputDialog，改为统一单字段原生表单弹窗；字段标签、buddy、accessibleName、控件高度、460px 对话框宽度和标准按钮完全复用现有桌面规范。
- 新增 PROGRESS_DIALOG_MIN_WIDTH、IMPORT_DIALOG_SIZE、DEMO_DIALOG_SIZE、DEMO_DIALOG_MIN_SIZE、STATUS_PROGRESS_MAX_WIDTH、REMARK_MAX_HEIGHT、SIGNATURE_PREVIEW_MIN_HEIGHT 等内容型尺寸 token，消除散落硬编码。
- 任务进度、导入预览、演示数据、状态栏进度、备注区和签名预览统一引用公共尺寸 token；不同内容仍保留必要的不同规格。
- 新增 WIDE_LAYOUT_BREAKPOINT=1100；质量总览、日检录入、检验记录、质量分析、报表中心统一在同一断点切换宽/窄布局，不再出现报表页提前切换的视觉漂移。
- 导出完成弹窗也改为复用统一 message_box，避免同一应用中出现两套信息弹窗按钮规格。
- 新增消息框按钮规格、内容型尺寸、单字段弹窗与统一自适应断点回归；实际打包 Product-QC-Daily.exe --self-test 同步验证这些 UI 规则。

下载 `Product-QC-Daily-windows-x64.zip`，完整解压后运行 `Product-QC-Daily.exe`。
