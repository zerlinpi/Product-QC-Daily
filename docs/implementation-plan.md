# Product-QC-Daily Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成可在 Windows 离线运行、导入原始日检表并打包 EXE 的质量管理软件。
**Architecture:** 参见 architecture.md。UI、服务和数据库分离，独立用户数据目录。
**Tech Stack:** Python 3.12+ / PySide6 / SQLite / SQLAlchemy / openpyxl / PyQtGraph。
**Spec:** 用户上传需求与 docs/architecture.md。

## Global Constraints
- 不依赖云服务器，Windows EXE 无需安装 Python。
- 数据库保存不能依赖 Excel；不得提交用户原始数据及签名。
- 完整日期区间统计；逐项未知数量不臆造；演示与正式数据明确区分。
- 核心事务、备份恢复、Excel、跨年统计必须自动化验证。

## Review Focus
- 备份含签名且恢复失败不损坏当前数据库。
- 重复 ID、冲突内容、非法数量、未知编码在预览时可见。
- 跨年月份、ISO 周、不良末尾项目统计完整。
- UI 编辑与复制不能无意覆盖或重复保存，分页和演示筛选一致。
- 打包后资源可读、数据写入用户目录、无 Python 环境可启动。

### Task 1: 数据与录入服务
Files: app/core/{paths,schemas}.py, app/database/*, app/services/{inspection,defect,settings}_service.py, tests/test_records.py.
Interface: Database(path), session(); InspectionService(db, paths).save(InspectionInput, record_id=None), get(id), query(RecordFilter), delete(ids), restore(ids); DefectService.list/save/disable.
- [x] 临时数据库 CRUD、约束、回滚、多缺陷、软删除、持久化测试。
- [x] 实现路径、迁移、字典、ORM、事务、分页和配置。
- [x] pytest tests/test_records.py：全部通过，提交。

### Task 2: 统计
Files: app/services/statistics_service.py, tests/test_statistics.py.
Interface: summary(filter), trend(filter), teams(filter), pareto(filter, metric), date_range(preset, today).
- [x] 测试跨年月份、ISO 周、零除、演示隔离、完整 24 项。
- [x] SQL 聚合，独立上一周期对比。
- [x] pytest：全部通过，提交。

### Task 3: Excel
Files: app/services/excel_service.py, app/services/excel_*.py, templates/*, scripts/prepare_template.py, tests/test_excel.py, docs/excel-analysis.md.
Interface: preview(path), import_preview(preview), export(path, filter, legacy), export_issues(preview, path).
- [x] 测试编码拆分、空值、日期、重复/冲突、签名、导出回读和模板图表。
- [x] 脱敏模板，导入预览，原子导入，标准/兼容导出，COM 可选。
- [x] pytest：全部通过，提交。

### Task 4: 维护服务
Files: app/services/{backup,demo,signature}_service.py, tests/test_maintenance.py.
Interface: backup(), restore(path), daily_backup(), DemoService.generate(options), clear(); SignatureService.store(path).
- [x] 测试 live WAL 备份、恢复前快照、坏文件拒绝、签名与 demo 清理。
- [x] 设置、保留期限、安全恢复和受控演示生成。
- [x] pytest：全部通过，提交。

### Task 5: 桌面工作流
Files: app/ui/*, app/main.py, tests/test_ui.py.
Interface: MainWindow(context), refresh(); 七页服务调用，worker 处理长任务。
- [x] Qt 离屏测试新增、再打开、编辑、复制、快捷键和页面导航。
- [x] 完成主题、表格、筛选、卡片、趋势、Pareto、设置、确认和错误提示。
- [x] pytest；实际离屏启动及截图检查；提交。

### Task 6: 发布与验收
Files: build.bat, run.bat, Product-QC-Daily.spec, .github/workflows/*, README.md, CHANGELOG.md.
- [x] 本地 lint、全套 pytest、应用自检。
- [x] 独立代码审查并修复重要发现，测试验证。
- [x] 发布代码至授权仓库，检查 Windows CI、打包 EXE 自检与构建产物。

验收依据与已知限制见 [verification.md](verification.md)。
