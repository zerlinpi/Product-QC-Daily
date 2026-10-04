"""Chinese application controls, including Qt dialogs on non-Chinese systems."""

from PySide6.QtCore import QLibraryInfo, QLocale, Qt, QTranslator

from app.core.paths import resource_path


class ChineseTranslator(QTranslator):
    # These strings are missing from the Qt 6 simplified-Chinese catalogue.
    overrides = {
        ("QFileDialog", "&Look in:"): "所在位置：",
        ("QFileDialog", "Files of &type:"): "文件类型：",
        ("QAbstractFileIconProvider", "Drive"): "磁盘",
        ("QAbstractFileIconProvider", "Folder"): "文件夹",
        ("QMimeType", "DOS/Windows batch file"): "批处理文件",
        ("QMimeType", "Plain text document"): "文本文档",
        ("QShortcut", "Keyboard"): "键盘",
    }

    def translate(self, context, source, disambiguation=None, n=-1):
        return self.overrides.get((context, source)) or super().translate(
            context, source, disambiguation, n
        )


def configure_chinese_ui(app):
    QLocale.setDefault(QLocale("zh_CN"))
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    if getattr(app, "_chinese_translator", None) is not None:
        return
    translator = ChineseTranslator(app)
    for directory in (
        str(resource_path("translations")),
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
    ):
        if translator.load("qtbase_zh_CN", directory):
            app.installTranslator(translator)
            app._chinese_translator = translator
            return
