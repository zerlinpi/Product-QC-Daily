from app.core.paths import AppPaths
from app.database.db import Database
from app.services.backup_service import BackupService
from app.services.defect_service import DefectService
from app.services.demo_service import DemoService
from app.services.excel_service import ExcelService
from app.services.inspection_service import InspectionService
from app.services.settings_service import SettingsService
from app.services.signature_service import SignatureService
from app.services.statistics_service import StatisticsService


class AppContext:
    def __init__(self, root=None):
        self.paths = AppPaths(root)
        self.db = Database(self.paths.db_file)
        self.settings = SettingsService(self.db)
        self.signatures = SignatureService(self.paths)
        self.defects = DefectService(self.db)
        self.inspections = InspectionService(self.db, self.paths, self.signatures)
        self.statistics = StatisticsService(self.db)
        self.excel = ExcelService(self)
        self.backup = BackupService(self)
        self.demo = DemoService(self)
